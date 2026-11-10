"""Tests for Week 5-6 (Track A, Option A2): Medication & Wellness Tracker.

Run from the project root:
    python -m unittest backend.tests.test_wellness -v
Uses a temporary SQLite database; your real data/health.db is never touched.
"""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import src.database as db
from backend.wellness import adherence, family, goals, insights, reports, visualization
from backend.wellness.common import WellnessError
from backend.wellness.schema import init_wellness_db

NOW = datetime(2026, 10, 30, 20, 0, tzinfo=db.TIMEZONE)  # 8 PM local


def _utc_text(local_dt):
    return local_dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class WellnessTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(db, "DB_PATH", Path(self.tmp.name) / "t.db")]
        self.now = NOW
        for target in ("src.database.now_local", "backend.wellness.common.now_local",
                       "backend.wellness.adherence.now_local", "backend.wellness.goals.now_local",
                       "backend.wellness.family.now_local"):
            self.patches.append(mock.patch(target, side_effect=lambda: self.now))
        for p in self.patches:
            p.start()
        db.init_db()
        db.migrate_user_id()
        init_wellness_db()
        conn = db.get_connection()
        for i, name in enumerate(["alice", "bob", "carol"], start=1):
            conn.execute("INSERT INTO users (id, username, password_hash) VALUES (?, ?, 'x')", (i, name))
        conn.commit()
        conn.close()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    # helpers
    def day(self, offset):
        return (self.now.date() + timedelta(days=offset))

    def add_med(self, user_id, name="Metformin", time="08:00", created_days_ago=5):
        created = (self.now - timedelta(days=created_days_ago)).replace(hour=0, minute=0)
        conn = db.get_connection()
        cur = conn.execute(
            "INSERT INTO medications (name, dosage, time, user_id, created_at) VALUES (?,?,?,?,?)",
            (name, "500mg", time, user_id, _utc_text(created)))
        conn.commit()
        conn.close()
        return cur.lastrowid

    def add_dose(self, med_id, offset, hhmm="08:10"):
        conn = db.get_connection()
        conn.execute("INSERT INTO dose_log (medication_id, taken_at) VALUES (?, ?)",
                     (med_id, f"{self.day(offset).isoformat()} {hhmm}:00"))
        conn.commit()
        conn.close()

    def add_fitness(self, user_id, offset, **kw):
        conn = db.get_connection()
        conn.execute(
            """INSERT INTO fitness_activities (user_id, activity_type, duration_minutes, steps,
               sleep_hours, recorded_at) VALUES (?, 'walking', ?, ?, ?, ?)""",
            (user_id, kw.get("minutes"), kw.get("steps"), kw.get("sleep"),
             f"{self.day(offset).isoformat()} 09:00:00"))
        conn.commit()
        conn.close()


class AdherenceTests(WellnessTestCase):
    def test_counts_missed_and_streaks(self):
        med = self.add_med(1)
        for offset in (-4, -3, -1):
            self.add_dose(med, offset)
        data = adherence.get_adherence(1, 30)
        m = data["by_medication"][0]
        self.assertEqual((m["expected"], m["taken"], m["missed"]), (6, 3, 3))
        self.assertEqual(m["adherence_percent"], 50.0)
        self.assertEqual(m["current_streak"], 0)   # today (8 PM) is overdue
        self.assertEqual(m["longest_streak"], 2)
        self.assertEqual(data["today"][0]["status"], "missed")

    def test_pending_today_is_not_counted(self):
        med = self.add_med(1, time="21:30")
        self.add_dose(med, -1, "21:35")
        m = adherence.get_adherence(1, 30)["by_medication"][0]
        self.assertEqual(adherence.get_today_schedule(1)[0]["status"], "upcoming")
        self.assertEqual(m["expected"], 5)  # today not counted yet
        self.assertEqual(m["current_streak"], 1)

    def test_log_dose_is_idempotent_and_owned(self):
        med = self.add_med(1)
        first = adherence.log_user_dose(1, med)
        second = adherence.log_user_dose(1, med)
        self.assertFalse(first["already_logged"])
        self.assertTrue(second["already_logged"])
        with self.assertRaises(WellnessError) as ctx:
            adherence.log_user_dose(2, med)  # someone else's medication
        self.assertEqual(ctx.exception.status, 404)

    def test_add_validates_time(self):
        with self.assertRaises(WellnessError):
            adherence.add_user_medication(1, "Aspirin", "75mg", "9am")
        created = adherence.add_user_medication(1, "Aspirin", "75mg", "09:00")
        self.assertEqual(created["time"], "09:00")

    def test_medication_added_after_its_time_is_not_missed_that_day(self):
        self.add_med(1, time="06:00", created_days_ago=0)  # created 05:30 -> 06:00 still expected
        conn = db.get_connection()
        conn.execute("UPDATE medications SET created_at = ?", (_utc_text(self.now.replace(hour=12)),))
        conn.commit()
        conn.close()
        self.assertEqual(adherence.get_adherence(1, 7)["by_medication"][0]["expected"], 0)


class GoalTests(WellnessTestCase):
    def make_goal(self, **kw):
        args = dict(title="Water", target_value=8, unit="glasses")
        args.update(kw)
        gid = goals.create_goal(1, **args)["id"]
        conn = db.get_connection()
        conn.execute("UPDATE wellness_goals SET start_date = ? WHERE id = ?",
                     (self.day(-4).isoformat(), gid))
        conn.commit()
        conn.close()
        return gid

    def test_manual_goal_analytics(self):
        gid = self.make_goal()
        for offset, value in ((-4, 8), (-3, 8), (-2, 5), (-1, 8)):
            goals.log_goal_value(1, gid, value, self.day(offset).isoformat(), "set")
        goals.log_goal_value(1, gid, 3)
        result = goals.log_goal_value(1, gid, 3)  # add -> 6 today
        self.assertEqual(result["day_total"], 6)
        a = goals.list_goals(1)[0]["analytics"]
        self.assertEqual(a["current_value"], 6)
        self.assertEqual(a["progress_percent"], 75.0)
        self.assertEqual(a["status"], "in_progress")
        self.assertEqual(a["streak"], 1)
        self.assertEqual(a["best_streak"], 2)
        self.assertEqual(a["success_rate_percent"], 75.0)  # 3 of 4 closed days

    def test_completed_today_extends_streak(self):
        gid = self.make_goal()
        for offset in (-1, 0):
            goals.log_goal_value(1, gid, 9, self.day(offset).isoformat(), "set")
        a = goals.list_goals(1)[0]["analytics"]
        self.assertEqual(a["status"], "completed")
        self.assertEqual(a["streak"], 2)

    def test_auto_goal_reads_fitness_data(self):
        gid = self.make_goal(title="Steps", target_value=5000, unit="steps", source="steps")
        self.add_fitness(1, 0, steps=3000)
        self.add_fitness(1, 0, steps=2500)
        self.add_fitness(2, 0, steps=99999)  # other user must not count
        a = goals.list_goals(1)[0]["analytics"]
        self.assertEqual(a["current_value"], 5500)
        self.assertEqual(a["status"], "completed")
        with self.assertRaises(WellnessError):
            goals.log_goal_value(1, gid, 100)

    def test_at_most_goal(self):
        self.make_goal(title="Screen time", target_value=3, unit="hours", direction="at_most")
        gid = goals.list_goals(1)[0]["id"]
        goals.log_goal_value(1, gid, 4, mode="set")
        a = goals.list_goals(1)[0]["analytics"]
        self.assertEqual(a["status"], "exceeded")
        self.assertLess(a["progress_percent"], 100)

    def test_validation_and_ownership(self):
        gid = self.make_goal()
        with self.assertRaises(WellnessError):
            goals.create_goal(1, "x", -1, "u")
        with self.assertRaises(WellnessError):
            goals.log_goal_value(1, gid, 1, self.day(1).isoformat())  # future
        with self.assertRaises(WellnessError):
            goals.log_goal_value(2, gid, 1)  # not the owner
        self.assertEqual(goals.list_goals(2), [])


class InsightAndReportTests(WellnessTestCase):
    def test_insights_cover_all_areas(self):
        med = self.add_med(1)
        self.add_dose(med, -1)
        for offset in range(-6, 1):
            self.add_fitness(1, offset, minutes=30, steps=6000, sleep=6)
        conn = db.get_connection()
        conn.execute("INSERT INTO health_metrics (metric_type, value, unit, recorded_at) "
                     "VALUES ('blood_pressure', '152/98', 'mmHg', ?)", (f"{self.day(0)} 07:00:00",))
        conn.commit()
        conn.close()
        goals.create_goal(1, "Water", 8, "glasses")

        data = insights.generate_wellness_insights(1)
        titles = " | ".join(i["title"] for i in data["insights"])
        self.assertIn("Doses are being missed often", titles)
        self.assertIn("Activity target reached", titles)
        self.assertIn("Sleep is on the short side", titles)
        self.assertIn("Systolic blood pressure outside the typical range", titles)
        self.assertTrue(0 <= data["wellness_score"]["score"] <= 100)
        self.assertEqual(data["insights"][0]["severity"], "attention")  # sorted by severity

    def test_empty_user_gets_helpful_insights(self):
        data = insights.generate_wellness_insights(3)
        self.assertIsNone(data["wellness_score"]["score"])
        self.assertGreaterEqual(len(data["insights"]), 2)

    def test_report_and_visualization(self):
        med = self.add_med(1)
        self.add_dose(med, -1)
        self.add_fitness(1, -1, minutes=20, steps=4000, sleep=7.5)
        goals.create_goal(1, "Steps", 6000, "steps", source="steps")
        report = reports.generate_wellness_report(1, 30)
        csv_text = reports.report_to_csv(report)
        html_text = reports.report_to_html(report)
        self.assertIn("adherence", csv_text)
        self.assertIn("Medication &amp; Wellness Report", html_text)
        viz = visualization.get_visualization(1, 14)
        self.assertEqual(len(viz["fitness_daily"]), 14)
        self.assertEqual(len(viz["adherence_daily"]), 14)
        self.assertEqual(viz["goal_overview"][0]["title"], "Steps")


class FamilyTests(WellnessTestCase):
    def link(self, **share):
        link_id = family.invite_family_member(1, "bob", "parent")["id"]
        family.respond_to_invite(2, link_id, True, **share)
        return link_id

    def test_consent_flow(self):
        link_id = family.invite_family_member(1, "bob", "parent")["id"]
        with self.assertRaises(WellnessError) as ctx:      # not accepted yet
            family.member_overview(1, 2)
        self.assertEqual(ctx.exception.status, 403)
        pending = family.list_family(2)["pending_requests"]
        self.assertEqual(pending[0]["caregiver_name"], "alice")
        with self.assertRaises(WellnessError):
            family.respond_to_invite(1, link_id, True)     # caregiver cannot accept
        family.respond_to_invite(2, link_id, True, share_metrics=False)
        self.assertEqual(family.member_overview(1, 2)["member"]["username"], "bob")
        with self.assertRaises(WellnessError):
            family.member_overview(3, 2)                   # carol has no link
        family.revoke_link(2, link_id)
        with self.assertRaises(WellnessError):
            family.member_overview(1, 2)

    def test_invite_validation(self):
        with self.assertRaises(WellnessError):
            family.invite_family_member(1, "alice")
        with self.assertRaises(WellnessError):
            family.invite_family_member(1, "nobody")
        family.invite_family_member(1, "bob")
        with self.assertRaises(WellnessError):
            family.invite_family_member(1, "bob")

    def test_patient_generated_code_requires_patient_approval(self):
        invitation = family.create_patient_invite_code(2)
        self.assertTrue(invitation["invite_code"])
        request = family.request_access_with_code(1, invitation["invite_code"], "child")
        self.assertEqual(request["status"], "pending")
        patient_view = family.list_family(2)
        self.assertEqual(patient_view["pending_requests"][0]["caregiver_name"], "alice")
        with self.assertRaises(WellnessError):
            family.member_overview(1, 2)  # no health data before consent
        with self.assertRaises(WellnessError):
            family.request_access_with_code(3, invitation["invite_code"], "friend")  # one time
        family.respond_to_invite(2, request["id"], True,
                                 share_medications=False, share_fitness=True,
                                 share_metrics=False)
        overview = family.member_overview(1, 2)
        self.assertEqual(overview["member"]["username"], "bob")
        self.assertIsNone(overview["medications"])
        self.assertIsNotNone(overview["fitness"])

    def test_patient_cannot_redeem_own_code(self):
        invitation = family.create_patient_invite_code(1)
        with self.assertRaises(WellnessError):
            family.request_access_with_code(1, invitation["invite_code"])

    def test_sharing_controls_visibility(self):
        self.link(share_medications=False, share_fitness=True, share_metrics=False)
        self.add_med(2)
        view = family.member_overview(1, 2)
        self.assertIsNone(view["medications"])
        self.assertIsNotNone(view["fitness"])
        self.assertIsNone(view["readings"])

    def test_caregiver_notifications_deduplicate(self):
        self.link()
        self.add_med(2)  # nothing logged, 8 PM -> overdue
        created = family.scan_notifications(1)
        again = family.scan_notifications(1)
        self.assertGreaterEqual(created, 1)
        self.assertEqual(again, 0)
        data = family.list_notifications(1)
        kinds = {n["kind"] for n in data["notifications"]}
        self.assertIn("missed_dose", kinds)
        self.assertEqual(data["unread_count"], len(data["notifications"]))
        family.mark_notifications_read(1)
        self.assertEqual(family.list_notifications(1)["unread_count"], 0)

    def test_dashboard(self):
        self.link()
        med = self.add_med(2)
        self.add_dose(med, 0)
        card = family.family_dashboard(1)["members"][0]
        self.assertEqual(card["username"], "bob")
        self.assertEqual(card["doses_today"], {"total": 1, "taken": 1, "missed": 0})


if __name__ == "__main__":
    unittest.main()
