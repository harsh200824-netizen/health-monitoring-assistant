#backend/wellness/router.py
"""HTTP layer for the Week 5-6 Medication & Wellness Tracker.

Every endpoint requires the same Bearer token as the rest of the API.  Only
GET and POST are used, because the existing CORS configuration allows just
those two methods.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from backend.auth import decode_access_token
from backend.wellness import adherence, family, goals, insights, reports, visualization
from backend.wellness.common import WellnessError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
router = APIRouter(prefix="/wellness", tags=["Medication & Wellness Tracker"])


def current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return {"user_id": payload["sub"], "role": payload.get("role")}


def run(func, *args, **kwargs):
    """Call a service function and turn WellnessError into an HTTP error."""
    try:
        return func(*args, **kwargs)
    except WellnessError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)


# ---------- request models ----------

class MedicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    dosage: str = Field(default="", max_length=50)
    time: str = Field(min_length=5, max_length=5, description="24-hour HH:MM")


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    target_value: float = Field(gt=0, le=1_000_000)
    unit: str = Field(min_length=1, max_length=30)
    period: Literal["daily", "weekly"] = "daily"
    direction: Literal["at_least", "at_most"] = "at_least"
    source: str = Field(default="manual", max_length=30)


class GoalLog(BaseModel):
    value: float = Field(ge=0, le=1_000_000)
    log_date: Optional[str] = Field(default=None, max_length=10)
    mode: Literal["add", "set"] = "add"
    note: str = Field(default="", max_length=200)


class InviteRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    relationship: str = Field(default="other", max_length=20)


class JoinFamilyRequest(BaseModel):
    invite_code: str = Field(min_length=6, max_length=100)
    relationship: str = Field(default="other", max_length=20)


class RespondRequest(BaseModel):
    accept: bool
    share_medications: bool = True
    share_fitness: bool = True
    share_metrics: bool = False


class SharingRequest(BaseModel):
    share_medications: bool
    share_fitness: bool
    share_metrics: bool


class ReadRequest(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=200)


# ---------- overview ----------

@router.get("/overview")
def overview(user=Depends(current_user)):
    uid = user["user_id"]
    data = run(insights.generate_wellness_insights, uid)
    adh = run(adherence.get_adherence, uid, 7)
    goal_rows = run(goals.list_goals, uid)
    return {
        "wellness_score": data["wellness_score"],
        "adherence_7d": adh["overall"],
        "today": adh["today"],
        "goals": {
            "total": len(goal_rows),
            "completed": sum(1 for g in goal_rows if g["analytics"]["status"] == "completed"),
        },
        "insight_counts": data["counts"],
        "unread_notifications": run(family.list_notifications, uid, True, 1)["unread_count"],
    }


# ---------- medication adherence ----------

@router.get("/adherence")
def get_adherence(days: int = Query(30, ge=1, le=365), user=Depends(current_user)):
    return run(adherence.get_adherence, user["user_id"], days)


@router.get("/medications/today")
def medications_today(user=Depends(current_user)):
    return run(adherence.get_today_schedule, user["user_id"])


@router.post("/medications", status_code=201)
def add_medication(request: MedicationCreate, user=Depends(current_user)):
    return run(adherence.add_user_medication, user["user_id"],
               request.name, request.dosage, request.time)


@router.post("/medications/{med_id}/dose")
def log_dose(med_id: int, user=Depends(current_user)):
    return run(adherence.log_user_dose, user["user_id"], med_id)


@router.post("/medications/{med_id}/deactivate")
def deactivate_medication(med_id: int, user=Depends(current_user)):
    return run(adherence.deactivate_user_medication, user["user_id"], med_id)


# ---------- wellness goals ----------

@router.get("/goals")
def list_goals(user=Depends(current_user)):
    return run(goals.list_goals, user["user_id"])


@router.post("/goals", status_code=201)
def create_goal(request: GoalCreate, user=Depends(current_user)):
    return run(goals.create_goal, user["user_id"], request.title, request.target_value,
               request.unit, request.period, request.direction, request.source)


@router.post("/goals/{goal_id}/log")
def log_goal(goal_id: int, request: GoalLog, user=Depends(current_user)):
    return run(goals.log_goal_value, user["user_id"], goal_id, request.value,
               request.log_date, request.mode, request.note)


@router.post("/goals/{goal_id}/archive")
def archive_goal(goal_id: int, user=Depends(current_user)):
    return run(goals.archive_goal, user["user_id"], goal_id)


@router.get("/goals/{goal_id}/history")
def goal_history(goal_id: int, days: int = Query(30, ge=1, le=365), user=Depends(current_user)):
    return run(goals.goal_history, user["user_id"], goal_id, days)


# ---------- charts, insights, reports ----------

@router.get("/visualization")
def get_visualization(days: int = Query(14, ge=7, le=90), user=Depends(current_user)):
    return run(visualization.get_visualization, user["user_id"], days)


@router.get("/insights")
def get_insights(days: int = Query(30, ge=7, le=180), user=Depends(current_user)):
    return run(insights.generate_wellness_insights, user["user_id"], days)


@router.get("/report")
def get_report(days: int = Query(30, ge=7, le=180), user=Depends(current_user)):
    return run(reports.generate_wellness_report, user["user_id"], days)


@router.get("/report/csv")
def get_report_csv(days: int = Query(30, ge=7, le=180), user=Depends(current_user)):
    report = run(reports.generate_wellness_report, user["user_id"], days)
    return Response(
        content=reports.report_to_csv(report),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="wellness_report.csv"'},
    )


@router.get("/report/printable", response_class=HTMLResponse)
def get_report_printable(days: int = Query(30, ge=7, le=180), user=Depends(current_user)):
    report = run(reports.generate_wellness_report, user["user_id"], days)
    return HTMLResponse(reports.report_to_html(report))


# ---------- family monitoring ----------

@router.get("/family")
def get_family(user=Depends(current_user)):
    return run(family.list_family, user["user_id"])


@router.get("/family/dashboard")
def get_family_dashboard(user=Depends(current_user)):
    return run(family.family_dashboard, user["user_id"])


@router.post("/family/invite-code", status_code=201)
def create_family_invite_code(user=Depends(current_user)):
    return run(family.create_patient_invite_code, user["user_id"])


@router.post("/family/join", status_code=201)
def join_family(request: JoinFamilyRequest, user=Depends(current_user)):
    return run(family.request_access_with_code, user["user_id"],
               request.invite_code, request.relationship)


@router.post("/family/invite", status_code=201)
def invite_family(request: InviteRequest, user=Depends(current_user)):
    return run(family.invite_family_member, user["user_id"],
               request.username, request.relationship)


@router.post("/family/{link_id}/respond")
def respond_family(link_id: int, request: RespondRequest, user=Depends(current_user)):
    return run(family.respond_to_invite, user["user_id"], link_id, request.accept,
               request.share_medications, request.share_fitness, request.share_metrics)


@router.post("/family/{link_id}/sharing")
def update_sharing(link_id: int, request: SharingRequest, user=Depends(current_user)):
    return run(family.update_sharing, user["user_id"], link_id, request.share_medications,
               request.share_fitness, request.share_metrics)


@router.post("/family/{link_id}/revoke")
def revoke_family(link_id: int, user=Depends(current_user)):
    return run(family.revoke_link, user["user_id"], link_id)


@router.get("/family/members/{member_id}/overview")
def member_overview(member_id: int, user=Depends(current_user)):
    return run(family.member_overview, user["user_id"], member_id)


# ---------- notifications ----------

@router.get("/notifications")
def get_notifications(unread_only: bool = False, user=Depends(current_user)):
    run(family.scan_notifications, user["user_id"])
    return run(family.list_notifications, user["user_id"], unread_only)


@router.post("/notifications/read")
def read_notifications(request: ReadRequest, user=Depends(current_user)):
    return run(family.mark_notifications_read, user["user_id"], request.ids)



@router.get("/alerts")
def get_alerts(user=Depends(current_user)):
    from backend.wellness.alerts import list_alerts
    return {"alerts": list_alerts(user["user_id"])}


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: int, user=Depends(current_user)):
    from backend.wellness.alerts import acknowledge_alert
    ok = acknowledge_alert(user["user_id"], alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"message": "Alert acknowledged."}



@router.get("/risk")
def get_risk(user=Depends(current_user)):
    from backend.wellness.ml_risk import predict_risk
    return run(predict_risk, user["user_id"])



@router.get("/research")
def get_research(topic: str = Query(..., min_length=2, max_length=100), user=Depends(current_user)):
    from backend.wellness.research import summarise_topic
    return summarise_topic(topic)


@router.post("/label-scan")
async def scan_label(file: UploadFile = File(...), user=Depends(current_user)):
    from backend.wellness.label_reader import read_label
    data = await file.read()
    result = read_label(data, file.content_type or "")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result