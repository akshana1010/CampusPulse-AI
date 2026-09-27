# CampusPulse AI 🎓

**AI-Powered College Social Problem Mapper**

> A production-grade Flask web application that lets students report campus problems.
> Google Gemini AI automatically analyses each report for category, priority, sentiment, and generates a summary.
> Reports are visualised on an interactive Leaflet/OpenStreetMap campus map, with a Chart.js admin analytics dashboard.

---

## ✨ Features

| Feature | Description |
|---|---|
| Student Registration & Login | Secure auth with Werkzeug password hashing |
| Problem Submission | Form with Leaflet map pin picker and image upload |
| AI Analysis | Gemini 1.5 Flash auto-assigns priority, category, summary, sentiment |
| Campus Map | Interactive Leaflet map with colour-coded markers and heatmap |
| Student Dashboard | Track personal reports with status timeline |
| Admin Panel | Manage all reports, filter, update statuses, add notes |
| Analytics Charts | Chart.js bar, doughnut, and line charts |
| Community Voting | Upvote/downvote reports to signal importance |
| In-App Notifications | Students notified on every status change |

---

## 🛠 Tech Stack

- **Backend:** Python 3.11+ · Flask 3.x · SQLAlchemy · Flask-Login · Flask-Migrate
- **Database:** SQLite (development) / PostgreSQL (production)
- **AI:** Google Gemini 1.5 Flash (`google-generativeai`)
- **Frontend:** Vanilla HTML · CSS · JavaScript
- **Maps:** Leaflet.js + OpenStreetMap
- **Charts:** Chart.js 4.x
- **Security:** Flask-WTF (CSRF) · Flask-Limiter · Werkzeug

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-org/campuspulse-ai.git
cd campuspulse-ai
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:
- `SECRET_KEY` — any long, random string
- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/)
- `CAMPUS_LAT`, `CAMPUS_LNG` — your campus GPS coordinates
- `CAMPUS_NAME` — your university name

### 5. Initialize the database

```bash
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
```

### 6. (Optional) Seed demo data

```bash
python seed.py
```

### 7. Run the development server

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📁 Project Structure

```
CampusPulse-AI/
├── app/
│   ├── __init__.py          # App factory
│   ├── models.py            # SQLAlchemy models
│   ├── routes/
│   │   ├── auth.py          # /auth/*
│   │   ├── reports.py       # /reports/*
│   │   ├── admin.py         # /admin/*
│   │   └── analytics.py     # /analytics/*
│   ├── services/
│   │   ├── ai_service.py    # Gemini integration
│   │   ├── file_service.py  # Image upload
│   │   └── notification_service.py
│   └── utils/
│       ├── decorators.py    # @admin_required, @student_required
│       └── helpers.py       # format_datetime, time_since, etc.
├── templates/               # Jinja2 HTML templates
├── static/                  # CSS, JS, images
├── uploads/                 # User uploaded images (gitignored)
├── tests/                   # pytest test suite
├── config.py                # Dev / Test / Production configs
├── run.py                   # Entry point
└── requirements.txt
```

---

## 🔑 Default Roles

| Role | Access |
|---|---|
| `student` | Submit reports, view own reports, vote, see campus map |
| `admin` | All of the above + manage all reports, update statuses, view analytics |

> To create an admin user, register normally then update the role in the database:
> ```bash
> flask shell
> >>> from app.models import User
> >>> u = User.query.filter_by(email='admin@uni.edu').first()
> >>> u.role = 'admin'
> >>> from app import db; db.session.commit()
> ```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 🌐 Deployment (Render)

1. Push your code to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Set the **Build Command:** `pip install -r requirements.txt && flask db upgrade`
4. Set the **Start Command:** `gunicorn run:app --workers 2 --bind 0.0.0.0:$PORT`
5. Add all environment variables from `.env.example` in the Render dashboard.
6. Add a **Disk** mount at `/opt/render/project/src/uploads` for file persistence.

---

## 📄 Licence

MIT © 2025 CampusPulse AI
