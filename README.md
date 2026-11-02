# Chaser

Chaser is an explainable AI collections agent for small businesses. It finds unpaid invoices, selects a respectful escalation stage, drafts a personalized follow-up with a one-click payment link, and records why it chose that tone at that moment.

This hackathon prototype is intentionally **draft-only**: it never sends email or calls PayPal's reminder endpoint from the web API. It runs end-to-end with realistic mock data and mock AI when no credentials are present.

## What is included

- FastAPI backend with mock-first PayPal and OpenAI-compatible AI clients.
- React dashboard with a real [AG Grid Community](https://www.ag-grid.com/react-data-grid/) invoice table.
- Three-stage escalation ladder: friendly nudge, firm reminder, final notice.
- Amount-aware risk rules that can accelerate high-value invoices.
- Append-only JSONL audit log for every generated draft and its rationale.
- PayPal Invoicing API v2 client for list, details, and reminder operations.

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

Open `http://localhost:5173`. Select **Create draft** on any invoice to exercise the escalation ladder and add an audit event.

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

To get sandbox credentials, sign in to the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/), choose **Apps & Credentials → Sandbox**, create or open a REST app, and copy its Client ID and Secret into `.env`. Do not put credentials in `frontend/`, source code, or commits.

## PayPal API contract

`backend/app/paypal_client.py` uses PayPal's documented REST hosts and paths:

| Operation | Method and path |
|---|---|
| OAuth client-credentials token | `POST /v1/oauth2/token` |
| List invoices | `GET /v2/invoicing/invoices` |
| Get invoice details | `GET /v2/invoicing/invoices/{invoice_id}` |
| Send PayPal reminder | `POST /v2/invoicing/invoices/{invoice_id}/remind` |

Sandbox base URL: `https://api-m.sandbox.paypal.com`. Live base URL: `https://api-m.paypal.com`.

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
- `POST /api/invoices/{invoice_id}/draft` — generate and audit a draft.
- `GET /api/activity` — newest audit events first.

## Verification

```bash
python -m pytest backend/tests
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
