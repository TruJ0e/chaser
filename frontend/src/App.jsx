import { useCallback, useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const currency = (value, code = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: code }).format(value);

function Metric({ label, value, detail, accent }) {
  return (
    <article className={`metric ${accent || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function App() {
  const [invoices, setInvoices] = useState([]);
  const [activity, setActivity] = useState([]);
  const [health, setHealth] = useState(null);
  const [draft, setDraft] = useState(null);
  const [loading, setLoading] = useState(true);
  const [drafting, setDrafting] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [invoiceResponse, activityResponse, healthResponse] = await Promise.all([
        fetch(`${API_URL}/api/invoices`),
        fetch(`${API_URL}/api/activity`),
        fetch(`${API_URL}/api/health`),
      ]);
      if (!invoiceResponse.ok || !activityResponse.ok || !healthResponse.ok) {
        throw new Error("The API returned an error.");
      }
      setInvoices(await invoiceResponse.json());
      setActivity(await activityResponse.json());
      setHealth(await healthResponse.json());
      setError("");
    } catch (requestError) {
      setError(`${requestError.message} Is the backend running on ${API_URL}?`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const createDraft = useCallback(async (invoice) => {
    setDrafting(invoice.id);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/invoices/${invoice.id}/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!response.ok) throw new Error("Draft generation failed.");
      setDraft({ ...(await response.json()), invoice });
      const activityResponse = await fetch(`${API_URL}/api/activity`);
      setActivity(await activityResponse.json());
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDrafting("");
    }
  }, []);

  const columns = useMemo(() => [
    { field: "customer_name", headerName: "Customer", minWidth: 180, flex: 1.2 },
    { field: "number", headerName: "Invoice", minWidth: 120 },
    {
      field: "amount",
      headerName: "Outstanding",
      minWidth: 145,
      valueFormatter: ({ value, data }) => currency(value, data.currency),
    },
    { field: "due_date", headerName: "Due date", minWidth: 125 },
    {
      field: "days_overdue",
      headerName: "Age",
      minWidth: 110,
      cellRenderer: ({ value }) => <span className={`age age-${value >= 45 ? "late" : value >= 15 ? "mid" : "new"}`}>{value} days</span>,
    },
    {
      headerName: "Next action",
      sortable: false,
      filter: false,
      minWidth: 150,
      cellRenderer: ({ data }) => (
        <button className="draft-button" disabled={drafting === data.id} onClick={() => createDraft(data)}>
          {drafting === data.id ? "Drafting…" : "Create draft"}
        </button>
      ),
    },
  ], [createDraft, drafting]);

  const totals = useMemo(() => {
    const outstanding = invoices.reduce((sum, item) => sum + item.amount, 0);
    return {
      outstanding,
      critical: invoices.filter((item) => item.days_overdue >= 45).length,
      averageAge: invoices.length ? Math.round(invoices.reduce((sum, item) => sum + item.days_overdue, 0) / invoices.length) : 0,
    };
  }, [invoices]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">C</span><span>Chaser</span></div>
        <nav>
          <a className="active" href="#overview">Overview</a>
          <a href="#invoices">Invoices <span>{invoices.length}</span></a>
          <a href="#activity">Agent activity</a>
        </nav>
        <div className="agent-card">
          <span className="pulse" />
          <div><strong>Agent online</strong><small>Draft-only safety mode</small></div>
        </div>
      </aside>

      <main>
        <header>
          <div><p className="eyebrow">COLLECTIONS OVERVIEW</p><h1>Good evening, Truman.</h1><p>Here’s what needs attention across your receivables.</p></div>
          <div className="mode-pill"><span /> PayPal {health?.paypal_mode || "…"} · AI {health?.ai_mode || "…"}</div>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <section id="overview" className="metrics">
          <Metric label="TOTAL OUTSTANDING" value={currency(totals.outstanding)} detail={`Across ${invoices.length} open invoices`} accent="ink" />
          <Metric label="AVG. DAYS OVERDUE" value={`${totals.averageAge} days`} detail="Portfolio average" />
          <Metric label="CRITICAL ACCOUNTS" value={totals.critical} detail="45+ days overdue" accent="coral" />
          <Metric label="RECOVERED THIS MONTH" value="$0" detail="Connect payment events next" accent="mint" />
        </section>

        <section id="invoices" className="panel invoice-panel">
          <div className="panel-heading"><div><p className="eyebrow">PRIORITY QUEUE</p><h2>Open invoices</h2></div><span>{loading ? "Loading…" : `${invoices.length} accounts`}</span></div>
          <div className="invoice-grid">
            <AgGridReact
              rowData={invoices}
              columnDefs={columns}
              defaultColDef={{ sortable: true, filter: true, resizable: true }}
              getRowId={({ data }) => data.id}
              rowHeight={58}
              headerHeight={48}
              animateRows
            />
          </div>
        </section>

        <section id="activity" className="lower-grid">
          <article className="panel activity-panel">
            <div className="panel-heading"><div><p className="eyebrow">AUDIT TRAIL</p><h2>Agent activity</h2></div></div>
            {activity.length === 0 ? <p className="empty">Create a draft to see the agent’s decision trail.</p> : activity.slice(0, 5).map((event) => (
              <div className="activity-row" key={`${event.timestamp}-${event.invoice_id}`}>
                <span className={`stage-dot ${event.stage}`} />
                <div><strong>{event.stage} draft · {event.invoice_number}</strong><p>{event.tone_rationale}</p><small>{new Date(event.timestamp).toLocaleString()}</small></div>
              </div>
            ))}
          </article>
          <article className="panel aging-panel">
            <p className="eyebrow">AGING SNAPSHOT</p><h2>Risk distribution</h2>
            {[{ label: "1–14 days", test: (d) => d < 15, cls: "fresh" }, { label: "15–44 days", test: (d) => d >= 15 && d < 45, cls: "watch" }, { label: "45+ days", test: (d) => d >= 45, cls: "risk" }].map((bucket) => {
              const amount = invoices.filter((item) => bucket.test(item.days_overdue)).reduce((sum, item) => sum + item.amount, 0);
              const width = totals.outstanding ? Math.max(5, amount / totals.outstanding * 100) : 0;
              return <div className="bucket" key={bucket.label}><div><span>{bucket.label}</span><strong>{currency(amount)}</strong></div><div className="bar"><i className={bucket.cls} style={{ width: `${width}%` }} /></div></div>;
            })}
          </article>
        </section>
      </main>

      {draft && <div className="modal-backdrop" onMouseDown={() => setDraft(null)}>
        <article className="draft-modal" onMouseDown={(event) => event.stopPropagation()}>
          <button className="close" onClick={() => setDraft(null)} aria-label="Close">×</button>
          <p className="eyebrow">{draft.stage.toUpperCase()} · AI DRAFT</p>
          <h2>{draft.subject}</h2>
          <pre>{draft.body}</pre>
          <div className="rationale"><strong>Why this tone, why now</strong><p>{draft.rationale}</p></div>
          <footer><span>Generated by {draft.generated_by} · not sent</span><button onClick={() => navigator.clipboard?.writeText(draft.body)}>Copy draft</button></footer>
        </article>
      </div>}
    </div>
  );
}

export default App;
