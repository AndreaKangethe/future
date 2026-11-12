import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const cards = [
  ["Assets", "assets", "cyan"], ["Open findings", "open_findings", "amber"],
  ["Critical findings", "critical_findings", "red"], ["Anomalies", "anomalies", "green"],
];

function App() {
  const [token, setToken] = React.useState(localStorage.getItem("token"));
  const [page, setPage] = React.useState("Overview");
  const [email, setEmail] = React.useState("admin@deepsight.local");
  const [password, setPassword] = React.useState("ChangeMe123!");
  const [loginError, setLoginError] = React.useState("");
  const [summary, setSummary] = React.useState<Record<string, number> | null>(null);
  const [assets, setAssets] = React.useState<Array<Record<string, string | number>>>([]);
  const [findings, setFindings] = React.useState<Array<Record<string, string | number>>>([]);
  const [vulnerabilities, setVulnerabilities] = React.useState<Array<Record<string, string | number>>>([]);
  const [integrations, setIntegrations] = React.useState<Array<Record<string, string | number>>>([]);
  const [audit, setAudit] = React.useState<Array<Record<string, string | number>>>([]);
  React.useEffect(() => {
    if (!token) return;
    fetch("/api/dashboard/summary", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : null).then(setSummary).catch(() => setSummary(null));
    fetch("/api/assets", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : []).then(setAssets).catch(() => setAssets([]));
    fetch("/api/findings", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : []).then(setFindings).catch(() => setFindings([]));
    fetch("/api/vulnerabilities", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : []).then(setVulnerabilities).catch(() => setVulnerabilities([]));
    fetch("/api/integrations", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : []).then(setIntegrations).catch(() => setIntegrations([]));
    fetch("/api/audit", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : []).then(setAudit).catch(() => setAudit([]));
  }, [token]);
  if (!token) return <div className="login"><div className="login-card"><div className="brand">DEEPSIGHT<span>◈</span></div><h1>See beyond the surface.</h1><p>Machine Learning-Driven Attack Surface Intelligence and Vulnerability Management Platform.</p><form onSubmit={async (event) => {
    event.preventDefault();
    const response = await fetch("/api/auth/login", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({email, password}) });
    if (!response.ok) { setLoginError("Invalid credentials"); return; }
    const data = await response.json(); localStorage.setItem("token", data.access_token); setToken(data.access_token);
  }}><label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} type="email" /></label><label>Password<input value={password} onChange={(e) => setPassword(e.target.value)} type="password" /></label>{loginError && <div className="error">{loginError}</div>}<button type="submit">Sign in</button></form><small>Development demo credentials are prefilled.</small></div></div>;
  const renderWorkspace = () => {
    if (page === "Assets") return <section className="panel"><h2>Assets</h2><p className="muted">Identity confidence and exposure evidence from approved sources.</p><div className="table">{assets.map((asset) => <div className="row" key={String(asset.id)}><b>{asset.name}</b><span>{asset.asset_type}</span><span>{asset.exposure_status}</span><span className="cyan">{Math.round(Number(asset.identity_confidence) * 100)}% confidence</span><em>{asset.epistemic_class}</em></div>)}</div></section>;
    if (page === "Findings") return <section className="panel"><h2>Findings</h2><p className="muted">CVSS and contextual risk remain separate evidence fields.</p><div className="table">{findings.map((finding) => <div className="row" key={String(finding.id)}><b>{finding.title}</b><span className={String(finding.severity) === "critical" ? "red" : "amber"}>{finding.severity}</span><span>CVSS {finding.cvss_score ?? "—"}</span><span className="cyan">Risk {finding.contextual_risk}</span><em>{finding.epistemic_class}</em></div>)}</div></section>;
    if (page === "Intelligence") return <section className="panel"><h2>Security intelligence</h2><p className="muted">Offline snapshot records are clearly separated from assessed risk.</p><div className="table">{vulnerabilities.map((vulnerability) => <div className="row" key={String(vulnerability.cve_id)}><b>{vulnerability.cve_id}</b><span>{vulnerability.severity ?? "unknown"}</span><span>CVSS {vulnerability.cvss_score ?? "—"}</span><span>{vulnerability.product ?? "—"}</span><em>observed</em></div>)}</div></section>;
    if (page === "Integrations") return <section className="panel"><h2>Integrations</h2><p className="muted">Read-only data sources with masked credentials.</p><div className="table">{integrations.map((integration) => <div className="row" key={String(integration.id)}><b>{integration.name}</b><span>{integration.provider}</span><span>{integration.status}</span><span>credentials masked</span><em>source</em></div>)}</div></section>;
    if (page === "Administration") return <section className="panel"><h2>Audit log</h2><p className="muted">Append-only administrative activity.</p><div className="table">{audit.map((entry) => <div className="row" key={String(entry.id)}><b>{entry.action}</b><span>{entry.resource_type}</span><span>{entry.resource_id ?? "—"}</span><span>{entry.timestamp}</span><em>audited</em></div>)}</div></section>;
    return <><section className="cards">{cards.map(([label, key, color]) => <div className="card" key={key}><small>{label}</small><strong className={color}>{summary?.[key] ?? "—"}</strong><span>View evidence →</span></div>)}</section><section className="grid"><div className="panel"><h2>Attack Surface</h2><p className="muted">External exposure and contextual risk, grounded in observed services.</p><div className="surface"><div><b>3</b><span>externally exposed assets</span></div><div><b>12</b><span>exposed services</span></div><div><b className="red">2</b><span>high-risk findings</span></div></div></div><div className="panel"><h2>Recent activity</h2>{["New service observed on app-server-01","Risk reassessment completed","Identity evidence reconciled"].map((x) => <div className="activity" key={x}><i/> {x}<small>today · observed</small></div>)}</div></section><section className="panel assistant"><h2>Deepsight assistant</h2><p>Ask evidence-grounded questions about assets, changes, exposure, and contextual risk.</p><div className="prompt">Why has the risk of app-server-01 increased? <button>Ask</button></div></section></>;
  };
  return <div className="app">
    <aside><div className="brand">DEEPSIGHT<span>◈</span></div><div className="tagline">See beyond the surface.</div>
      {["Overview","Assets","Findings","Infrastructure","Intelligence","Investigations","Reports","Integrations","Administration"].map((item) => <div className={`nav ${page === item ? "active" : ""}`} key={item} onClick={() => setPage(item)}>{item}</div>)}
    </aside>
    <main><header><div><h1>{page}</h1><p>Evidence-based infrastructure security intelligence</p></div><div className="status">● Platform healthy</div></header>
      {renderWorkspace()}
    </main>
  </div>
}
createRoot(document.getElementById("root")!).render(<App />);
