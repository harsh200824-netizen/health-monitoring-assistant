//frontend-react/src/WellnessTracker.jsx
import { useCallback, useEffect, useMemo, useState } from "react";
import "./WellnessTracker.css";

// Week 5-6 (Track A, Option A2): Medication & Wellness Tracker UI.
// Self-contained: it only needs the login token from App.jsx.

const API = "http://127.0.0.1:8000";

async function request(token, path, options = {}) {
  const headers = { Authorization: `Bearer ${token}` };
  if (options.body) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API}/wellness/${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = isJson ? data.detail : null;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail;
    throw new Error(message || `Request failed (${res.status}).`);
  }
  return data;
}

const pretty = (value) => String(value ?? "").replaceAll("_", " ");
const shortDate = (d) => String(d || "").slice(5);
const fmt = (n, digits = 1) => (n == null ? "-" : Number.isInteger(n) ? n : Number(n).toFixed(digits));

const STATUS_LABEL = {
  taken: ["Taken", "good"], upcoming: ["Upcoming", "info"], due: ["Due now", "warn"], missed: ["Missed", "bad"],
  completed: ["Completed", "good"], in_progress: ["In progress", "info"], on_track: ["On track", "good"],
  behind: ["Behind", "warn"], not_started: ["Not started", "info"], within_limit: ["Within limit", "good"],
  exceeded: ["Over limit", "bad"], no_data: ["No data yet", "info"],
};

function Pill({ status }) {
  const [label, tone] = STATUS_LABEL[status] || [pretty(status), "info"];
  return <span className={`wt-pill wt-${tone}`}>{label}</span>;
}

function Empty({ text }) {
  return <div className="wt-empty">{text}</div>;
}

function Bars({ data, max, color = "#51d9c8", unit = "", height = 110, labelEvery = 1 }) {
  const top = max ?? Math.max(1, ...data.map((d) => d.value ?? 0));
  return (
    <div className="wt-bars" style={{ height }}>
      {data.map((d, i) => (
        <div className="wt-bar-col" key={`${d.label}-${i}`} title={`${d.label}: ${d.value ?? "no data"} ${unit}`}>
          <div className="wt-bar-track">
            <div
              className="wt-bar"
              style={{
                height: `${Math.min(100, ((d.value ?? 0) / top) * 100)}%`,
                background: d.color || color,
                opacity: d.value == null ? 0.15 : 1,
              }}
            />
          </div>
          <span className="wt-bar-label">{i % labelEvery === 0 ? d.label : ""}</span>
        </div>
      ))}
    </div>
  );
}

function Line({ points, color = "#51d9c8", unit = "" }) {
  if (!Array.isArray(points) || points.length === 0) {
  return <Empty text="No readings yet." />;
}
  const values = points.map((p) => p.value);
  const min = Math.min(...values), max = Math.max(...values), range = max - min || 1;
  const W = 300, H = 100, pad = 8;
  const coords = points.map((p, i) => [
    points.length === 1 ? W / 2 : pad + i * ((W - 2 * pad) / (points.length - 1)),
    H - pad - ((p.value - min) / range) * (H - 2 * pad),
  ]);
  return (
    <div>
      <svg className="wt-line" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Trend chart">
        <polyline points={coords.map((c) => c.join(",")).join(" ")} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        {coords.map((c, i) => <circle key={i} cx={c[0]} cy={c[1]} r="2.6" fill={color} />)}
      </svg>
      <div className="wt-line-meta">
        <span>{shortDate(points[0].date)}</span>
        <span>min {fmt(min)} / max {fmt(max)} {unit}</span>
        <span>{shortDate(points[points.length - 1].date)}</span>
      </div>
    </div>
  );
}

function Message({ text, error }) {
  if (!text) return null;
  return <div className={error ? "state-banner error" : "wt-note"} role={error ? "alert" : "status"}>{text}</div>;
}

/* ------------------------------------------------------------------ */
/* Adherence                                                           */
/* ------------------------------------------------------------------ */

function AdherenceTab({ api, onChange }) {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ name: "", dosage: "", time: "08:00" });
  const [msg, setMsg] = useState({ text: "", error: false });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setData(await api(`adherence?days=${days}`)); }
    catch (e) { setMsg({ text: e.message, error: true }); }
  }, [api, days]);
 useEffect(() => {
  let cancelled = false;

  const refresh = async () => {
    await Promise.resolve();
    if (!cancelled) {
      await load();
    }
  };

  refresh();

  return () => {
    cancelled = true;
  };
}, [load]);

  const act = async (fn, okText) => {
    setBusy(true);
    try {
      const res = await fn();
      setMsg({ text: okText || res?.message || "Done.", error: false });
      await load();
      onChange();
    } catch (e) { setMsg({ text: e.message, error: true }); }
    finally { setBusy(false); }
  };

  const addMedication = (event) => {
    event.preventDefault();
    act(async () => {
      const res = await api("medications", { method: "POST", body: { name: form.name.trim(), dosage: form.dosage.trim(), time: form.time } });
      setForm({ name: "", dosage: "", time: "08:00" });
      return res;
    }, "Medication added.");
  };

  const overall = data?.overall;
  return (
    <div>
      <Message {...msg} />
      <div className="wt-stat-row">
        <div className="wt-stat"><span>Adherence ({days} days)</span><strong>{overall?.adherence_percent == null ? "-" : `${overall.adherence_percent}%`}</strong><small>{overall ? pretty(overall.grade) : ""}</small></div>
        <div className="wt-stat"><span>Doses taken</span><strong>{overall?.taken ?? "-"}</strong><small>of {overall?.expected ?? "-"} expected</small></div>
        <div className="wt-stat"><span>Missed</span><strong>{overall?.missed ?? "-"}</strong><small>in this period</small></div>
        <label className="wt-stat wt-select-stat"><span>Period</span>
          <select className="chart-select" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
          </select>
        </label>
      </div>

      <div className="two-column">
        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">TODAY</span><h3>Today&apos;s doses</h3></div></div>
          {!data?.today?.length ? <Empty text="No active medications. Add one to start tracking." /> : (
            <ul className="wt-list">
              {data.today.map((m) => (
                <li key={m.id} className="wt-row">
                  <div>
                    <strong>{m.name}</strong> <span className="muted">{m.dosage}</span>
                    <div className="muted">Scheduled {m.time}{m.status === "missed" ? ` - ${m.minutes_late} min late` : ""}</div>
                  </div>
                  <div className="wt-actions">
                    <Pill status={m.status} />
                    {m.status !== "taken" && <button className="button button-primary" disabled={busy} onClick={() => act(() => api(`medications/${m.id}/dose`, { method: "POST" }))}>Mark taken</button>}
                    <button className="button button-secondary" disabled={busy} onClick={() => { if (window.confirm(`Remove ${m.name} from your active medications?`)) act(() => api(`medications/${m.id}/deactivate`, { method: "POST" })); }}>Remove</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">NEW</span><h3>Add a medication</h3></div></div>
          <form className="form-grid" onSubmit={addMedication}>
            <label className="field span-two">Name<input value={form.name} maxLength="100" required onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Metformin" /></label>
            <label className="field">Dosage<input value={form.dosage} maxLength="50" onChange={(e) => setForm({ ...form, dosage: e.target.value })} placeholder="500 mg" /></label>
            <label className="field">Daily time<input type="time" value={form.time} required onChange={(e) => setForm({ ...form, time: e.target.value })} /></label>
            <div className="form-footer span-two"><button className="button button-primary" disabled={busy}>Add medication</button></div>
          </form>
        </article>
      </div>

      <article className="panel wt-panel">
        <div className="panel-heading"><div><span className="eyebrow">TREND</span><h3>Daily adherence</h3></div></div>
        {data ? <Bars data={data.daily.map((d) => ({ label: shortDate(d.date), value: d.adherence_percent }))} max={100} unit="%" labelEvery={Math.max(1, Math.ceil(days / 10))} /> : <Empty text="Loading..." />}
      </article>

      <article className="panel wt-panel">
        <div className="panel-heading"><div><span className="eyebrow">BY MEDICATION</span><h3>Adherence and streaks</h3></div></div>
        {!data?.by_medication?.length ? <Empty text="No medication data yet." /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Medication</th><th>Time</th><th>Taken</th><th>Missed</th><th>Adherence</th><th>Streak</th><th>Best</th><th>Last taken</th></tr></thead>
              <tbody>
                {data.by_medication.map((m) => (
                  <tr key={m.id}>
                    <td>{m.name} {m.dosage}</td><td>{m.time}</td><td>{m.taken}/{m.expected}</td><td>{m.missed}</td>
                    <td>{m.adherence_percent == null ? "-" : `${m.adherence_percent}%`}</td>
                    <td>{m.current_streak}d</td><td>{m.longest_streak}d</td><td>{m.last_taken ? m.last_taken.slice(0, 16) : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Goals                                                               */
/* ------------------------------------------------------------------ */

const PRESETS = {
  custom: { title: "", target_value: "", unit: "", period: "daily", direction: "at_least", source: "manual" },
  water: { title: "Drink water", target_value: 8, unit: "glasses", period: "daily", direction: "at_least", source: "manual" },
  steps: { title: "Daily steps", target_value: 8000, unit: "steps", period: "daily", direction: "at_least", source: "steps" },
  sleep: { title: "Sleep", target_value: 7, unit: "hours", period: "daily", direction: "at_least", source: "sleep_hours" },
  active: { title: "Weekly active minutes", target_value: 150, unit: "minutes", period: "weekly", direction: "at_least", source: "active_minutes" },
  screen: { title: "Screen time", target_value: 3, unit: "hours", period: "daily", direction: "at_most", source: "manual" },
};
const TREND = { up: "↑ improving", down: "↓ declining", flat: "→ steady", not_enough_data: "not enough data" };

function GoalsTab({ api, onChange }) {
  const [goals, setGoals] = useState([]);
  const [preset, setPreset] = useState("water");
  const [form, setForm] = useState(PRESETS.water);
  const [logs, setLogs] = useState({});
  const [msg, setMsg] = useState({ text: "", error: false });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setGoals(await api("goals")); }
    catch (e) { setMsg({ text: e.message, error: true }); }
  }, [api]);
 useEffect(() => {
  let cancelled = false;

  const refresh = async () => {
    await Promise.resolve();
    if (!cancelled) {
      await load();
    }
  };

  refresh();

  return () => {
    cancelled = true;
  };
}, [load]);

  const choosePreset = (key) => { setPreset(key); setForm(PRESETS[key]); };

  const run = async (fn, okText) => {
    setBusy(true);
    try {
      const res = await fn();
      setMsg({ text: okText || res?.message || "Done.", error: false });
      await load();
      onChange();
      return true;
    } catch (e) { setMsg({ text: e.message, error: true }); return false; }
    finally { setBusy(false); }
  };

  const createGoal = (event) => {
    event.preventDefault();
    run(() => api("goals", { method: "POST", body: { ...form, target_value: Number(form.target_value) } }), "Goal created.");
  };

  const logProgress = async (goal, mode) => {
    const value = Number(logs[goal.id]);
    if (!Number.isFinite(value) || value < 0 || logs[goal.id] === "" || logs[goal.id] == null) {
      setMsg({ text: "Enter a number of zero or more.", error: true });
      return;
    }
    const ok = await run(() => api(`goals/${goal.id}/log`, { method: "POST", body: { value, mode } }), "Progress logged.");
    if (ok) setLogs({ ...logs, [goal.id]: "" });
  };

  const isAuto = form.source !== "manual";
  return (
    <div>
      <Message {...msg} />
      <div className="two-column">
        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">PROGRESS</span><h3>Your wellness goals</h3></div><span className="data-tag">{goals.length} active</span></div>
          {!goals.length ? <Empty text="No goals yet. Create one to start tracking." /> : (
            <div className="goal-list">
              {goals.map((g) => {
                const a = g.analytics;
                const auto = g.source !== "manual";
                return (
                  <div className="goal-item wt-goal" key={g.id}>
                    <div className="goal-top"><strong>{g.title}</strong><Pill status={a.status} /></div>
                    <div className="goal-values">
                      {fmt(a.current_value)} / {g.direction === "at_most" ? "max " : ""}{g.target_value} {g.unit} ({g.period}){auto ? " - auto-tracked" : ""}
                    </div>
                    <progress value={a.progress_percent} max="100" aria-label={`${g.title} progress`} />
                    <div className="wt-goal-stats">
                      <span>Streak <b>{a.streak}</b></span>
                      <span>Best <b>{a.best_streak}</b></span>
                      <span>Success <b>{a.success_rate_percent == null ? "-" : `${a.success_rate_percent}%`}</b></span>
                      <span>{TREND[a.trend]}</span>
                    </div>
                    <Bars height={56} max={Math.max(g.target_value, ...a.history.map((h) => h.value))} data={a.history.map((h) => ({ label: shortDate(h.bucket_start), value: h.value, color: h.met ? "#51d9c8" : "#6d7f94" }))} unit={g.unit} />
                    <div className="wt-goal-actions">
                      {!auto && (
                        <>
                          <input type="number" min="0" step="any" placeholder={`Add ${g.unit}`} value={logs[g.id] ?? ""} onChange={(e) => setLogs({ ...logs, [g.id]: e.target.value })} aria-label={`Log ${g.unit} for ${g.title}`} />
                          <button className="button button-primary" disabled={busy} onClick={() => logProgress(g, "add")}>Add</button>
                          <button className="button button-secondary" disabled={busy} onClick={() => logProgress(g, "set")}>Set today</button>
                        </>
                      )}
                      <button className="button button-secondary" disabled={busy} onClick={() => { if (window.confirm(`Archive "${g.title}"?`)) run(() => api(`goals/${g.id}/archive`, { method: "POST" })); }}>Archive</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">NEW GOAL</span><h3>Create a goal</h3></div></div>
          <form className="form-grid" onSubmit={createGoal}>
            <label className="field span-two">Start from a template
              <select className="wt-select" value={preset} onChange={(e) => choosePreset(e.target.value)}>
                <option value="water">Drink water (manual)</option><option value="steps">Daily steps (auto)</option>
                <option value="sleep">Sleep hours (auto)</option><option value="active">Weekly active minutes (auto)</option>
                <option value="screen">Screen time limit (manual)</option><option value="custom">Custom</option>
              </select>
            </label>
            <label className="field span-two">Title<input value={form.title} required maxLength="80" onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
            <label className="field">Target<input type="number" min="0.01" step="any" required value={form.target_value} onChange={(e) => setForm({ ...form, target_value: e.target.value })} /></label>
            <label className="field">Unit<input value={form.unit} required maxLength="30" onChange={(e) => setForm({ ...form, unit: e.target.value })} /></label>
            <label className="field">Period
              <select className="wt-select" value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value })}><option value="daily">Daily</option><option value="weekly">Weekly</option></select>
            </label>
            <label className="field">Goal type
              <select className="wt-select" value={form.direction} onChange={(e) => setForm({ ...form, direction: e.target.value })}><option value="at_least">Reach at least</option><option value="at_most">Stay at or below</option></select>
            </label>
            <label className="field span-two">Tracking
              <select className="wt-select" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}>
                <option value="manual">Manual - I log it myself</option><option value="steps">Auto - steps from fitness activities</option>
                <option value="active_minutes">Auto - active minutes</option><option value="sleep_hours">Auto - sleep hours</option>
                <option value="calories">Auto - calories burned</option><option value="distance_km">Auto - distance (km)</option>
              </select>
            </label>
            {isAuto && <p className="muted span-two">Auto goals update from the activities you log in the Fitness section.</p>}
            <div className="form-footer span-two"><button className="button button-primary" disabled={busy}>Create goal</button></div>
          </form>
        </article>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Insights & charts                                                   */
/* ------------------------------------------------------------------ */

function InsightsTab({ api }) {
  const [days, setDays] = useState(14);
  const [insights, setInsights] = useState(null);
  const [viz, setViz] = useState(null);
  const [metric, setMetric] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [i, v] = await Promise.all([api("insights"), api(`visualization?days=${days}`)]);
      setInsights(i); setViz(v); setError("");
    } catch (e) { setError(e.message); }
  }, [api, days]);
  useEffect(() => {
  let cancelled = false;

  const refresh = async () => {
    await Promise.resolve();
    if (!cancelled) {
      await load();
    }
  };

  refresh();

  return () => {
    cancelled = true;
  };
}, [load]);

  const metricNames = viz ? Object.keys(viz.metric_series) : [];
  const selected = metricNames.includes(metric) ? metric : metricNames[0];
  const every = Math.max(1, Math.ceil(days / 8));
  const fitness = viz?.fitness_daily || [];
  const score = insights?.wellness_score;

  return (
    <div>
      <Message text={error} error />
      <div className="two-column">
        <article className="panel wt-score-panel">
          <div className="panel-heading"><div><span className="eyebrow">WELLNESS SCORE</span><h3>Overall picture</h3></div></div>
          {score?.score == null ? <Empty text="Add medications, goals or activity to see your score." /> : (
            <div className="wt-score">
              <div className={`wt-score-ring wt-score-${score.label}`}><strong>{score.score}</strong><span>/ 100</span></div>
              <div className="wt-score-parts">
                {Object.entries(score.components).map(([k, v]) => (
                  <div key={k}><span>{k}</span><progress value={v} max="100" aria-label={`${k} score`} /><b>{v}</b></div>
                ))}
              </div>
            </div>
          )}
        </article>
        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">PERSONALIZED</span><h3>Insights and recommendations</h3></div>
            {insights && <span className="data-tag">{insights.counts.attention} need attention</span>}</div>
          {!insights?.insights?.length ? <Empty text="No insights yet." /> : (
            <ul className="wt-insights">
              {insights.insights.map((item, i) => (
                <li key={i} className={`wt-insight wt-sev-${item.severity}`}>
                  <strong>{item.title}</strong>
                  <p>{item.message}</p>
                  {item.recommendation && <p className="wt-reco">Suggestion: {item.recommendation}</p>}
                </li>
              ))}
            </ul>
          )}
          {insights && <p className="assistant-disclaimer">{insights.disclaimer}</p>}
        </article>
      </div>

      <div className="wt-toolbar">
        <span className="eyebrow">CHARTS</span>
        <select className="chart-select" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option><option value={14}>Last 14 days</option><option value={30}>Last 30 days</option>
        </select>
      </div>
      <div className="two-column">
        <article className="panel"><div className="panel-heading"><div><span className="eyebrow">MOVEMENT</span><h3>Steps per day</h3></div></div>
          <Bars data={fitness.map((d) => ({ label: shortDate(d.date), value: d.has_data ? d.steps : null }))} unit="steps" labelEvery={every} /></article>
        <article className="panel"><div className="panel-heading"><div><span className="eyebrow">ACTIVITY</span><h3>Active minutes per day</h3></div></div>
          <Bars color="#77aefa" data={fitness.map((d) => ({ label: shortDate(d.date), value: d.has_data ? d.duration_minutes : null }))} unit="min" labelEvery={every} /></article>
      </div>
      <div className="two-column">
        <article className="panel"><div className="panel-heading"><div><span className="eyebrow">REST</span><h3>Sleep hours</h3></div></div>
          <Bars color="#c4a7fc" max={10} data={fitness.map((d) => ({ label: shortDate(d.date), value: d.sleep_hours ? d.sleep_hours : null }))} unit="h" labelEvery={every} /></article>
        <article className="panel"><div className="panel-heading"><div><span className="eyebrow">MEDICATION</span><h3>Adherence by medication</h3></div></div>
          {!viz?.adherence_by_medication?.length ? <Empty text="No medications yet." /> :
            <Bars max={100} unit="%" data={viz.adherence_by_medication.map((m) => ({ label: m.name.slice(0, 8), value: m.percent }))} />}</article>
      </div>
      <div className="two-column">
        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">READINGS</span><h3>Health metric trend</h3></div>
            {metricNames.length > 0 && <select className="chart-select" value={selected} onChange={(e) => setMetric(e.target.value)}>{metricNames.map((n) => <option key={n} value={n}>{pretty(n)}</option>)}</select>}</div>
          {selected ? <Line points={viz.metric_series[selected]} unit={viz.metric_series[selected][0]?.unit} color="#ffc384" /> : <Empty text="Numeric health readings will appear here." />}
        </article>
        <article className="panel"><div className="panel-heading"><div><span className="eyebrow">GOALS</span><h3>Goal progress</h3></div></div>
          {!viz?.goal_overview?.length ? <Empty text="No goals yet." /> :
            <Bars max={100} unit="%" data={viz.goal_overview.map((g) => ({ label: g.title.slice(0, 8), value: g.percent }))} />}</article>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Family & caregiver notifications                                    */
/* ------------------------------------------------------------------ */

const RELATIONSHIPS = ["parent", "child", "spouse", "sibling", "grandparent", "friend", "other"];

function ShareToggles({ value, onChange }) {
  return (
    <div className="wt-toggles">
      {[["share_medications", "Medications"], ["share_fitness", "Fitness"], ["share_metrics", "Health readings"]].map(([key, label]) => (
        <label key={key}><input type="checkbox" checked={!!value[key]} onChange={(e) => onChange({ ...value, [key]: e.target.checked })} /> {label}</label>
      ))}
    </div>
  );
}

function FamilyTab({ api, onChange }) {
  const [family, setFamily] = useState({ monitoring: [], caregivers: [], pending_requests: [] });
  const [dashboard, setDashboard] = useState({ members: [] });
  const [notes, setNotes] = useState({ unread_count: 0, notifications: [] });
  const [join, setJoin] = useState({ invite_code: "", relationship: "parent" });
  const [inviteCode, setInviteCode] = useState(null);
  const [shares, setShares] = useState({});
  const [detail, setDetail] = useState(null);
  const [msg, setMsg] = useState({ text: "", error: false });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [f, d, n] = await Promise.all([api("family"), api("family/dashboard"), api("notifications")]);
      setFamily(f); setDashboard(d); setNotes(n);
    } catch (e) { setMsg({ text: e.message, error: true }); }
  }, [api]);
useEffect(() => {
  let cancelled = false;

  const refresh = async () => {
    await Promise.resolve();
    if (!cancelled) {
      await load();
    }
  };

  refresh();

  const timer = setInterval(refresh, 60000);

  return () => {
    cancelled = true;
    clearInterval(timer);
  };
}, [load]);
  const run = async (fn, okText) => {
    setBusy(true);
    try {
      const res = await fn();
      setMsg({ text: okText || res?.message || "Done.", error: false });
      await load();
      onChange();
      return true;
    } catch (e) { setMsg({ text: e.message, error: true }); return false; }
    finally { setBusy(false); }
  };

  const shareFor = (id, fallback) => shares[id] || fallback || { share_medications: true, share_fitness: true, share_metrics: false };
  const openMember = async (memberId) => {
    try { setDetail(await api(`family/members/${memberId}/overview`)); }
    catch (e) { setMsg({ text: e.message, error: true }); }
  };

  return (
    <div>
      <Message {...msg} />

      {family.pending_requests.length > 0 && (
        <article className="panel wt-panel wt-attention">
          <div className="panel-heading"><div><span className="eyebrow">ACTION NEEDED</span><h3>Caregiver requests</h3></div></div>
          {family.pending_requests.map((r) => (
            <div className="wt-row" key={r.id}>
              <div><strong>{r.caregiver_name}</strong> would like to monitor your health as your {r.relationship}.
                <div className="muted">Choose what they can see before accepting:</div>
                <ShareToggles value={shareFor(r.id)} onChange={(v) => setShares({ ...shares, [r.id]: v })} /></div>
              <div className="wt-actions">
                <button className="button button-primary" disabled={busy} onClick={() => run(() => api(`family/${r.id}/respond`, { method: "POST", body: { accept: true, ...shareFor(r.id) } }))}>Accept</button>
                <button className="button button-secondary" disabled={busy} onClick={() => run(() => api(`family/${r.id}/respond`, { method: "POST", body: { accept: false } }))}>Decline</button>
              </div>
            </div>
          ))}
        </article>
      )}

      <div className="two-column">
        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">CAREGIVER VIEW</span><h3>People I monitor</h3></div><span className="data-tag">{dashboard.members.length} connected</span></div>
          {!family.monitoring.length ? <Empty text="You are not monitoring anyone yet." /> : (
            <div className="wt-cards">
              {family.monitoring.map((link) => {
                const card = dashboard.members.find((m) => m.link_id === link.id);
                return (
                  <div className="wt-member" key={link.id}>
                    <div className="wt-member-head"><strong>{link.member_name}</strong><span className="muted">{link.relationship}</span></div>
                    {link.status === "pending" ? <span className="wt-pill wt-info">Waiting for approval</span> : (
                      <>
                        <div className="wt-member-stats">
                          <span>7-day adherence <b>{card?.adherence_7d == null ? "-" : `${card.adherence_7d}%`}</b></span>
                          <span>Today <b>{card?.doses_today ? `${card.doses_today.taken}/${card.doses_today.total}` : "-"}</b></span>
                          <span>Alerts <b className={card?.alerts ? "wt-bad-text" : ""}>{card?.alerts ?? 0}</b></span>
                        </div>
                        <div className="wt-actions">
                          <button className="button button-secondary" onClick={() => openMember(link.member_id)}>View details</button>
                        </div>
                      </>
                    )}
                    <button className="text-button wt-link" disabled={busy} onClick={() => { if (window.confirm(`Stop monitoring ${link.member_name}?`)) run(() => api(`family/${link.id}/revoke`, { method: "POST" })); }}>{link.status === "pending" ? "Cancel request" : "Stop monitoring"}</button>
                  </div>
                );
              })}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">PATIENT INVITATION</span><h3>Invite a caregiver</h3></div></div>
          <p className="muted">Generate a one-time code and share it privately with your caregiver. The code expires after 24 hours.</p>
          <button className="button button-primary" disabled={busy} onClick={() => run(async () => { const result = await api("family/invite-code", { method: "POST" }); setInviteCode(result); return result; }, "Invitation code created.")}>Generate invitation code</button>
          {inviteCode && <div className="wt-note" style={{ marginTop: 12 }}>
            <strong>Share this code with your caregiver:</strong>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
              <code style={{ fontSize: 17, letterSpacing: 1.5, userSelect: "all" }}>{inviteCode.invite_code}</code>
              <button type="button" className="button button-secondary" onClick={() => navigator.clipboard?.writeText(inviteCode.invite_code).then(() => setMsg({ text: "Invitation code copied.", error: false })).catch(() => setMsg({ text: "Select and copy the code manually.", error: true }))}>Copy code</button>
            </div>
            <small>Expires: {inviteCode.expires_at}. This code can be used once.</small>
          </div>}
          <div className="wt-divider" />
          <div className="panel-heading"><div><span className="eyebrow">CAREGIVER</span><h3>Join a family member</h3></div></div>
          <p className="muted">Enter the invitation code shared by the patient. You will not see their health information unless they approve your request.</p>
          <form className="form-grid" onSubmit={(e) => { e.preventDefault(); run(() => api("family/join", { method: "POST", body: join }), "Access request sent. The patient must approve it.").then((ok) => ok && setJoin({ ...join, invite_code: "" })); }}>
            <label className="field">Invitation code<input value={join.invite_code} required maxLength="100" autoComplete="off" onChange={(e) => setJoin({ ...join, invite_code: e.target.value })} /></label>
            <label className="field">Relationship to patient
              <select className="wt-select" value={join.relationship} onChange={(e) => setJoin({ ...join, relationship: e.target.value })}>{RELATIONSHIPS.map((r) => <option key={r} value={r}>{r}</option>)}</select>
            </label>
            <div className="form-footer span-two"><button className="button button-primary" disabled={busy}>Request access</button></div>
          </form>
        </article>
      </div>

      {detail && (
        <article className="panel wt-panel">
          <div className="panel-heading"><div><span className="eyebrow">DETAILS</span><h3>{detail.member.username} ({detail.member.relationship})</h3></div><button className="button button-secondary" onClick={() => setDetail(null)}>Close</button></div>
          {detail.alerts.length > 0 && <ul className="wt-insights">{detail.alerts.map((a) => <li key={a.key} className="wt-insight wt-sev-attention"><strong>{pretty(a.kind)}</strong><p>{a.message}</p></li>)}</ul>}
          {detail.medications ? (
            <>
              <p className="muted">Adherence: {detail.medications.adherence_7d ?? "-"}% over 7 days, {detail.medications.adherence_30d ?? "-"}% over 30 days.</p>
              <div className="table-wrap"><table><thead><tr><th>Medication</th><th>Time</th><th>Today</th></tr></thead><tbody>
                {detail.medications.today.map((m) => <tr key={m.id}><td>{m.name} {m.dosage}</td><td>{m.time}</td><td><Pill status={m.status} /></td></tr>)}
              </tbody></table></div>
              <Bars height={80} max={100} unit="%" data={detail.medications.daily.map((d) => ({ label: shortDate(d.date), value: d.adherence_percent }))} />
            </>
          ) : <p className="muted">Medication data is not shared.</p>}
          {detail.fitness ? <p className="muted">Last 7 days: {detail.fitness.total_steps.toLocaleString()} steps, {detail.fitness.active_minutes} active minutes, average sleep {detail.fitness.average_sleep_hours} h.</p> : <p className="muted">Fitness data is not shared.</p>}
          {detail.readings ? (detail.readings.length ? <p className="muted">Latest readings: {detail.readings.map((r) => `${pretty(r.metric)} ${r.latest} ${r.unit || ""}`).join("; ")}</p> : <p className="muted">No readings recorded.</p>) : <p className="muted">Health readings are not shared.</p>}
        </article>
      )}

      <div className="two-column">
        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">PRIVACY</span><h3>People who can see my data</h3></div></div>
          {!family.caregivers.length ? <Empty text="No one is monitoring your health." /> : family.caregivers.map((c) => (
            <div className="wt-row wt-column-row" key={c.id}>
              <div><strong>{c.caregiver_name}</strong> <span className="muted">({c.relationship})</span>
                <ShareToggles value={shareFor(`s${c.id}`, c)} onChange={(v) => setShares({ ...shares, [`s${c.id}`]: v })} /></div>
              <div className="wt-actions">
                <button className="button button-secondary" disabled={busy} onClick={() => run(() => api(`family/${c.id}/sharing`, { method: "POST", body: shareFor(`s${c.id}`, c) }))}>Save sharing</button>
                <button className="button button-secondary" disabled={busy} onClick={() => { if (window.confirm(`Stop sharing with ${c.caregiver_name}?`)) run(() => api(`family/${c.id}/revoke`, { method: "POST" })); }}>Revoke access</button>
              </div>
            </div>
          ))}
        </article>

        <article className="panel">
          <div className="panel-heading"><div><span className="eyebrow">ALERTS</span><h3>Notifications</h3></div>
            {notes.unread_count > 0 && <button className="button button-secondary" onClick={() => run(() => api("notifications/read", { method: "POST", body: { ids: [] } }), "All marked as read.")}>Mark all read ({notes.unread_count})</button>}</div>
          {!notes.notifications.length ? <Empty text="No notifications." /> : (
            <ul className="wt-notes">
              {notes.notifications.slice(0, 12).map((n) => (
                <li key={n.id} className={`${n.read_at ? "" : "wt-unread"} wt-sev-${n.severity}`}>
                  <p>{n.message}</p><small>{String(n.created_at).slice(0, 16)}</small>
                </li>
              ))}
            </ul>
          )}
        </article>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Reports                                                             */
/* ------------------------------------------------------------------ */

function ReportsTab({ api, token }) {
  const [days, setDays] = useState(30);
  const [report, setReport] = useState(null);
  const [state, setState] = useState("idle");
  const [error, setError] = useState("");

  const generate = async () => {
    setState("loading"); setError("");
    try { setReport(await api(`report?days=${days}`)); setState("done"); }
    catch (e) { setError(e.message); setState("error"); }
  };

  const fetchBlob = async (path, type) => {
    const res = await fetch(`${API}/wellness/${path}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error(`Download failed (${res.status}).`);
    return new Blob([await res.text()], { type });
  };
  const downloadCsv = async () => {
    try {
      const blob = await fetchBlob(`report/csv?days=${days}`, "text/csv");
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "wellness_report.csv";
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (e) { setError(e.message); }
  };
  const openPrintable = async () => {
    try {
      const blob = await fetchBlob(`report/printable?days=${days}`, "text/html");
      window.open(URL.createObjectURL(blob), "_blank");
    } catch (e) { setError(e.message); }
  };

  return (
    <div>
      <Message text={error} error />
      <article className="panel wt-panel">
        <div className="wt-toolbar">
          <div><span className="eyebrow">WELLNESS REPORT</span><h3 className="wt-h3">Medication and wellness summary</h3></div>
          <div className="wt-actions">
            <select className="chart-select" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
            </select>
            <button className="button button-primary" onClick={generate} disabled={state === "loading"}>{state === "loading" ? "Generating..." : "Generate report"}</button>
          </div>
        </div>
        {report ? (
          <div>
            <div className="wt-actions wt-report-actions">
              <button className="button button-secondary" onClick={downloadCsv}>Download CSV</button>
              <button className="button button-secondary" onClick={openPrintable}>Open printable version (save as PDF)</button>
            </div>
            <div className="report-grid">
              <div className="report-stat"><span>Wellness score</span><strong>{report.wellness_score.score ?? "-"}</strong></div>
              <div className="report-stat"><span>Adherence</span><strong>{report.adherence.overall.adherence_percent == null ? "-" : `${report.adherence.overall.adherence_percent}%`}</strong></div>
              <div className="report-stat"><span>Doses missed</span><strong>{report.adherence.overall.missed}</strong></div>
              <div className="report-stat"><span>Active days</span><strong>{report.fitness.days_with_activity}</strong></div>
              <div className="report-stat"><span>Total steps</span><strong>{report.fitness.total_steps.toLocaleString()}</strong></div>
              <div className="report-stat"><span>Active minutes</span><strong>{report.fitness.total_active_minutes}</strong></div>
            </div>
            <h4 className="wt-h4">Goals</h4>
            {report.goals.length ? report.goals.map((g, i) => <p className="report-goal" key={i}>{g.title}: {fmt(g.current_value)} / {g.target} {g.unit} ({g.progress_percent}%, {pretty(g.status)})</p>) : <p className="muted">No goals.</p>}
            <h4 className="wt-h4">Readings</h4>
            {report.readings.length ? report.readings.map((r) => <p className="report-goal" key={r.metric}>{pretty(r.metric)}: latest {r.latest} {r.unit}, range {r.min}-{r.max} over {r.readings} readings</p>) : <p className="muted">No numeric readings in this period.</p>}
            <h4 className="wt-h4">Insights</h4>
            <ul className="wt-insights">{report.insights.map((i, k) => <li key={k} className={`wt-insight wt-sev-${i.severity}`}><strong>{i.title}</strong><p>{i.message}</p></li>)}</ul>
            <p className="report-note">{report.disclaimer}</p>
          </div>
        ) : <Empty text="Generate a report to see your adherence, activity, readings, goals and insights in one place." />}
      </article>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Container                                                           */
/* ------------------------------------------------------------------ */

const TABS = [["adherence", "Adherence"], ["goals", "Goals"], ["insights", "Insights & charts"], ["family", "Family"], ["reports", "Reports"]];
/* ------------------------------------------------------------------ */
/* Alerts                                                              */
/* ------------------------------------------------------------------ */

function AlertsPanel({ api, onChange }) {
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await api("alerts");
      setAlerts(data.alerts || []);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, [api]);

  useEffect(() => {
  let cancelled = false;

  const refresh = async () => {
    await Promise.resolve();
    if (!cancelled) {
      await load();
    }
  };

  refresh();
  const timer = setInterval(refresh, 60000);

  return () => {
    cancelled = true;
    clearInterval(timer);
  };
}, [load]);

  const acknowledge = async (id) => {
    try {
      await api(`alerts/${id}/acknowledge`, { method: "POST" });
      await load();
      onChange();
    } catch (e) {
      setError(e.message);
    }
  };

  if (!alerts.length && !error) return null;

  return (
    <article className="panel wt-panel wt-attention">
      <div className="panel-heading">
        <div><span className="eyebrow">ALERTS</span><h3>Needs your attention</h3></div>
        <span className="data-tag">{alerts.length} open</span>
      </div>
      <Message text={error} error />
      <ul className="wt-insights">
        {alerts.map((a) => (
          <li key={a.id} className={`wt-insight wt-sev-${a.severity === "urgent" ? "attention" : a.severity}`}>
            <strong>{pretty(a.rule)}</strong>
            <p>{a.message}</p>
            <small className="muted">{String(a.created_at).slice(0, 16)}</small>
            <div className="wt-actions">
              <button className="button button-secondary" onClick={() => acknowledge(a.id)}>Acknowledge</button>
            </div>
          </li>
        ))}
      </ul>
      <p className="muted">If you feel unwell, contact your doctor or emergency services now. This is not a diagnosis.</p>
    </article>
  );
}

export default function WellnessTracker({ token, activeTab }) {
  const api = useMemo(() => (path, options) => request(token, path, options), [token]);
const [tab, setTab] = useState(activeTab || "adherence");
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState("");

  const loadOverview = useCallback(async () => {
    try { setOverview(await api("overview")); setError(""); }
    catch (e) { setError(e.message); }
  }, [api]);
useEffect(() => {
  let cancelled = false;

  const refresh = async () => {
    await Promise.resolve();
    if (!cancelled) {
      await loadOverview();
    }
  };

  refresh();
  const timer = setInterval(refresh, 60000);

  return () => {
    cancelled = true;
    clearInterval(timer);
  };
}, [loadOverview]);
  const today = overview?.today || [];
  const taken = today.filter((m) => m.status === "taken").length;
  const unread = overview?.unread_notifications || 0;

  return (
    <section id="wellness-tracker" className="section-block wt-root">
      <div className="section-title"><div><span className="eyebrow">MEDICATION &amp; WELLNESS</span><h2>Wellness tracker</h2></div></div>
      {error && <div className="state-banner error" role="alert">{error} <button className="text-button" onClick={loadOverview}>Retry</button></div>}

      <div className="wt-stat-row">
        <div className="wt-stat"><span>Wellness score</span><strong>{overview?.wellness_score?.score ?? "-"}</strong><small>{pretty(overview?.wellness_score?.label || "")}</small></div>
        <div className="wt-stat"><span>7-day adherence</span><strong>{overview?.adherence_7d?.adherence_percent == null ? "-" : `${overview.adherence_7d.adherence_percent}%`}</strong><small>{overview ? `${overview.adherence_7d.missed} missed` : ""}</small></div>
        <div className="wt-stat"><span>Doses today</span><strong>{overview ? `${taken}/${today.length}` : "-"}</strong><small>taken</small></div>
        <div className="wt-stat"><span>Goals completed</span><strong>{overview ? `${overview.goals.completed}/${overview.goals.total}` : "-"}</strong><small>this period</small></div>
      </div>
      <AlertsPanel api={api} onChange={loadOverview} />
      <div className="wt-tabs" role="tablist">
        {TABS.map(([key, label]) => (
          <button key={key} role="tab" aria-selected={tab === key} className={`wt-tab ${tab === key ? "wt-tab-active" : ""}`} onClick={() => setTab(key)}>
            {label}{key === "family" && unread > 0 && <span className="wt-badge">{unread}</span>}
          </button>
        ))}
      </div>

      {tab === "adherence" && <AdherenceTab api={api} onChange={loadOverview} />}
      {tab === "goals" && <GoalsTab api={api} onChange={loadOverview} />}
      {tab === "insights" && <InsightsTab api={api} />}
      {tab === "family" && <FamilyTab api={api} onChange={loadOverview} />}
      {tab === "reports" && <ReportsTab api={api} token={token} />}
      <p className="assistant-disclaimer">Tracking and insights are for awareness only and are not medical advice.</p>
    </section>
  );
}
