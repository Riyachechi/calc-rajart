# Raj Art Service — Sheet Printing Dashboard

A full-stack rebuild of `calculator.py`: same rate logic, but now a
website with a **saved order history** (a real database), instead of a
Streamlit app that forgets everything on refresh.

- **Backend:** FastAPI (Python) — reads `Sorted_Sheet_Rates_For_Dashboard.xlsx`
  and reproduces the exact pricing rules from `calculator.py`
  (GSM + quantity + printing side lookup, nearest-quantity fallback,
  lamination add-on).
- **Database:** SQLite (`raj_art.db`), created automatically. Every order
  you save is a row, so it's there next time you open the site.
- **Frontend:** plain HTML/CSS/JS — no build step, served directly by
  the backend, so it's one service to deploy.

```
raj-art-dashboard/
├── app/
│   ├── main.py          FastAPI app + all API routes
│   ├── rates.py          Pricing logic (ported from calculator.py)
│   ├── models.py         Order database table
│   ├── schemas.py        Request/response shapes
│   ├── database.py       DB connection (SQLite by default)
│   └── data/
│       └── Sorted_Sheet_Rates_For_Dashboard.xlsx
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── requirements.txt
├── Procfile              For Render / Railway / Heroku-style platforms
├── render.yaml            One-click Render blueprint (includes a persistent disk)
└── .gitignore
```

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Open **http://localhost:8000** — that's the whole site (calculator +
saved orders), served from the one backend.

To update prices later, just replace the file at
`app/data/Sorted_Sheet_Rates_For_Dashboard.xlsx` with a new workbook that
keeps the same two sheet names and column headers (`Sheet_Rates_Sorted`,
`Lamination_Rates`), then restart the server.

## Putting it on GitHub

```bash
cd raj-art-dashboard
git init
git add .
git commit -m "Raj Art Service dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## Deploying it to a live link

**Render.com (recommended — free tier, and `render.yaml` is already set up):**

1. Push this folder to a GitHub repo (above).
2. Go to [render.com](https://render.com) → **New** → **Blueprint** → connect
   your repo. Render reads `render.yaml` automatically and provisions a
   web service with a small persistent disk mounted at `/var/data`, so
   your saved orders **survive redeploys** (SQLite on a normal free-tier
   disk gets wiped every time you push otherwise).
3. Click **Apply** — after the build finishes you get a live URL like
   `https://raj-art-dashboard.onrender.com`.

**Railway.app (also easy):**

1. Push to GitHub, then **New Project → Deploy from GitHub repo** on
   [railway.app](https://railway.app).
2. Railway detects `requirements.txt` and the `Procfile` automatically.
3. Add a **Volume** mounted at, say, `/data`, and set an environment
   variable `DATABASE_URL=sqlite:////data/raj_art.db` so orders persist
   the same way as on Render.

Either way, no other configuration is required — the frontend is served
by the same backend, so there's only one service and one URL.

## API reference (for reference / future integrations)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/rates/options` | GSM list, printing sides, lamination options for the form |
| POST | `/api/calculate` | Price a job (no save) |
| POST | `/api/orders` | Price a job **and** save it as a customer order |
| GET | `/api/orders?search=` | List saved orders, optional name/phone search |
| GET | `/api/orders/{id}` | Fetch one saved order |
| DELETE | `/api/orders/{id}` | Delete a saved order |
| GET | `/api/orders/export/csv` | Download all saved orders as CSV |

Interactive API docs are also available automatically at `/docs` once
the server is running.
