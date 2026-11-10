import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function LabelScanner({ token }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const scan = async (event) => {
    event.preventDefault();
    if (!file) return;

    setBusy(true);
    setError("");
    setResult(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch(`${API}/wellness/label-scan`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Scan failed (${res.status}).`);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="label-scanner">
      <form onSubmit={scan} className="import-form">
        <label className="file-picker">
          Choose a medicine label photo
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
          />
        </label>
        <button className="button button-secondary" disabled={!file || busy}>
          {busy ? "Reading label…" : "Read label"}
        </button>
      </form>
      {error && <div className="state-banner error" role="alert">{error}</div>}
      {result && (
        <div className="answer-card" role="status">
          <p style={{ whiteSpace: "pre-wrap" }}>{result.result}</p>
          <small>{result.note}</small>
        </div>
      )}
    </div>
  );
}