import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const cards = [
  ["Assets", "assets", "cyan"], ["Open findings", "open_findings", "amber"],
  ["Critical findings", "critical_findings", "red"], ["Anomalies", "anomalies", "green"],
];

function App() {
  const [token, setToken] = React.useState(localStorage.getItem("token"));
  const [email, setEmail] = React.useState("admin@deepsight.local");
  const [password, setPassword] = React.useState("ChangeMe123!");
  const [loginError, setLoginError] = React.useState("");
  const [summary, setSummary] = React.useState<Record<string, number> | null>(null);
  React.useEffect(() => {
    if (!token) return;
    fetch("/api/dashboard/summary", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : null).then(setSummary).catch(() => setSummary(null));
  }, [token]);
  if (!token) return <div className="login"><div className="login-card"><div className="brand">DEEPSIGHT<span>◈</span></div><h1>See beyond the surface.</h1><p>Machine Learning-Driven Attack Surface Intelligence and Vulnerability Management Platform.</p><form onSubmit={async (event) => {
    event.preventDefault();
    const response = await fetch("/api/auth/login", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({email, password}) });
    if (!response.ok) { setLoginError("Invalid credentials"); return; }
    const data = await response.json(); localStorage.setItem("token", data.access_token); setToken(data.access_token);
  }}><label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} type="email" /></label><label>Password<input value={password} onChange={(e) => setPassword(e.target.value)} type="password" /></label>{loginError && <div className="error">{loginError}</div>}<button type="submit">Sign in</button></form><small>Development demo credentials are prefilled.</small></div></div>;
  return <div className="app">
    <aside><div className="brand">DEEPSIGHT<span>◈</span></div><div className="tagline">See beyond the surface.</div>
      {["Overview","Assets","Findings","Infrastructure","Intelligence","Investigations","Reports","Integrations","Administration"].map((item, i) => <div className={`nav ${i === 0 ? "active" : ""}`} key={item}>{item}</div>)}
    </aside>
    <main><header><div><h1>Overview</h1><p>Evidence-based infrastructure security intelligence</p></div><div className="status">● Platform healthy</div></header>
      <section className="cards">{cards.map(([label, key, color]) => <div className="card" key={key}><small>{label}</small><strong className={color}>{summary?.[key] ?? "—"}</strong><span>View evidence →</span></div>)}</section>
      <section className="grid"><div className="panel"><h2>Attack Surface</h2><p className="muted">External exposure and contextual risk, grounded in observed services.</p><div className="surface"><div><b>3</b><span>externally exposed assets</span></div><div><b>12</b><span>exposed services</span></div><div><b className="red">2</b><span>high-risk findings</span></div></div></div>
      <div className="panel"><h2>Recent activity</h2>{["New service observed on app-server-01","Risk reassessment completed","Identity evidence reconciled"].map((x) => <div className="activity" key={x}><i/> {x}<small>today · observed</small></div>)}</div></section>
      <section className="panel assistant"><h2>Deepsight assistant</h2><p>Ask evidence-grounded questions about assets, changes, exposure, and contextual risk.</p><div className="prompt">Why has the risk of app-server-01 increased? <button>Ask</button></div></section>
    </main>
  </div>
}
createRoot(document.getElementById("root")!).render(<App />);
