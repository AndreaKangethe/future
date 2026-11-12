import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Row = Record<string, unknown>;
type Page = "Overview" | "Assets" | "Findings" | "Infrastructure" | "Intelligence" | "Investigations" | "Reports" | "Integrations" | "Administration";

const cards = [
  ["Assets", "assets", "cyan"], ["Open findings", "open_findings", "amber"],
  ["Critical findings", "critical_findings", "red"], ["Anomalies", "anomalies", "green"],
];
const navigation: Page[] = ["Overview", "Assets", "Findings", "Infrastructure", "Intelligence", "Investigations", "Reports", "Integrations", "Administration"];

function formatDate(value: unknown) {
  if (!value) return "—";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function StateMessage({ kind, message }: { kind: "loading" | "error" | "empty"; message: string }) {
  return <div className={`state ${kind}`} role={kind === "error" ? "alert" : "status"}>{message}</div>;
}

function App() {
  const [token, setToken] = React.useState<string | null>(localStorage.getItem("token"));
  const [page, setPage] = React.useState<Page>("Overview");
  const [email, setEmail] = React.useState("admin@deepsight.local");
  const [password, setPassword] = React.useState("ChangeMe123!");
  const [loginError, setLoginError] = React.useState("");
  const [summary, setSummary] = React.useState<Row | null>(null);
  const [assets, setAssets] = React.useState<Row[]>([]);
  const [findings, setFindings] = React.useState<Row[]>([]);
  const [vulnerabilities, setVulnerabilities] = React.useState<Row[]>([]);
  const [integrations, setIntegrations] = React.useState<Row[]>([]);
  const [audit, setAudit] = React.useState<Row[]>([]);
  const [investigations, setInvestigations] = React.useState<Row[]>([]);
  const [reports, setReports] = React.useState<Row[]>([]);
  const [loading, setLoading] = React.useState<Record<string, boolean>>({});
  const [errors, setErrors] = React.useState<Record<string, string>>({});

  const request = React.useCallback(async (key: string, path: string, setter: (value: any) => void) => {
    if (!token) return;
    setLoading((current) => ({ ...current, [key]: true }));
    setErrors((current) => ({ ...current, [key]: "" }));
    try {
      const response = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
      if (response.status === 401) {
        localStorage.removeItem("token");
        setToken(null);
        throw new Error("Your session has expired. Please sign in again.");
      }
      if (!response.ok) throw new Error(`Unable to load ${key}.`);
      setter(await response.json());
    } catch (error) {
      setErrors((current) => ({ ...current, [key]: error instanceof Error ? error.message : `Unable to load ${key}.` }));
    } finally {
      setLoading((current) => ({ ...current, [key]: false }));
    }
  }, [token]);

  React.useEffect(() => {
    if (!token) return;
    request("summary", "/api/dashboard/summary", setSummary);
    request("assets", "/api/assets", setAssets);
    request("findings", "/api/findings", setFindings);
    request("vulnerabilities", "/api/vulnerabilities", setVulnerabilities);
    request("integrations", "/api/integrations", setIntegrations);
    request("audit", "/api/audit", setAudit);
    request("investigations", "/api/investigations", setInvestigations);
    request("reports", "/api/reports", setReports);
  }, [token, request]);

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setPage("Overview");
  };

  if (!token) return <div className="login"><div className="login-card">
    <div className="brand">DEEPSIGHT<span>◈</span></div>
    <h1>See beyond the surface.</h1>
    <p>Machine Learning-Driven Attack Surface Intelligence and Vulnerability Management Platform.</p>
    <form onSubmit={async (event) => {
      event.preventDefault();
      setLoginError("");
      try {
        const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
        if (!response.ok) throw new Error("Invalid credentials");
        const data = await response.json();
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
      } catch (error) {
        setLoginError(error instanceof Error ? error.message : "Unable to sign in");
      }
    }}>
      <label htmlFor="email">Email<input id="email" value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" required /></label>
      <label htmlFor="password">Password<input id="password" value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" required /></label>
      {loginError && <div className="error" role="alert">{loginError}</div>}
      <button type="submit">Sign in</button>
    </form>
    <small>Development demo credentials are prefilled.</small>
  </div></div>;

  const renderCollection = (key: string, title: string, description: string, items: Row[], renderRow: (item: Row) => React.ReactNode) => (
    <section className="panel" aria-labelledby={`${key}-heading`}>
      <div className="panel-heading"><div><h2 id={`${key}-heading`}>{title}</h2><p className="muted">{description}</p></div><button className="secondary" onClick={() => request(key, `/api/${key}`, key === "investigations" ? setInvestigations : setReports)} aria-label={`Refresh ${title.toLowerCase()}`}>Refresh</button></div>
      {loading[key] && <StateMessage kind="loading" message={`Loading ${title.toLowerCase()}…`} />}
      {!loading[key] && errors[key] && <><StateMessage kind="error" message={errors[key]} /><button className="secondary" onClick={() => request(key, `/api/${key}`, key === "investigations" ? setInvestigations : setReports)}>Try again</button></>}
      {!loading[key] && !errors[key] && items.length === 0 && <StateMessage kind="empty" message={`No ${title.toLowerCase()} yet.`} />}
      {!loading[key] && !errors[key] && items.length > 0 && <div className="table">{items.map(renderRow)}</div>}
    </section>
  );

  const renderWorkspace = () => {
    if (page === "Investigations") return renderCollection("investigations", "Investigations", "Track evidence, ownership, conclusions, and investigation status in one place.", investigations, (item) => <div className="row" key={String(item.id)}><b>{String(item.title)}</b><span className={`status-pill ${String(item.status)}`}>{String(item.status)}</span><span>{item.owner_id ? "Assigned owner" : "Unassigned"}</span><span>Updated {formatDate(item.updated_at)}</span><em>{item.conclusions || "No conclusions"}</em></div>);
    if (page === "Reports") return renderCollection("reports", "Reports", "Review generated evidence summaries and export references.", reports, (item) => <div className="row" key={String(item.id)}><b>{String(item.report_type)}</b><span className={`status-pill ${String(item.status)}`}>{String(item.status)}</span><span>Generated {formatDate(item.generated_at)}</span><span>{Array.isArray(item.evidence_sources) ? `${item.evidence_sources.length} evidence source${item.evidence_sources.length === 1 ? "" : "s"}` : "No sources listed"}</span><em>{item.object_ref || "No export reference"}</em></div>);
    if (page === "Assets") return <section className="panel"><h2>Assets</h2><p className="muted">Identity confidence and exposure evidence from approved sources.</p><div className="table">{assets.map((asset) => <div className="row" key={String(asset.id)}><b>{String(asset.name)}</b><span>{String(asset.asset_type)}</span><span>{String(asset.exposure_status)}</span><span className="cyan">{Math.round(Number(asset.identity_confidence) * 100)}% confidence</span><em>{String(asset.epistemic_class)}</em></div>)}</div></section>;
    if (page === "Findings") return <section className="panel"><h2>Findings</h2><p className="muted">CVSS and contextual risk remain separate evidence fields.</p><div className="table">{findings.map((finding) => <div className="row" key={String(finding.id)}><b>{String(finding.title)}</b><span className={String(finding.severity) === "critical" ? "red" : "amber"}>{String(finding.severity)}</span><span>CVSS {String(finding.cvss_score ?? "—")}</span><span className="cyan">Risk {String(finding.contextual_risk)}</span><em>{String(finding.epistemic_class)}</em></div>)}</div></section>;
    if (page === "Intelligence") return <section className="panel"><h2>Security intelligence</h2><p className="muted">Offline snapshot records are clearly separated from assessed risk.</p><div className="table">{vulnerabilities.map((vulnerability) => <div className="row" key={String(vulnerability.cve_id)}><b>{String(vulnerability.cve_id)}</b><span>{String(vulnerability.severity ?? "unknown")}</span><span>CVSS {String(vulnerability.cvss_score ?? "—")}</span><span>{String(vulnerability.product ?? "—")}</span><em>observed</em></div>)}</div></section>;
    if (page === "Integrations") return <section className="panel"><h2>Integrations</h2><p className="muted">Read-only data sources with masked credentials.</p><div className="table">{integrations.map((integration) => <div className="row" key={String(integration.id)}><b>{String(integration.name)}</b><span>{String(integration.provider)}</span><span>{String(integration.status)}</span><span>credentials masked</span><em>source</em></div>)}</div></section>;
    if (page === "Administration") return <section className="panel"><h2>Audit log</h2><p className="muted">Append-only administrative activity.</p><div className="table">{audit.map((entry) => <div className="row" key={String(entry.id)}><b>{String(entry.action)}</b><span>{String(entry.resource_type)}</span><span>{String(entry.resource_id ?? "—")}</span><span>{formatDate(entry.timestamp)}</span><em>audited</em></div>)}</div></section>;
    return <><section className="cards">{cards.map(([label, key, color]) => <div className="card" key={key}><small>{label}</small><strong className={color}>{summary?.[key] != null ? String(summary[key]) : loading.summary ? "…" : "—"}</strong><span>View evidence →</span></div>)}</section><section className="grid"><div className="panel"><h2>Attack Surface</h2><p className="muted">External exposure and contextual risk, grounded in observed services.</p><div className="surface"><div><b>3</b><span>externally exposed assets</span></div><div><b>12</b><span>exposed services</span></div><div><b className="red">2</b><span>high-risk findings</span></div></div></div><div className="panel"><h2>Recent activity</h2>{["New service observed on app-server-01", "Risk reassessment completed", "Identity evidence reconciled"].map((x) => <div className="activity" key={x}><i />{x}<small>today · observed</small></div>)}</div></section><section className="panel assistant"><h2>Deepsight assistant</h2><p>Ask evidence-grounded questions about assets, changes, exposure, and contextual risk.</p><div className="prompt">Why has the risk of app-server-01 increased? <button type="button">Ask</button></div></section></>;
  };

  return <div className="app">
    <aside><div className="brand">DEEPSIGHT<span>◈</span></div><div className="tagline">See beyond the surface.</div><nav aria-label="Primary navigation">{navigation.map((item) => <button className={`nav ${page === item ? "active" : ""}`} aria-current={page === item ? "page" : undefined} key={item} onClick={() => setPage(item)}>{item}</button>)}</nav><button className="logout" onClick={logout}>Log out</button></aside>
    <main><header><div><h1>{page}</h1><p>Evidence-based infrastructure security intelligence</p></div><div className="header-actions"><div className="status">● Platform healthy</div><button className="logout mobile-logout" onClick={logout}>Log out</button></div></header><div aria-live="polite">{renderWorkspace()}</div></main>
  </div>;
}

createRoot(document.getElementById("root")!).render(<App />);
