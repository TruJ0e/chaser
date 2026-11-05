# Chaser

Chaser is an explainable AI collections agent for small businesses. It finds unpaid invoices, selects a respectful escalation stage, drafts a personalized follow-up with a one-click payment link, and records why it chose that tone at that moment.

This hackathon prototype is intentionally **mock-first and draft-only**: the demo makes no live PayPal sandbox calls, never sends email, and never calls PayPal's reminder endpoint from the web API. No PayPal Developer account is required. It runs end-to-end with realistic mock invoices, recovered payments, payment links, and deterministic draft generation when credentials are absent.

## What is included

- FastAPI backend with mock-first PayPal and OpenAI-compatible AI clients.
- React dashboard with a real [AG Grid Community](https://www.ag-grid.com/react-data-grid/) invoice table.
- Three-stage escalation ladder: friendly nudge, firm reminder, final notice.
- Amount-aware risk rules that can accelerate high-value invoices.
- Append-only JSONL audit log for every generated draft and its rationale.
- A swappable `PayPalClient` interface with network-free mock and REST adapters.
- Mock recovered-revenue metrics and aging buckets served to the dashboard.

## Quick start (mock mode — no credentials needed)

Prerequisites: Python 3.11+ and Node.js 20.19+.

### 1. Start the API

Windows PowerShell:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements-dev.txt
uvicorn app.main:app --app-dir backend --reload
```

macOS/Linux:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
uvicorn app.main:app --app-dir backend --reload
```

The API is at `http://localhost:8000`; interactive docs are at `http://localhost:8000/docs`.

### 2. Start the dashboard

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Select **Create draft** on invoices in each age band to exercise nudge, reminder, and final-notice copy. Each draft records its rationale in the activity feed. **Pay now** opens a local mock PayPal payer view in one click; it does not contact PayPal or collect payment details.

The expected default health response includes `"paypal_mode": "mock"`. Do not add PayPal credentials when running the hackathon demo.

## Configuration

All configuration belongs in the repository-root `.env` file (ignored by git). Start with `.env.example`.

| Variable | Purpose | Mock behavior |
|---|---|---|
| `PAYPAL_CLIENT_ID` | REST app client ID | Missing ID or secret enables mock invoices |
| `PAYPAL_CLIENT_SECRET` | REST app secret | Never expose this to the frontend |
| `PAYPAL_SANDBOX` | `true` uses sandbox; `false` uses live | Defaults to `true` |
| `NEBIUS_BASE_URL` | OpenAI-compatible API root, ending in `/v1` | Missing URL or key enables deterministic mock drafts |
| `NEBIUS_API_KEY` | Nebius API key | Never commit it |
| `NEBIUS_MODEL` | Chat-completions model ID | Defaults to a configurable Llama model ID |
| `CHASER_ACTIVITY_LOG` | JSONL audit log path | `backend/data/activity.jsonl` |
| `VITE_API_URL` | Backend URL used at frontend build/dev time | `http://localhost:8000` |

## PayPal integration seam

The application depends only on the `PayPalClient` protocol in `backend/app/paypal_client.py`. `create_paypal_client()` chooses one adapter at startup:

- With blank `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`, it returns `MockPayPalClient`. This is the supported hackathon-demo path and performs no network calls.
- When both values are present, it returns `PayPalRESTClient`. The API routes and React dashboard do not need to change.

To switch later to a live PayPal **sandbox**, sign in to the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/), choose **Apps & Credentials → Sandbox**, create or open a REST app, place its Client ID and Secret in the repository-root `.env`, keep `PAYPAL_SANDBOX=true`, and restart the API. Confirm `/api/health` reports `"paypal_mode": "sandbox"`. Do not put credentials in `frontend/`, source code, or commits.

The REST adapter is implemented and contract-tested with an in-process HTTP mock; it has not been exercised against a real PayPal sandbox account under the current mock-first decision.

## PayPal API contract

`backend/app/paypal_client.py` uses PayPal's documented REST hosts and paths:

| Operation | Method and path |
|---|---|
| OAuth client-credentials token | `POST /v1/oauth2/token` |
| List invoices | `GET /v2/invoicing/invoices` |
| Search open invoices (used by `/api/invoices`) | `POST /v2/invoicing/search-invoices` with body `{"status": ["SENT","UNPAID","PARTIALLY_PAID"], "due_date_range": {"start": ..., "end": <today>}}` |
| Get invoice details | `GET /v2/invoicing/invoices/{invoice_id}` |
| Send PayPal reminder | `POST /v2/invoicing/invoices/{invoice_id}/remind` with body `{subject, note, send_to_recipient, send_to_invoicer, additional_recipients}`; returns 204 |

Sandbox base URL: `https://api-m.sandbox.paypal.com`. Live base URL: `https://api-m.paypal.com`.

Each open invoice is then fetched in full. The normalizer chases `due_amount` (the outstanding balance after partial payments, falling back to `amount`) and uses `detail.metadata.recipient_view_url` as the one-click payment link.

The list call uses v2 parameters `page`, `page_size`, `total_required`, and `fields`. References: [Invoices v2 overview](https://developer.paypal.com/api/invoicing/v2/), [list invoices](https://developer.paypal.com/api/invoicing/v2/invoices-list/), [get invoice](https://developer.paypal.com/api/invoicing/v2/invoices-get/), [send reminder](https://developer.paypal.com/api/invoicing/v2/invoices-remind/), and [REST authentication](https://developer.paypal.com/api/rest/authentication/).

The reminder method is implemented for the next milestone but is not connected to a route or UI. Before enabling sends, add explicit user approval, idempotency/rate controls, and tests against a sandbox business account. PayPal currently limits reminders to two per invoice per day and controls the email's subject/note.

## Escalation policy

The transparent policy is in `backend/app/escalation.py`:

- **Nudge:** 0–14 days overdue.
- **Reminder:** 15–44 days overdue, or 7+ days when the balance is at least USD 5,000.
- **Final:** 45+ days overdue, or 30+ days when the balance is at least USD 10,000.

The rationale includes the invoice age, amount, and available relationship note. Every successful draft appends one JSON object to the activity log. Existing lines are never rewritten by the application.

## API

- `GET /api/health` — active integration modes and sending safety state.
- `GET /api/invoices` — normalized overdue invoices.
- `GET /api/dashboard` — outstanding, aging-bucket, critical-account, and recovered-revenue metrics.
- `POST /api/invoices/{invoice_id}/draft` — generate and audit a draft.
- `GET /api/activity` — newest audit events first.
- `GET /mock/pay/{invoice_id}` — local mock payer view; available only in mock mode.

## Verification

```bash
python -m pytest backend/tests
# If Windows denies access to the pytest temp dir, add: --basetemp .pytest-tmp
cd frontend
npm run build
```

## Roadmap / TODO

- Add an approval-gated email provider and connect sending only after review.
- Reconcile PayPal payment webhooks to recovered-revenue metrics.
- Store relationship history and audit events in a production database.
- Add pagination/concurrency limits for accounts with large invoice volumes.
- Validate the live detail normalizer against real sandbox invoices once credentials are supplied.

## License

[MIT](LICENSE)
