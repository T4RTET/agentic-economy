import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const MANTLE_CHAIN_ID = 5000;

type Risk = "Low" | "Medium" | "High";
type Agent = {
  id: number;
  name: string;
  description: string;
  agent_type: string;
  owner_wallet: string;
  chain_id: number;
  status: string;
  created_at: string;
};
type Reputation = {
  trust_score: number;
  risk_level: Risk;
  recommended_wallet_limit_usd: number;
  successful_volume_usd: number;
  total_events: number;
  complaint_count: number;
  score_breakdown: Record<string, { score: number; max: number; description: string; penalty_applied?: number }>;
};
type Event = {
  id: number;
  title: string;
  category: string;
  outcome: "success" | "failed" | "error";
  value_usd: number;
  tx_hash: string | null;
  created_at: string;
};
type Complaint = {
  id: number;
  reason: string;
  severity: "low" | "medium" | "high";
  status: "open" | "confirmed" | "dismissed";
  created_at: string;
};
type Passport = {
  agent: Agent;
  reputation: Reputation;
  analysis: { summary: string; strengths: string[]; risk_flags: string[]; recommendation: string };
  actions_history: Event[];
  complaints: Complaint[];
};
type AgentSummary = { agent: Agent; reputation: Reputation };
type View = "catalog" | "passport";

declare global {
  interface Window {
    ethereum?: { request(args: { method: string; params?: unknown[] }): Promise<unknown> };
  }
}

export default function App() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [passport, setPassport] = useState<Passport | null>(null);
  const [view, setView] = useState<View>("catalog");
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<"All" | Risk>("All");
  const [modal, setModal] = useState<"agent" | "event" | "complaint" | null>(null);
  const [wallet, setWallet] = useState("");
  const [notice, setNotice] = useState("Loading reputation network...");
  const [busy, setBusy] = useState(false);

  const filteredAgents = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return agents.filter(({ agent, reputation }) => {
      const matchesText = !needle || `${agent.name} ${agent.description} ${agent.agent_type}`.toLowerCase().includes(needle);
      return matchesText && (riskFilter === "All" || reputation.risk_level === riskFilter);
    });
  }, [agents, query, riskFilter]);

  useEffect(() => {
    void loadAgents();
  }, []);

  async function execute(label: string, action: () => Promise<void>) {
    setBusy(true);
    setNotice(label);
    try {
      await action();
    } catch (error) {
      setNotice(readableError(error));
    } finally {
      setBusy(false);
    }
  }

  async function loadAgents() {
    await execute("Reading verified agent history...", async () => {
      const data = await api<AgentSummary[]>("/agents");
      setAgents(data);
      setNotice(`${data.length} agent passports available`);
    });
  }

  async function openPassport(id: number) {
    await execute("Building agent passport...", async () => {
      const data = await api<Passport>(`/agents/${id}/passport`);
      setPassport(data);
      setView("passport");
      window.scrollTo({ top: 0, behavior: "smooth" });
      setNotice(`Passport #${id} verified`);
    });
  }

  async function connectWallet() {
    await execute("Connecting wallet...", async () => {
      if (!window.ethereum) throw new Error("MetaMask is not installed. You can still explore demo passports.");
      const accounts = (await window.ethereum.request({ method: "eth_requestAccounts" })) as string[];
      const address = accounts[0];
      if (!address) throw new Error("No wallet selected.");
      setWallet(address);
      try {
        const existing = await api<Passport>(`/wallet/${address}/passport?chain_id=${MANTLE_CHAIN_ID}`);
        setPassport(existing);
        setView("passport");
        setNotice("Wallet-linked passport found");
      } catch {
        setNotice("Wallet connected. Create an agent passport to link it.");
        setModal("agent");
      }
    });
  }

  async function resetDemo() {
    await execute("Resetting demo data...", async () => {
      await api("/demo/reset", { method: "POST" });
      setPassport(null);
      setView("catalog");
      await loadAgents();
      setNotice("Demo restored: three distinct risk profiles");
    });
  }

  async function submitAgent(form: HTMLFormElement) {
    const data = new FormData(form);
    await execute("Issuing agent passport...", async () => {
      const agent = await api<Agent>("/agents", {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          description: data.get("description"),
          agent_type: data.get("agent_type"),
          owner_wallet: data.get("owner_wallet"),
          chain_id: MANTLE_CHAIN_ID,
        }),
      });
      setModal(null);
      await loadAgents();
      await openPassport(agent.id);
    });
  }

  async function submitEvent(form: HTMLFormElement) {
    if (!passport) return;
    const data = new FormData(form);
    await execute("Adding verifiable action...", async () => {
      await api(`/agents/${passport.agent.id}/events`, {
        method: "POST",
        body: JSON.stringify({
          title: data.get("title"),
          category: data.get("category"),
          outcome: data.get("outcome"),
          value_usd: Number(data.get("value_usd")),
          tx_hash: data.get("tx_hash") || null,
          metadata: { source: "passport-demo" },
        }),
      });
      setModal(null);
      await openPassport(passport.agent.id);
      await loadAgents();
    });
  }

  async function submitComplaint(form: HTMLFormElement) {
    if (!passport) return;
    const data = new FormData(form);
    await execute("Recording risk signal...", async () => {
      await api(`/agents/${passport.agent.id}/complaints`, {
        method: "POST",
        body: JSON.stringify({ reason: data.get("reason"), severity: data.get("severity"), status: "open" }),
      });
      setModal(null);
      await openPassport(passport.agent.id);
      await loadAgents();
    });
  }

  return (
    <div className="app">
      <header className="nav">
        <button className="brand" onClick={() => setView("catalog")} aria-label="Open agent directory">
          <span className="brand-mark">A</span>
          <span><strong>Agent Passport</strong><small>Trust layer on Mantle</small></span>
        </button>
        <nav>
          <button className={view === "catalog" ? "active" : ""} onClick={() => setView("catalog")}>Directory</button>
          {passport && <button className={view === "passport" ? "active" : ""} onClick={() => setView("passport")}>Passport</button>}
        </nav>
        <div className="nav-actions">
          <button className="icon-button" onClick={resetDemo} title="Reset demo" disabled={busy}>↻</button>
          <button className="wallet-button" onClick={connectWallet} disabled={busy}>
            <span className="status-dot" />{wallet ? shortAddress(wallet) : "Connect wallet"}
          </button>
        </div>
      </header>

      <div className="notice" aria-live="polite"><span className={busy ? "pulse" : ""} />{notice}</div>

      {view === "catalog" ? (
        <main>
          <section className="intro">
            <div>
              <p className="kicker">Reputation infrastructure for autonomous finance</p>
              <h1>Know what an agent can be trusted with.</h1>
              <p>Every passport turns wallet activity, execution quality, complaints, and onchain evidence into an explainable trust decision.</p>
            </div>
            <div className="network-stats">
              <Stat value={String(agents.length)} label="Registered agents" />
              <Stat value={formatUsd(agents.reduce((sum, item) => sum + item.reputation.successful_volume_usd, 0))} label="Verified volume" />
              <Stat value="Mantle" label="Settlement network" />
            </div>
          </section>

          <section className="directory">
            <div className="section-heading">
              <div><p className="kicker">Live registry</p><h2>Agent directory</h2></div>
              <button className="primary" onClick={() => setModal("agent")}>+ Issue passport</button>
            </div>
            <div className="filters">
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search agents, capabilities, types..." />
              <div className="segments">
                {(["All", "Low", "Medium", "High"] as const).map((risk) => (
                  <button key={risk} className={riskFilter === risk ? "selected" : ""} onClick={() => setRiskFilter(risk)}>{risk}</button>
                ))}
              </div>
            </div>
            <div className="agent-grid">
              {filteredAgents.map((item) => <AgentCard key={item.agent.id} item={item} onOpen={() => openPassport(item.agent.id)} />)}
            </div>
          </section>
        </main>
      ) : passport ? (
        <PassportView passport={passport} onBack={() => setView("catalog")} onEvent={() => setModal("event")} onComplaint={() => setModal("complaint")} />
      ) : null}

      {modal === "agent" && (
        <Modal title="Issue agent passport" subtitle="Register an AI agent and bind it to an owner wallet." onClose={() => setModal(null)}>
          <DataForm onSubmit={submitAgent} submitLabel="Issue passport">
            <Field label="Agent name" name="name" placeholder="Treasury Guard" minLength={2} />
            <Field label="Agent type" name="agent_type" placeholder="defi-risk-agent" minLength={2} />
            <Field label="Owner wallet" name="owner_wallet" defaultValue={wallet} placeholder="0x..." minLength={6} wide />
            <Field label="Description" name="description" placeholder="What the agent does and where it operates" wide textarea />
          </DataForm>
        </Modal>
      )}
      {modal === "event" && (
        <Modal title="Add verified action" subtitle="Every outcome updates the passport immediately." onClose={() => setModal(null)}>
          <DataForm onSubmit={submitEvent} submitLabel="Record action">
            <Field label="Action title" name="title" placeholder="Executed guarded swap" minLength={2} />
            <Field label="Category" name="category" placeholder="swap" minLength={2} />
            <Select label="Outcome" name="outcome" options={["success", "failed", "error"]} />
            <Field label="Value, USD" name="value_usd" type="number" defaultValue="100" min="0" />
            <Field label="Transaction hash" name="tx_hash" placeholder="0x... (optional)" wide />
          </DataForm>
        </Modal>
      )}
      {modal === "complaint" && (
        <Modal title="Submit complaint" subtitle="Complaints are visible risk signals and affect trust." onClose={() => setModal(null)}>
          <DataForm onSubmit={submitComplaint} submitLabel="Submit complaint">
            <Select label="Severity" name="severity" options={["low", "medium", "high"]} />
            <Field label="Reason" name="reason" placeholder="Describe the issue clearly" minLength={4} wide textarea />
          </DataForm>
        </Modal>
      )}
    </div>
  );
}

function AgentCard({ item, onOpen }: { item: AgentSummary; onOpen(): void }) {
  const { agent, reputation } = item;
  return (
    <article className="agent-card" onClick={onOpen}>
      <div className="card-top"><AgentIcon name={agent.name} /><RiskBadge risk={reputation.risk_level} /></div>
      <p className="agent-type">{agent.agent_type}</p>
      <h3>{agent.name}</h3>
      <p className="description">{agent.description}</p>
      <div className="trust-row">
        <ScoreRing score={reputation.trust_score} risk={reputation.risk_level} />
        <div><span>Recommended wallet limit</span><strong>{formatUsd(reputation.recommended_wallet_limit_usd)}</strong></div>
      </div>
      <div className="card-metrics">
        <span><strong>{reputation.total_events}</strong> actions</span>
        <span><strong>{formatUsd(reputation.successful_volume_usd)}</strong> handled</span>
        <span><strong>{reputation.complaint_count}</strong> complaints</span>
      </div>
      <button className="card-link">Open passport <span>→</span></button>
    </article>
  );
}

function PassportView({ passport, onBack, onEvent, onComplaint }: { passport: Passport; onBack(): void; onEvent(): void; onComplaint(): void }) {
  const { agent, reputation, analysis } = passport;
  return (
    <main className="passport-page">
      <button className="back" onClick={onBack}>← Agent directory</button>
      <section className="passport-hero">
        <div className="identity">
          <AgentIcon name={agent.name} large />
          <div><p className="agent-type">{agent.agent_type}</p><h1>{agent.name}</h1><p>{agent.description}</p></div>
        </div>
        <div className="passport-score">
          <ScoreRing score={reputation.trust_score} risk={reputation.risk_level} large />
          <div><RiskBadge risk={reputation.risk_level} /><span>Recommended wallet access</span><strong>{formatUsd(reputation.recommended_wallet_limit_usd)}</strong></div>
        </div>
      </section>

      <section className="passport-meta">
        <div><span>Owner wallet</span><strong>{shortAddress(agent.owner_wallet)}</strong></div>
        <div><span>Network</span><strong>Mantle · {agent.chain_id}</strong></div>
        <div><span>Passport ID</span><strong>ARP-{String(agent.id).padStart(6, "0")}</strong></div>
        <div><span>Status</span><strong className="verified">● {agent.status}</strong></div>
      </section>

      <section className="passport-layout">
        <div className="main-column">
          <article className="panel analysis">
            <div className="section-heading"><div><p className="kicker">Decision intelligence</p><h2>Trust assessment</h2></div></div>
            <p className="analysis-summary">{analysis.summary}</p>
            <div className="signal-columns">
              <div><h3>Strengths</h3>{analysis.strengths.map((item) => <p className="signal positive" key={item}>✓ {item}</p>)}</div>
              <div><h3>Risk flags</h3>{analysis.risk_flags.length ? analysis.risk_flags.map((item) => <p className="signal negative" key={item}>! {item}</p>) : <p className="signal neutral">No material flags</p>}</div>
            </div>
            <div className="recommendation"><span>Recommended action</span><strong>{analysis.recommendation}</strong></div>
          </article>

          <article className="panel">
            <div className="section-heading"><div><p className="kicker">Explainable score</p><h2>Trust factors</h2></div></div>
            <div className="score-factors">
              {Object.entries(reputation.score_breakdown).map(([key, factor]) => (
                <div className="factor" key={key}>
                  <div><strong>{titleCase(key)}</strong><span>{factor.description}</span></div>
                  <div className="factor-score"><strong>{factor.score}</strong><span>/ {factor.max}</span></div>
                  <div className="bar"><span style={{ width: `${Math.max(0, Math.min(100, (factor.score / factor.max) * 100))}%` }} /></div>
                </div>
              ))}
            </div>
          </article>

          <article className="panel">
            <div className="section-heading"><div><p className="kicker">Verifiable history</p><h2>Agent actions</h2></div><button className="primary small" onClick={onEvent}>+ Add action</button></div>
            <div className="timeline">
              {passport.actions_history.map((event) => (
                <div className="timeline-item" key={event.id}>
                  <span className={`event-dot ${event.outcome}`} />
                  <div><strong>{event.title}</strong><span>{event.category} · {dateLabel(event.created_at)}{event.tx_hash ? " · onchain verified" : ""}</span></div>
                  <div className="event-value"><strong>{formatUsd(event.value_usd)}</strong><span className={event.outcome}>{event.outcome}</span></div>
                </div>
              ))}
            </div>
          </article>
        </div>

        <aside>
          <article className="panel key-metrics">
            <p className="kicker">Evidence snapshot</p><h2>Passport metrics</h2>
            <Stat value={formatUsd(reputation.successful_volume_usd)} label="Successful volume" />
            <Stat value={String(reputation.total_events)} label="Recorded actions" />
            <Stat value={String(reputation.complaint_count)} label="Active complaints" />
            <Stat value={dateLabel(agent.created_at)} label="Created" />
          </article>
          <article className="panel">
            <div className="section-heading"><div><p className="kicker">Public signals</p><h2>Complaints</h2></div><button className="danger small" onClick={onComplaint}>+ Report</button></div>
            {passport.complaints.length ? passport.complaints.map((complaint) => (
              <div className="complaint" key={complaint.id}><RiskBadge risk={complaint.severity === "high" ? "High" : complaint.severity === "medium" ? "Medium" : "Low"} /><p>{complaint.reason}</p><span>{complaint.status} · {dateLabel(complaint.created_at)}</span></div>
            )) : <p className="empty">No complaints recorded.</p>}
          </article>
        </aside>
      </section>
    </main>
  );
}

function Modal({ title, subtitle, onClose, children }: { title: string; subtitle: string; onClose(): void; children: React.ReactNode }) {
  return <div className="modal-backdrop" onMouseDown={onClose}><section className="modal" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" onClick={onClose}>×</button><p className="kicker">Agent Reputation Passport</p><h2>{title}</h2><p>{subtitle}</p>{children}</section></div>;
}
function DataForm({ onSubmit, submitLabel, children }: { onSubmit(form: HTMLFormElement): Promise<void>; submitLabel: string; children: React.ReactNode }) {
  return <form className="data-form" onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); void onSubmit(event.currentTarget); }}>{children}<button className="primary submit" type="submit">{submitLabel}</button></form>;
}
function Field(props: React.InputHTMLAttributes<HTMLInputElement> & { label: string; wide?: boolean; textarea?: boolean }) {
  const { label, wide, textarea, ...inputProps } = props;
  return <label className={wide ? "wide" : ""}><span>{label}</span>{textarea ? <textarea name={inputProps.name} placeholder={inputProps.placeholder} required /> : <input {...inputProps} required={inputProps.name !== "tx_hash"} />}</label>;
}
function Select({ label, name, options }: { label: string; name: string; options: string[] }) {
  return <label><span>{label}</span><select name={name}>{options.map((option) => <option key={option}>{option}</option>)}</select></label>;
}
function AgentIcon({ name, large }: { name: string; large?: boolean }) {
  return <div className={`agent-icon ${large ? "large" : ""}`}>{name.split(/\s+/).slice(0, 2).map((word) => word[0]).join("")}</div>;
}
function RiskBadge({ risk }: { risk: Risk }) {
  return <span className={`risk-badge ${risk.toLowerCase()}`}><i />{risk} risk</span>;
}
function ScoreRing({ score, risk, large }: { score: number; risk: Risk; large?: boolean }) {
  return <div className={`score-ring ${risk.toLowerCase()} ${large ? "large" : ""}`} style={{ "--score": `${score * 3.6}deg` } as React.CSSProperties}><strong>{score}</strong><span>trust score</span></div>;
}
function Stat({ value, label }: { value: string; label: string }) {
  return <div className="stat"><strong>{value}</strong><span>{label}</span></div>;
}

async function api<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Backend request failed");
  return data as T;
}
function shortAddress(address: string) { return address.length > 13 ? `${address.slice(0, 7)}…${address.slice(-5)}` : address; }
function formatUsd(value: number) { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value); }
function dateLabel(value: string) { return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value.replace(" ", "T") + (value.includes("T") ? "" : "Z"))); }
function titleCase(value: string) { return value.split("_").map((word) => word[0].toUpperCase() + word.slice(1)).join(" "); }
function readableError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return message.toLowerCase().includes("failed to fetch") ? "Backend is offline. Start FastAPI on port 8000." : message;
}
