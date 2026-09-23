import { useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api, clearToken, getToken, login } from "./api";

type Decision = {
  request_id: string;
  decision: string;
  risk_score: number;
  hard_violation: boolean;
  reasons: string[];
  checks: Record<string, string>;
  algorithm_results?: Record<string, string>;
  timestamp?: string;
};

const NAV = [
  ["/", "Overview"],
  ["/assets", "Assets"],
  ["/changes", "Live Changes"],
  ["/approvals", "Approvals"],
  ["/state", "Process State"],
  ["/policies", "Policies"],
  ["/incidents", "Incidents"],
  ["/recovery", "Recovery"],
  ["/research", "Research"],
  ["/admin", "Administration"],
];

function Login() {
  const [username, setUsername] = useState("engineer-a");
  const [password, setPassword] = useState("lab-engineer-change-me");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }
  return (
    <div className="login">
      <form onSubmit={onSubmit}>
        <div className="brand">PLC Change Assurance</div>
        <p className="sub">Lab identities only. These are not production credentials.</p>
        <label>Username</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} />
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="error">{error}</p>}
        <button className="primary" type="submit">Sign in</button>
      </form>
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  return (
    <div className="app">
      <aside className="nav">
        <div className="brand">
          Change Assurance
          <small>Cyber-physical gateway</small>
        </div>
        {NAV.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
            {label}
          </NavLink>
        ))}
        <button
          className="linkish"
          onClick={() => {
            clearToken();
            navigate("/login");
          }}
        >
          Sign out
        </button>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

function Overview() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api("/api/overview").then(setData).catch(() => setData(null));
  }, []);
  if (!data) return <p>Loading plant overview…</p>;
  return (
    <>
      <h1>Overview</h1>
      <p className="sub">
        Mode {data.operating_mode} · enforcement {data.enforcement_enabled ? "on" : "off"} · lab {String(data.lab_mode)}
      </p>
      <div className="grid">
        <div className="card"><h3>PLCs</h3><div className="metric">{data.plc_count}</div></div>
        <div className="card"><h3>Blocked</h3><div className="metric">{data.blocked_changes}</div></div>
        <div className="card"><h3>Held</h3><div className="metric">{data.held_changes}</div></div>
        <div className="card"><h3>Allowed</h3><div className="metric">{data.allowed_changes}</div></div>
        <div className="card"><h3>Incidents</h3><div className="metric">{data.active_incidents}</div></div>
        <div className="card"><h3>Policy</h3><div className="metric">{data.policy_status}</div></div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Active process states</h3>
        <pre>{JSON.stringify(data.active_process_states, null, 2)}</pre>
        <h3>Sensors</h3>
        <pre>{JSON.stringify(data.sensors, null, 2)}</pre>
      </div>
    </>
  );
}

function Assets() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api<any[]>("/api/plcs").then(setRows);
  }, []);
  return (
    <>
      <h1>Assets</h1>
      <p className="sub">Incomplete fields are allowed; missing data is shown as empty rather than guessed.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>PLC</th><th>Vendor</th><th>IP</th><th>State</th><th>Criticality</th></tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.plc_id}>
                <td><NavLink to={`/assets/${row.plc_id}`}>{row.plc_id}</NavLink></td>
                <td>{row.vendor}</td>
                <td>{row.ip}</td>
                <td>{row.state}</td>
                <td>{row.criticality}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function AssetDetail() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api(`/api/plcs/${id}`).then(setData);
  }, [id]);
  if (!data) return <p>Loading asset…</p>;
  return (
    <>
      <h1>{data.plc_id}</h1>
      <p className="sub">{data.vendor} {data.model} · {data.ip} · {data.protocol}</p>
      <div className="two">
        <div className="card">
          <h3>Current state</h3>
          <div className="metric">{data.state}</div>
          <h3>Parameters</h3>
          <pre>{JSON.stringify(data.parameters, null, 2)}</pre>
        </div>
        <div className="card">
          <h3>Process connections</h3>
          <pre>{JSON.stringify(data.dependencies, null, 2)}</pre>
          <p>Policy coverage: {String(data.policy_coverage)}</p>
        </div>
      </div>
    </>
  );
}

function Changes() {
  const [rows, setRows] = useState<Decision[]>([]);
  const [open, setOpen] = useState<Decision | null>(null);
  useEffect(() => {
    const tick = () => api<Decision[]>("/api/change-requests").then(setRows);
    tick();
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, []);
  return (
    <>
      <h1>Live Changes</h1>
      <p className="sub">Every BLOCK / HOLD / WARN row must show the exact reasons.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Request</th><th>Decision</th><th>Risk</th><th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.request_id} className="clickable" onClick={() => setOpen(row)}>
                <td>{row.timestamp}</td>
                <td>{row.request_id}</td>
                <td><span className={`pill ${row.decision}`}>{row.decision}</span></td>
                <td>{row.risk_score}</td>
                <td>{row.reasons?.[0] || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {open && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Why this decision</h3>
          <p><span className={`pill ${open.decision}`}>{open.decision}</span> risk {open.risk_score} hard={String(open.hard_violation)}</p>
          <ol className="reasons">
            {(open.reasons || []).map((r) => <li key={r}>{r}</li>)}
          </ol>
          <pre>{JSON.stringify(open.checks, null, 2)}</pre>
        </div>
      )}
    </>
  );
}

function Approvals() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api<any[]>("/api/change-approvals").then(setRows);
  }, []);
  return (
    <>
      <h1>Approvals</h1>
      <p className="sub">Consumed approvals cannot be silently reused.</p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Ticket</th><th>Object</th><th>PLC</th><th>Status</th><th>Window</th></tr></thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.approval_id}>
                <td>{row.change_ticket}</td>
                <td>{row.object}</td>
                <td>{row.plc_id}</td>
                <td>{row.status}</td>
                <td>{row.valid_from} → {row.valid_until}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function ProcessState() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api("/api/plcs/tank-plc-01/state").then(setData);
  }, []);
  const current = data?.state;
  const states = Object.keys(data?.model?.states || {});
  return (
    <>
      <h1>Process State</h1>
      <p className="sub">FSM is loaded from the commissioned model, not hard-coded in the UI.</p>
      <div className="fsm">
        {states.map((name) => (
          <div key={name} className={`state-node ${name === current ? "current" : ""}`}>{name}</div>
        ))}
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Permitted transitions</h3>
        <pre>{JSON.stringify(data?.model?.transitions, null, 2)}</pre>
      </div>
    </>
  );
}

function Policies() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api<any[]>("/api/policies").then(setRows);
  }, []);
  return (
    <>
      <h1>Policies</h1>
      <p className="sub">YAML is validated before activation. Version and content hash are retained on every decision.</p>
      <table>
        <thead><tr><th>Name</th><th>Version</th><th>Status</th><th>Hash</th></tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}><td>{row.name}</td><td>{row.version}</td><td>{row.status}</td><td>{row.hash}</td></tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function Incidents() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api<any[]>("/api/incidents").then(setRows);
  }, []);
  return (
    <>
      <h1>Incidents</h1>
      {rows.map((row) => (
        <div className="card" key={row.incident_id} style={{ marginBottom: 12 }}>
          <h3>{row.title}</h3>
          <p>{row.severity} · {row.request_id}</p>
          <ol className="reasons">
            {(row.payload?.reasons || []).map((r: string) => <li key={r}>{r}</li>)}
          </ol>
        </div>
      ))}
    </>
  );
}

function Recovery() {
  const [result, setResult] = useState<any>(null);
  async function evaluate() {
    const data = await api("/api/recovery/evaluate", {
      method: "POST",
      body: JSON.stringify({
        plc_id: "tank-plc-01",
        parameter: "TankLevel_SP",
        requested_value: 95,
        previous_value: 95,
        already_applied: true,
      }),
    });
    setResult(data);
  }
  return (
    <>
      <h1>Recovery</h1>
      <p className="sub">Advisory only. Previous value is not assumed safe.</p>
      <button className="primary" onClick={evaluate}>Evaluate recovery for unsafe level</button>
      {result && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>{result.action}</h3>
          <ol className="reasons">{(result.rationale || []).map((r: string) => <li key={r}>{r}</li>)}</ol>
          <pre>{JSON.stringify(result.target_values, null, 2)}</pre>
        </div>
      )}
    </>
  );
}

function Research() {
  const [rows, setRows] = useState<any[]>([]);
  const [caps, setCaps] = useState<any>(null);
  useEffect(() => {
    api<any[]>("/api/research/compare").then(setRows);
    api("/api/capabilities").then(setCaps);
  }, []);
  const methods = useMemo(() => ["static_range", "fsm", "fsm_temporal", "full_framework"], []);
  return (
    <>
      <h1>Research / Evaluation</h1>
      <p className="sub">Same change, independent algorithms. Ground-truth labels never appear here.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Request</th>
              {methods.map((m) => <th key={m}>{m}</th>)}
              <th>Reasons</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.request_id}>
                <td>{row.request_id}</td>
                {methods.map((m) => (
                  <td key={m}><span className={`pill ${row.algorithms?.[m] || row.full_framework}`}>{row.algorithms?.[m] || "—"}</span></td>
                ))}
                <td>{(row.reasons || []).join("; ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Capability honesty</h3>
        <pre>{JSON.stringify(caps, null, 2)}</pre>
      </div>
    </>
  );
}

function Admin() {
  return (
    <>
      <h1>Administration</h1>
      <p className="sub">Enforcement stays off unless LAB_MODE is true. Demo passwords are lab fixtures.</p>
      <div className="card">
        <p>Fail-safe modes: fail_open, fail_closed, fail_to_advisory (environment setting).</p>
        <p>Roles: admin, engineer, operator, analyst, auditor, researcher.</p>
      </div>
    </>
  );
}

function Guard({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Shell>{children}</Shell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Guard><Overview /></Guard>} />
      <Route path="/assets" element={<Guard><Assets /></Guard>} />
      <Route path="/assets/:id" element={<Guard><AssetDetail /></Guard>} />
      <Route path="/changes" element={<Guard><Changes /></Guard>} />
      <Route path="/approvals" element={<Guard><Approvals /></Guard>} />
      <Route path="/state" element={<Guard><ProcessState /></Guard>} />
      <Route path="/policies" element={<Guard><Policies /></Guard>} />
      <Route path="/incidents" element={<Guard><Incidents /></Guard>} />
      <Route path="/recovery" element={<Guard><Recovery /></Guard>} />
      <Route path="/research" element={<Guard><Research /></Guard>} />
      <Route path="/admin" element={<Guard><Admin /></Guard>} />
    </Routes>
  );
}
