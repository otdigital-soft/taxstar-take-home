# TaxStar

Internal tool for managing company entities and their invoices — Flask + MongoDB API and Next.js frontend.

## Stack

**Backend:** Flask (Python), PyMongo, Pydantic, JWT auth, Fernet encryption for TRN  
**Frontend:** Next.js App Router, React Hook Form + Zod, TanStack Query, Tailwind CSS, Sonner toasts

## Prerequisites

- Python 3.11+ (developed/tested on 3.14 as well)
- Node.js 18+
- MongoDB running locally (default `mongodb://localhost:27017`), or:

```bash
docker compose up -d mongo
```

## Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # already present; adjust if needed
python run.py
```

API listens on `http://localhost:5000`.

### Tests

```bash
cd backend
.\.venv\Scripts\activate   # or source .venv/bin/activate
pytest -q
```

Tests use **mongomock** and do not require a real MongoDB instance.

## Frontend setup

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

App runs at `http://localhost:3000`.

Set `NEXT_PUBLIC_API_URL` if the API is not on `http://localhost:5000`.

## API overview

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/auth/signup` | No | `{ email, password, name }` |
| POST | `/api/auth/login` | No | `{ email, password }` |
| POST | `/api/entities` | JWT | `{ name, trn }` — TRN encrypted; response returns `trn_masked` |
| GET | `/api/entities` | JWT | List current user's entities |
| GET | `/api/entities/:id` | JWT | Single entity |
| POST | `/api/invoices` | JWT | `{ entity_id, invoice_number, amount: "1250.50", ... }` |
| GET | `/api/invoices?entity_id=&status=` | JWT | Filter uses `effective_status` |
| PATCH | `/api/invoices/:id` | JWT | `{ status }` with transition rules |

### Error shape

All errors use one envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid fields.",
    "fields": {
      "due_date": "Value error, due_date must fall after issue_date"
    }
  }
}
```

## Decisions & tradeoffs

- **Blueprint-per-domain** under `/api` keeps auth, entities, and invoices isolated and easy to extend.
- **PyMongo (no ORM)** matches the brief and keeps schemas explicit via Pydantic request *and* response models at the API boundary.
- **Money as minor units:** amounts are accepted as decimal strings (e.g. `"1250.50"`), validated with `Decimal`, and stored as `amount_minor` integers (e.g. `125050`). Responses return `amount` as a string. Avoids float rounding issues common in financial software. Assumption: 2 decimal places for all currencies in this exercise.
- **Status transitions** are intentionally constrained (`draft→sent/paid`, `sent→paid/overdue`, `overdue→paid`, `paid→∅`). The brief only requires status updates; the map is an assumption documented here and enforced with `forbidden_status_transition`.
- **Effective overdue:** stored `status` is never silently rewritten. Responses include `effective_status`, which becomes `overdue` when `due_date < today` and the invoice is not paid. List filters apply to `effective_status`.
- **TRN encrypted + masked:** Mongo stores only `trn_encrypted` (Fernet). API responses expose `trn_masked` (e.g. `******2345`), never the full TRN. Covered by tests asserting no plaintext `trn` field in Mongo.
- **Authorization ≠ authentication:** entity queries include `owner_id`. Invoice access is authorized **through the parent entity**. Cross-user access returns **404** (not 403) so we don’t leak existence.
- **Indexes** are created on app startup: unique `users.email`, `entities(owner_id, created_at)`, `invoices(entity_id, status, created_at)`, and unique `(entity_id, invoice_number)`.
- **Invoice numbers unique per entity** — reasonable assumption; duplicates return `409 duplicate_invoice_number`.
- **GET `/api/entities`** was added so the UI can list entities — a small extension of the listed endpoints.
- **JWT in `localStorage`** keeps the frontend simple for a take-home; production would prefer httpOnly cookies + CSRF protection.

## Out-of-scope integration: Celery / Redis background jobs

If we needed async work (e.g. generating invoice PDFs or sending “overdue” reminders), I would add a Redis broker, a Celery worker process, and enqueue tasks from the Flask routes after a successful write — e.g. `send_invoice_reminder.delay(invoice_id)` after creating an invoice with status `sent`. Workers would share the same Mongo connection settings and Fernet key via env, and I’d expose a small admin/health endpoint for queue depth. For local dev, Docker Compose would run `mongo`, `redis`, `api`, `worker`, and `frontend` together.

## What I’d add with more time

- Refresh tokens / token revocation and httpOnly cookie sessions
- Pagination on invoice lists; currency exponent table beyond 2 dp
- Soft-delete, audit log for status changes
- E2E tests (Playwright) against a dockerized stack
- Role-based access if multiple users share an entity

## Assumptions

- One user owns the entities they create; no multi-user sharing in this version.
- Marking paid is a status PATCH to `paid` (no payment gateway).
- Signup is included on `/login` so the app is usable without seeding users.
- Status transition rules and per-entity unique invoice numbers are product assumptions beyond the brief.
- Currencies use two decimal places (minor units × 100).
