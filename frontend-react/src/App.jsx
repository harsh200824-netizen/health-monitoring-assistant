//frontend-react/src/App.jsx
import { useCallback, useEffect, useState } from "react";
import "./App.css";
import Auth from "./Auth";
import WellnessTracker from "./WellnessTracker";
import VoiceButton from "./VoiceButton";
import LabelScanner from "./LabelScanner";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const apiFetch = (path, options = {}, token) => {
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(`${API}/${path}`, {
    ...options,
    headers,
  });
};
const NAV = ["Overview", "Fitness", "Medications", "Health goals", "Import data", "Reports", "AI assistant", "Wellness tracker", "Family"];
const pretty = (value) => String(value ?? "—").replaceAll("_", " ");


  function App() {
  const [token, setToken] = useState("");
  const [summary, setSummary] = useState(null), [, setAnalytics] = useState(null), [insights, setInsights] = useState(null);
  const [medications, setMedications] = useState([]), [doseHistory, setDoseHistory] = useState([]), [metrics, setMetrics] = useState([]);
  const [fitnessActivities, setFitnessActivities] = useState([]), [fitnessSummary, setFitnessSummary] = useState(null), [goalProgress, setGoalProgress] = useState([]);
  const [apiStatus, setApiStatus] = useState("Checking"), [loading, setLoading] = useState(true), [loadError, setLoadError] = useState("");
  const [section, setSection] = useState("Overview"), [menuOpen, setMenuOpen] = useState(false);
  const [chartMetric, setChartMetric] = useState("");
  const [fitnessMessage, setFitnessMessage] = useState(""), [savingFitness, setSavingFitness] = useState(false);
  const [fitnessForm, setFitnessForm] = useState({ activity_type: "walking", duration_minutes: "", steps: "", distance_km: "", calories_burned: "", sleep_hours: "", notes: "" });
  const [question, setQuestion] = useState(""), [answer, setAnswer] = useState(""), [loadingAI, setLoadingAI] = useState(false), [aiError, setAiError] = useState("");
  const [report, setReport] = useState(null), [reportState, setReportState] = useState("idle"), [reportError, setReportError] = useState("");
  const [file, setFile] = useState(null), [importState, setImportState] = useState(null), [importError, setImportError] = useState(""), [importing, setImporting] = useState(false);
  const [interactionText, setInteractionText] = useState(""), [interaction, setInteraction] = useState(null), [interactionError, setInteractionError] = useState(""), [checkingInteractions, setCheckingInteractions] = useState(false);
  const [goalForm, setGoalForm] = useState({ goal_type: "", target_value: "", unit: "" }), [goalMessage, setGoalMessage] = useState(""), [savingGoal, setSavingGoal] = useState(false);

 const loadDashboard = useCallback(async () => {
    setLoading(true); setLoadError("");
    try {
      const paths = ["health/summary", "analytics", "insights", "medications", "dose-history", "health-metrics", "fitness-activities", "fitness-summary", "health-goals/progress"];
      const responses = await Promise.all(
  paths.map((path) => apiFetch(path, {}, token))
);
      const failed = responses.find((response) => !response.ok);
      if (failed) throw new Error(`Dashboard data request failed (${failed.status}).`);
      const [s, a, i, m, d, h, f, fs, g] = await Promise.all(responses.map((response) => response.json()));
      setSummary(s); setAnalytics(a); setInsights(i); setMedications(m); setDoseHistory(d); setMetrics(h); setFitnessActivities(f); setFitnessSummary(fs); setGoalProgress(g);
    } catch (error) { setLoadError(error.message || "Could not load dashboard data. Check the API connection."); }
    finally { setLoading(false); }
 }, [token]);
 const checkAPI = useCallback(async () => {
  try {
    const res = await fetch(`${API}/health`);
    const data = await res.json();
    setApiStatus(res.ok && data.status === "healthy" ? "Connected" : "Unavailable");
  } catch {
    setApiStatus("Unavailable");
  }
 }, []);
 useEffect(() => {
  let cancelled = false;

  const runChecks = async () => {
    await Promise.resolve();

    if (cancelled) return;

    try {
      const res = await fetch(`${API}/health`);
      const data = await res.json();

      if (!cancelled) {
        setApiStatus(
          res.ok && data.status === "healthy"
            ? "Connected"
            : "Unavailable"
        );
      }
    } catch {
      if (!cancelled) {
        setApiStatus("Unavailable");
      }
    }

    if (cancelled) return;

    if (token) {
      await loadDashboard();
    } else {
      setLoading(false);
    }
  };

  runChecks();

  return () => {
    cancelled = true;
  };
}, [token, loadDashboard]);
  const addFitnessActivity = async (event) => {
  event.preventDefault();
  setFitnessMessage("");
  setSavingFitness(true);

  const payload = {
    activity_type: fitnessForm.activity_type.trim(),
    duration_minutes: fitnessForm.duration_minutes === "" ? null : Number(fitnessForm.duration_minutes),
    steps: fitnessForm.steps === "" ? null : Number(fitnessForm.steps),
    distance_km: fitnessForm.distance_km === "" ? null : Number(fitnessForm.distance_km),
    calories_burned: fitnessForm.calories_burned === "" ? null : Number(fitnessForm.calories_burned),
    sleep_hours: fitnessForm.sleep_hours === "" ? null : Number(fitnessForm.sleep_hours),
    notes: fitnessForm.notes.trim(),
  };

  try {
    const res = await apiFetch("fitness-activities", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }, token);
  
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not save activity.");

  
setFitnessMessage(data.message || "Activity saved successfully.");

setFitnessForm({
  activity_type: "walking",
  duration_minutes: "",
  steps: "",
  distance_km: "",
  calories_burned: "",
  sleep_hours: "",
  notes: "",
});

// Activity save ho chukki hai.
// Dashboard refresh fail hove taan success message overwrite na hove.
try {
  await loadDashboard();
} catch (refreshError) {
  console.error("Dashboard refresh failed:", refreshError);
}
  } catch (error) {
    setFitnessMessage(error.message || "Could not save activity.");
  } finally {
    setSavingFitness(false);
  }
};


const askAI = async (event) => {
  event.preventDefault();
  if (!question.trim()) return;

  setLoadingAI(true);
  setAnswer("");
  setAiError("");

  try {
    const res = await apiFetch("ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question.trim() }),
    }, token);

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Assistant request failed (${res.status}).`);

    setAnswer(data.answer);
  } catch (error) {
    setAiError(error.message);
  } finally {
    setLoadingAI(false);
  }
};

const generateReport = async () => {
  setReportState("loading");
  setReportError("");

  try {
    const res = await apiFetch("health-report", {}, token);
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || `Report request failed (${res.status}).`);

    setReport(data);
    setReportState("success");
  } catch (error) {
    setReportError(error.message);
    setReportState("error");
  }
};

const importData = async (event) => {
  event.preventDefault();
  if (!file) return;

  setImporting(true);
  setImportError("");
  setImportState(null);

  try {
    const form = new FormData();
    form.append("file", file);

    const res = await apiFetch("health-data/import", {
      method: "POST",
      body: form,
    }, token);

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Import failed (${res.status}).`);

    setImportState(data);
    setFile(null);
    event.target.reset();
    await loadDashboard();
  } catch (error) {
    setImportError(error.message);
  } finally {
    setImporting(false);
  }
};

const checkInteractions = async (event) => {
  event.preventDefault();

  const names = interactionText
    .split(/[,\n]/)
    .map((name) => name.trim())
    .filter(Boolean);

  if (!names.length) {
    setInteractionError("Enter at least one medication name.");
    return;
  }

  setInteraction(null);
  setInteractionError("");
  setCheckingInteractions(true);

  try {
    const res = await apiFetch("medication-interactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ medications: names }),
    }, token);

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Check failed (${res.status}).`);

    setInteraction(data);
  } catch (error) {
    setInteractionError(error.message);
  } finally {
    setCheckingInteractions(false);
  }
};

const addGoal = async (event) => {
  event.preventDefault();
  setSavingGoal(true);
  setGoalMessage("");

  try {
    const res = await apiFetch("health-goals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...goalForm,
        target_value: Number(goalForm.target_value),
      }),
    }, token);

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Could not add goal (${res.status}).`);

    setGoalMessage(data.message || "Goal added successfully.");
    setGoalForm({ goal_type: "", target_value: "", unit: "" });
    await loadDashboard();
  } catch (error) {
    setGoalMessage(error.message);
  } finally {
    setSavingGoal(false);
  }
};

const metricTypes = [...new Set(metrics.map((metric) => metric.metric_type))];

const selectedMetric = metricTypes.includes(chartMetric)
  ? chartMetric
  : metricTypes[0];

const chartData = [...metrics]
  .filter((item) => item.metric_type === selectedMetric)
  .reverse()
  .slice(-14)
  .map((item) => ({
    ...item,
    numeric: Number(item.value),
  }))
  .filter((item) => Number.isFinite(item.numeric));

let chart = null;

if (chartData.length > 0) {
  const min = Math.min(...chartData.map((item) => item.numeric));
  const max = Math.max(...chartData.map((item) => item.numeric));
  const range = max - min || 1;

  chart = {
    data: chartData,
    points: chartData
      .map((item, index) => {
        const x = chartData.length === 1
          ? 50
          : 12 + index * (76 / (chartData.length - 1));

        const y = 92 - ((item.numeric - min) / range) * 66;

        return `${x},${y}`;
      })
      .join(" "),
  };
}
  const setCurrentSection = (name) => { setSection(name); setMenuOpen(false); const targetId = name === "Family" ? "wellness-tracker" : name.replaceAll(" ", "-").toLowerCase(); document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" }); };
  if (!token) {
    return <Auth onLogin={setToken} />;
  }
  return <div className="app-shell">
    
    <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
      <a className="brand" href="#overview" onClick={() => setCurrentSection("Overview")}><span className="brand-mark">✳</span><span>pulse<span className="brand-accent">care</span><small>HEALTH INTELLIGENCE</small></span></a>
      <div className="nav-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{NAV.map((item, index) => <button key={item} className={`nav-item ${section === item ? "active" : ""}`} onClick={() => setCurrentSection(item)}><span className="nav-icon">{["◫", "⌁", "✚", "◎", "⇧", "▤", "✧", "♡", "♧"][index]}</span>{item}</button>)}</nav>
      <div className="sidebar-bottom"><div className="privacy-card"><span className="shield">◈</span><strong>Your health, protected</strong><p>Your health records stay in your connected workspace.</p></div><div className="profile"><div className="avatar">H</div><div><strong>Health profile</strong><span>Personal workspace</span></div><span className="profile-more">···</span></div></div>
    </aside>
    {menuOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
    <main className="main-area">
      <header className="topbar"><button className="menu-toggle" aria-label="Open menu" onClick={() => setMenuOpen(true)}>☰</button><div className="breadcrumb">Workspace <span>/</span> <strong>{section}</strong></div><div className="topbar-right"><div className="api-status"><span className={`status-dot ${apiStatus === "Connected" ? "connected" : ""}`} />{apiStatus === "Connected" ? "System operational" : apiStatus}</div><div className="top-avatar" aria-label="Profile">H</div></div></header>
      <div className="content-wrap">
        <div className="page-heading"><div><div className="eyebrow">{new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date()).toUpperCase()}</div><h1>Your health at a glance<span>.</span></h1><p>A clear view of your health data and daily activity.</p></div><button className="button button-secondary refresh-button" onClick={() => { checkAPI(); loadDashboard(); }} disabled={loading}>↻ <span>{loading ? "Refreshing…" : "Refresh data"}</span></button></div>
        {loadError && <div className="state-banner error" role="alert">{loadError} <button className="text-button" onClick={loadDashboard}>Retry</button></div>}
        <section id="overview" className="section-block"><div className="section-title"><div><span className="eyebrow">OVERVIEW</span><h2>Health snapshot</h2></div><span className="updated-label">{loading ? "Syncing data…" : "Based on your recorded data"}</span></div>
          <div className="metric-grid">
            {[{ label: "Active medications", value: summary?.active_medications, icon: "✚", tone: "mint", note: "Current prescriptions" }, { label: "Doses recorded", value: summary?.dose_records, icon: "◷", tone: "blue", note: "Dose history entries" }, { label: "Health readings", value: summary?.health_metric_records, icon: "⌁", tone: "purple", note: "Metrics in your record" }, { label: "Fitness activities", value: fitnessSummary?.total_activities, icon: "↗", tone: "orange", note: "Activities recorded" }].map((metric) => <article className="metric-card" key={metric.label}><div className={`metric-icon ${metric.tone}`}>{metric.icon}</div><div className="metric-label">{metric.label}</div><div className="metric-value">{loading ? <span className="skeleton" /> : metric.value ?? "—"}</div><div className="metric-note">{metric.note}</div></article>)}
          </div>
          <div className="overview-grid"><article className="panel chart-panel"><div className="panel-heading"><div><span className="eyebrow">YOUR RECORD</span><h3>Health metric history</h3></div>{metricTypes.length > 0 && <label className="chart-select-label"><span className="sr-only">Choose metric type</span><select className="chart-select" value={selectedMetric} onChange={(e) => setChartMetric(e.target.value)}>{metricTypes.map((type) => <option key={type} value={type}>{pretty(type)}</option>)}</select></label>}</div>
            {chart ? <><div className="chart-wrap"><div className="chart-y-labels"><span>{Math.max(...chart.data.map((item) => item.numeric))} {chart.data.at(-1).unit}</span><span>{(Math.max(...chart.data.map((item) => item.numeric)) + Math.min(...chart.data.map((item) => item.numeric))) / 2}</span><span>{Math.min(...chart.data.map((item) => item.numeric))}</span></div><svg className="trend-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`Trend of recorded ${selectedMetric} measurements`}><defs><linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#44d7c2" stopOpacity=".22"/><stop offset="100%" stopColor="#44d7c2" stopOpacity="0"/></linearGradient></defs><path d={`M ${chart.points.split(" ").join(" L ")} L 88 100 L 12 100 Z`} fill="url(#trendFill)"/><polyline points={chart.points} fill="none" stroke="#51d9c8" strokeWidth="1.4" vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round"/>{chart.data.map((item, i) => <circle key={`${item.id}-${i}`} cx={chart.data.length === 1 ? 50 : 12 + i * (76 / (chart.data.length - 1))} cy={92 - ((item.numeric - Math.min(...chart.data.map((entry) => entry.numeric))) / (Math.max(...chart.data.map((entry) => entry.numeric)) - Math.min(...chart.data.map((entry) => entry.numeric)) || 1)) * 66} r="1.8" fill="#51d9c8" stroke="#101a28" strokeWidth="1"/> )}</svg></div><div className="chart-caption"><span>{chart.data[0].recorded_at}</span><span>{chart.data.length} {pretty(selectedMetric)} readings · {chart.data.at(-1).unit || "recorded value"}</span><span>{chart.data.at(-1).recorded_at}</span></div></> : <EmptyState loading={loading} text={metricTypes.length ? "No numeric readings for this metric yet." : "Health readings will appear here once recorded."} />}
          </article><article className="panel insight-panel"><div className="panel-heading"><div><span className="eyebrow">PERSONALIZED</span><h3>Health insights</h3></div><span className="sparkle">✧</span></div>{insights?.insights?.length ? <ul className="insight-list">{insights.insights.map((item, index) => <li key={index}><span className="insight-bullet">✧</span>{item}</li>)}</ul> : <EmptyState loading={loading} text="No insights available yet." />}</article></div>
        </section>
        <section id="fitness" className="section-block"><div className="section-title"><div><span className="eyebrow">MOVEMENT & REST</span><h2>Fitness activity</h2></div></div><div className="summary-strip">{[{ label: "Total steps", value: fitnessSummary?.total_steps, unit: "steps" }, { label: "Active time", value: fitnessSummary?.total_duration_minutes, unit: "min" }, { label: "Distance", value: fitnessSummary ? Number(fitnessSummary.total_distance_km).toFixed(1) : null, unit: "km" }, { label: "Calories", value: fitnessSummary?.total_calories, unit: "kcal" }, { label: "Sleep", value: fitnessSummary ? Number(fitnessSummary.total_sleep_hours).toFixed(1) : null, unit: "hrs" }].map((item) => <div className="summary-item" key={item.label}><span>{item.label}</span><strong>{loading ? "—" : item.value ?? "—"}<small> {item.unit}</small></strong></div>)}</div>
          <div className="two-column"><article className="panel"><div className="panel-heading"><div><span className="eyebrow">LOG A SESSION</span><h3>Add fitness activity</h3></div></div><form className="form-grid" onSubmit={addFitnessActivity}><label className="field span-two">Activity type<input value={fitnessForm.activity_type} onChange={(e) => setFitnessForm({ ...fitnessForm, activity_type: e.target.value })} required maxLength="50" placeholder="Walking, running, cycling…" /></label>{[["duration_minutes", "Duration", "min", "1440", "1"], ["steps", "Steps", "steps", "200000", "1"], ["distance_km", "Distance", "km", "1000", "0.1"], ["calories_burned", "Calories", "kcal", "20000", "1"], ["sleep_hours", "Sleep", "hrs", "24", "0.1"]].map(([key, label, unit, max, step]) => <label className="field" key={key}>{label} <span className="unit">({unit})</span><input type="number" min="0" max={max} step={step} value={fitnessForm[key]} onChange={(e) => setFitnessForm({ ...fitnessForm, [key]: e.target.value })} /></label>)}<label className="field span-two">Notes <textarea rows="2" maxLength="500" value={fitnessForm.notes} onChange={(e) => setFitnessForm({ ...fitnessForm, notes: e.target.value })} placeholder="Optional notes" /></label><div className="form-footer span-two"><button className="button button-primary" disabled={savingFitness}>{savingFitness ? "Saving…" : "Save activity"}</button>{fitnessMessage && <span className="form-message" role="status">{fitnessMessage}</span>}</div></form></article><article className="panel"><div className="panel-heading"><div><span className="eyebrow">RECENT</span><h3>Activity history</h3></div></div><DataTable loading={loading} rows={fitnessActivities.slice(0, 8)} empty="No fitness activities recorded yet." columns={[["activity_type", "Activity"], ["duration_minutes", "Minutes"], ["steps", "Steps"], ["recorded_at", "Recorded"]]} /></article></div>
        </section>
        <section id="medications" className="section-block"><div className="section-title"><div><span className="eyebrow">CARE ROUTINE</span><h2>Medication management</h2></div></div><div className="two-column"><article className="panel"><div className="panel-heading"><div><span className="eyebrow">CURRENT PLAN</span><h3>Active medications</h3></div><span className="data-tag">{medications.length} active</span></div><DataTable loading={loading} rows={medications} empty="No active medications recorded." columns={[["name", "Medication"], ["dosage", "Dosage"], ["time", "Scheduled time"]]} /></article><article className="panel"><div className="panel-heading"><div><span className="eyebrow">RECENT LOGS</span><h3>Dose history</h3></div></div><DataTable loading={loading} rows={doseHistory.slice(0, 8)} empty="No dose records available." columns={[["name", "Medication"], ["dosage", "Dosage"], ["taken_at", "Taken at"]]} /></article></div><article className="panel interaction-panel"><div className="panel-heading"><div><span className="eyebrow">SAFETY CHECK</span><h3>Medication interaction check</h3></div></div><p className="muted">Enter medication names separated by commas. This tool is for awareness only.</p><form className="interaction-form" onSubmit={checkInteractions}><label className="sr-only" htmlFor="interaction-meds">Medication names</label><textarea id="interaction-meds" rows="2" value={interactionText} onChange={(e) => setInteractionText(e.target.value)} placeholder="For example: medication A, medication B" required /><button className="button button-secondary" disabled={checkingInteractions}>{checkingInteractions ? "Checking…" : "Check medications"}</button></form><div className="warning-note"><span>ⓘ</span><p>Results may be unverified. This checker is not connected to a verified interaction database. An empty result does not mean medications are safe to take together. Ask a pharmacist or doctor to review your medication list.</p></div>{interactionError && <div className="state-banner error" role="alert">{interactionError}</div>}{interaction && <div className="interaction-result" role="status"><strong>{interaction.status === "not_verified" ? "Unable to verify interactions" : pretty(interaction.status)}</strong><p>{interaction.message}</p>{interaction.medications_checked?.length > 0 && <small>Submitted: {interaction.medications_checked.join(", ")}</small>}</div>}</article></section>
        <section id="health-goals" className="section-block"><div className="section-title"><div><span className="eyebrow">YOUR TARGETS</span><h2>Health goals</h2></div></div><div className="two-column"><article className="panel"><div className="panel-heading"><div><span className="eyebrow">PROGRESS</span><h3>Goal tracking</h3></div></div>{goalProgress.length ? <div className="goal-list">{goalProgress.map((goal) => <div className="goal-item" key={goal.id}><div className="goal-top"><strong>{pretty(goal.goal_type)}</strong><span>{goal.progress_percent}%</span></div><div className="goal-values">{goal.current_value} / {goal.target_value} {goal.unit}</div><progress value={goal.progress_percent} max="100" aria-label={`${pretty(goal.goal_type)} progress`} /><div className="goal-foot"><span>{goal.completed ? "Completed" : "In progress"}</span><span>Target {goal.target_value} {goal.unit}</span></div></div>)}</div> : <EmptyState loading={loading} text="No health goals added yet." />}</article><article className="panel"><div className="panel-heading"><div><span className="eyebrow">SET AN INTENTION</span><h3>Create a health goal</h3></div></div><form className="form-grid" onSubmit={addGoal}><label className="field span-two">Goal type<input value={goalForm.goal_type} onChange={(e) => setGoalForm({ ...goalForm, goal_type: e.target.value })} required maxLength="50" placeholder="Daily steps, weekly activity…" /></label><label className="field">Target value<input type="number" min="0.01" max="1000000" step="any" value={goalForm.target_value} onChange={(e) => setGoalForm({ ...goalForm, target_value: e.target.value })} required /></label><label className="field">Unit<input value={goalForm.unit} onChange={(e) => setGoalForm({ ...goalForm, unit: e.target.value })} required maxLength="30" placeholder="steps, minutes…" /></label><div className="form-footer span-two"><button className="button button-primary" disabled={savingGoal}>{savingGoal ? "Adding…" : "Add goal"}</button>{goalMessage && <span className="form-message" role="status">{goalMessage}</span>}</div></form></article></div></section>
        <section id="import-data" className="section-block"><div className="section-title"><div><span className="eyebrow">DATA MANAGEMENT</span><h2>Import health data</h2></div></div><article className="panel import-panel"><div className="import-copy"><div className="upload-icon">⇧</div><div><h3>Bring your records together</h3><p>Import health metric records from a JSON, CSV, or XML file. Files must be under 2 MB.</p><span className="format-pills"><i>JSON</i><i>CSV</i><i>XML</i></span></div></div><form onSubmit={importData} className="import-form"><label className="file-picker">Choose a data file<input type="file" accept=".json,.csv,.xml,application/json,text/csv,application/xml,text/xml" onChange={(e) => setFile(e.target.files?.[0] || null)} required /></label><button className="button button-primary" disabled={!file || importing}>{importing ? "Importing…" : "Import records"}</button></form>{importError && <div className="state-banner error" role="alert">{importError}</div>}{importState && <div className="import-result" role="status"><strong>{importState.message}</strong><span>{importState.imported_records} imported</span><span>{importState.skipped_records} skipped</span><small>{importState.filename} · {importState.format?.toUpperCase()}</small></div>}</article></section>
        <section id="reports" className="section-block"><div className="section-title"><div><span className="eyebrow">YOUR RECORD, SUMMARIZED</span><h2>Health reports</h2></div><button className="button button-primary" onClick={generateReport} disabled={reportState === "loading"}>{reportState === "loading" ? "Generating…" : "Generate report"}</button></div>{reportError && <div className="state-banner error" role="alert">{reportError}</div>}{report ? <article className="panel report-panel"><div className="report-header"><div><span className="eyebrow">GENERATED REPORT</span><h3>{report.report_title}</h3></div><span className="report-date">{report.generated_at ? new Date(report.generated_at).toLocaleString() : ""}</span></div><div className="report-grid">{Object.entries(report.health_summary || {}).map(([key, value]) => <div className="report-stat" key={key}><span>{pretty(key)}</span><strong>{value}</strong></div>)}{Object.entries(report.fitness_summary || {}).map(([key, value]) => <div className="report-stat" key={key}><span>{pretty(key)}</span><strong>{value}</strong></div>)}</div><h4>Goal progress</h4>{report.goal_progress?.length ? report.goal_progress.map((goal) => <p className="report-goal" key={goal.id}>{pretty(goal.goal_type)}: {goal.current_value} / {goal.target_value} {goal.unit} ({goal.progress_percent}%)</p>) : <p className="muted">No goals available in this report.</p>}<p className="report-note">{report.note}</p></article> : <article className="panel report-placeholder"><span className="report-icon">▤</span><div><h3>{reportState === "loading" ? "Preparing your report…" : "A readable summary of your health data"}</h3><p>Generate a report to see your recorded metrics, activity summary, and goal progress in one place.</p></div></article>}</section>
        <section id="ai-assistant" className="section-block"><div className="section-title"><div><span className="eyebrow">AI HEALTH ASSISTANT</span><h2>Ask about your health record</h2></div></div><article className="panel assistant-panel"><div className="assistant-orb">✧</div><div className="assistant-intro"><h3>How can I help?</h3><p>Ask about information in your stored record or a general health topic.</p></div><form onSubmit={askAI} className="assistant-form"><label className="sr-only" htmlFor="health-question">Your question</label><textarea id="health-question" rows="3" maxLength="500" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="For example: What medications are in my record?" required /><VoiceButton onText={(text) => setQuestion(text)} disabled={loadingAI} /> <button className="button button-primary" disabled={loadingAI || !question.trim()}>{loadingAI ? "Thinking…" : "Ask assistant  →"}</button></form>{aiError && <div className="state-banner error" role="alert">{aiError}</div>}{answer && <div className="answer-card" aria-live="polite"><div className="answer-heading"><span className="answer-avatar">✧</span><strong>Assistant response</strong></div><p>{answer}</p><small>AI generated · For informational purposes only</small></div>}<p className="assistant-disclaimer">AI responses can be incomplete or inaccurate and are not a substitute for professional medical advice.</p><LabelScanner token={token} /></article></section>
        <section className="section-block records-section"><div className="section-title"><div><span className="eyebrow">HEALTH RECORD</span><h2>Recent measurements</h2></div></div><article className="panel"><DataTable loading={loading} rows={metrics.slice(0, 10)} empty="No health metrics recorded." columns={[["metric_type", "Metric"], ["value", "Value"], ["unit", "Unit"], ["recorded_at", "Recorded at"]]} /></article></section>
        <WellnessTracker token={token} activeTab={section === "Family" ? "family" : undefined} />
        <footer className="app-footer"><span>Pulsecare · Personal health workspace</span><span>Health information is for tracking purposes and is not a diagnosis.</span></footer>
      </div>
    </main>
  </div>;
}
 
function EmptyState({ loading, text }) { return <div className="empty-state">{loading ? <><span className="spinner" />Loading your data…</> : <><span className="empty-symbol">⌁</span>{text}</>}</div>; }
function DataTable({ rows, columns, empty, loading }) { if (loading || !rows.length) return <EmptyState loading={loading} text={empty} />; return <div className="table-wrap"><table><thead><tr>{columns.map(([, title]) => <th key={title}>{title}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row.id ?? index}>{columns.map(([key]) => <td key={key}>{row[key] == null || row[key] === "" ? "—" : key.includes("recorded_at") || key.includes("taken_at") ? String(row[key]).replace("T", " ").slice(0, 16) : pretty(row[key])}</td>)}</tr>)}</tbody></table></div>; }
 
export default App;
