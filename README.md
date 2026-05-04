# Hospital Management System

A full-stack, role-based hospital management web application built with **Python Flask**, **SQLAlchemy**, and **Bootstrap 5**. Designed to manage patients, doctors, lab requests, and pharmacy inventory with a clean animated UI and a complete CI/CD pipeline.

![CI/CD](https://github.com/fahadjavedktk/hospital_management_system/actions/workflows/ci-cd.yml/badge.svg)

---

## Features

### 5 user roles with full access control

| Role | Capabilities |
|------|-------------|
| **Admin** | Add/remove doctors, patients, staff accounts |
| **Doctor** | View only their own assigned patients, write prescriptions, order lab tests, view lab reports and images instantly |
| **Lab** | View all lab requests, enter results with text and drag-and-drop image upload |
| **Pharmacy** | Add, edit, delete medicines — stock auto-deducts on prescription |
| **Patient** | View their own lab results (with images) and prescriptions only |

### Security highlights
- Passwords hashed with Werkzeug — never stored in plain text
- Role-based access control enforced on every backend endpoint
- Doctor isolation — each doctor only sees and prescribes to their own patients
- Session expiry after 8 hours
- Full audit log — every action recorded with user, action, and IP
- Input validation on all POST routes
- All secrets via environment variables — nothing hardcoded

### Lab image reports
- Lab staff upload X-ray, blood test, or any image via drag and drop
- Stored as base64 — no separate file storage needed
- Doctor sees image instantly in their Lab Reports tab
- Patient sees image inline in their health dashboard

### UI highlights
- Animated hero landing page with floating gradient circles
- Fixed topbar with colour-coded role chips
- Role-aware sidebar navigation
- Smooth fade-in and slide-in animations throughout
- Stat cards on lab and pharmacy dashboards
- Loading spinners, empty states, and inline banners — no browser alerts
- Double-submit prevention on all forms

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10, Flask 3.0.3 |
| ORM | Flask-SQLAlchemy 3.1.1 |
| Auth | Flask-Login 0.6.3 + Werkzeug |
| Database (dev) | SQLite — auto-created, zero setup |
| Database (prod) | PostgreSQL 15 |
| Frontend | Bootstrap 5.3, Bootstrap Icons, Vanilla JS |
| Server | Gunicorn 22.0.0 |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Testing | Pytest 8.2.2 + pytest-flask |

---

## Project Structure

```
hospital_management_system/
├── app.py                    # Flask app — 935 lines, 28 routes, 7 models
├── test_app.py               # 29 tests, 62%+ coverage
├── migrate_db.py             # One-time database migration script
├── requirements.txt          # Pinned dependencies
├── Dockerfile                # Production image (Gunicorn, non-root user)
├── docker-compose.yml        # App + PostgreSQL
├── .env.example              # Environment variable template
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci-cd.yml         # GitHub Actions pipeline
└── templates/
    ├── base.html             # Shared layout — topbar + sidebar
    ├── home.html             # Animated landing page
    ├── login.html            # Login with shake animation
    ├── admin.html            # 3-tab admin dashboard
    ├── doctor.html           # Patients + lab reports tabs
    ├── patient_form.html     # Prescription form with history
    ├── lab.html              # Lab requests with image upload
    ├── pharmacy.html         # Inventory with edit modal
    └── patient.html          # Patient health record with images
```

---

## Database Models

| Table | Purpose |
|-------|---------|
| `user_account` | All users — hashed passwords, roles, active status |
| `doctor` | Doctor profiles — name, specialisation, phone, linked login |
| `patient` | Patient records — linked to doctor and optional user account |
| `prescription` | Prescriptions — medicine name and quantity |
| `lab_request` | Lab orders — result text and base64 image |
| `medicine` | Pharmacy inventory — name, stock, price |
| `audit_log` | Action log — user, action, IP, timestamp |

---

## Quick Start

### Run locally (SQLite — zero setup)

```bash
# Clone
git clone https://github.com/fahadjavedktk/hospital_management_system.git
cd hospital_management_system

# Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install
pip install -r requirements.txt

# Environment file
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux

# Generate and set a secret key in .env
python -c "import secrets; print(secrets.token_hex(32))"

# Run
python app.py
```

Open **http://localhost:5000**

---

### Run with Docker + PostgreSQL

```bash
# Fill in .env (set SECRET_KEY, DATABASE_URL, DB_PASSWORD)
copy .env.example .env

# Build and start
docker compose up --build
```

Open **http://localhost:5000**

```bash
docker compose down                          # Stop
docker compose down --volumes --remove-orphans   # Full reset
```

---

## Default Credentials

> Change all passwords immediately in production.

| Username | Password | Role |
|----------|----------|------|
| `admin` | `Admin@2024!` | Admin |
| `doctor` | `Doctor@2024!` | Doctor |
| `lab` | `Lab@2024!` | Lab |
| `pharma` | `Pharma@2024!` | Pharmacy |
| `patient` | `Patient@2024!` | Patient |

Created automatically on first startup.

---

## Adding a Doctor (correct workflow)

1. Log in as **admin**
2. Go to **Admin panel → Doctors tab**
3. Enter the doctor's name and specialisation
4. Fill in **Username** and **Password** to create a login account — this links the profile to the account so the doctor only sees their own patients
5. Click **Add doctor**
6. Go to **Patients tab** — the doctor now appears in the dropdown

---

## Running Tests

```bash
pytest

# With coverage
pytest --cov=app --cov-report=term-missing
```

Test coverage includes login, auth protection, doctor/patient/staff management, role isolation, pharmacy CRUD, prescriptions with stock deduction, and lab result updates.

---

## CI/CD Pipeline

Every push to `main` automatically runs:

| Step | Tool | What it checks |
|------|------|---------------|
| Lint | flake8 | Code style in test file |
| Security scan | bandit | Security issues in app.py |
| Tests | pytest | 29 tests with 50% min coverage |
| Docker build | docker build | Container builds successfully |
| Smoke test | curl | App responds on port 5000 |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask session key — generate with `secrets.token_hex(32)` |
| `DATABASE_URL` | Yes | `sqlite:///hospital.db` for dev, PostgreSQL URL for prod |
| `DB_PASSWORD` | Docker only | PostgreSQL password for docker-compose |
| `FLASK_DEBUG` | No | `true` for local dev only — never in production |

---

## Production Checklist

- [ ] Change all default passwords
- [ ] Set a strong random `SECRET_KEY`
- [ ] Switch to PostgreSQL
- [ ] Set `FLASK_DEBUG=false`
- [ ] Add Nginx reverse proxy with HTTPS (Let's Encrypt — free)
- [ ] Set up daily automated database backups
- [ ] Restrict server firewall to ports 80, 443, 22
- [ ] Remove `/debug/doctor_link` route from app.py

---

## License

MIT — free to use and modify.

---

---

## Full Technology Stack

### Backend
- **Python 3.10** — core programming language
- **Flask 3.0.3** — web framework, routing, templating
- **Flask-SQLAlchemy 3.1.1** — ORM for database models and queries
- **Flask-Login 0.6.3** — session management, login/logout, auth protection
- **Werkzeug 3.0.3** — password hashing (bcrypt), WSGI utilities
- **python-dotenv 1.0.1** — loads environment variables from `.env` file
- **Gunicorn 22.0.0** — production WSGI server (replaces Flask dev server)
- **psycopg2-binary 2.9.9** — PostgreSQL database driver

### Database
- **SQLite** — development database, zero setup, auto-created on first run
- **PostgreSQL 15** — production database, handles concurrent users

### Frontend
- **Bootstrap 5.3** — responsive grid, components, utility classes
- **Bootstrap Icons 1.11** — icon library used throughout the UI
- **Vanilla JavaScript (ES6+)** — all interactivity, fetch API calls, DOM manipulation
- **CSS3** — custom animations (fadeIn, slideUp, popIn, shake, float, pulse, spin)

### DevOps & Infrastructure
- **Docker** — containerises the app into a portable image
- **Docker Compose** — orchestrates app + PostgreSQL containers together
- **GitHub Actions** — CI/CD pipeline, runs on every push to main
- **Gunicorn** — 4-worker production server inside Docker

### CI/CD Pipeline Tools
- **flake8** — Python code style linter
- **bandit** — Python security vulnerability scanner
- **pytest 8.2.2** — test framework
- **pytest-flask 1.3.0** — Flask-specific test utilities
- **pytest-cov** — test coverage reporting
- **curl** — container smoke test (verifies app responds after Docker build)

### Security
- **Werkzeug bcrypt** — password hashing
- **Flask sessions** — signed with `SECRET_KEY`, expire after 8 hours
- **Role-based access control** — enforced at backend on every route
- **Audit logging** — SQLAlchemy model recording every sensitive action
- **Input validation** — all POST routes validate before touching database
- **Environment variables** — secrets never hardcoded in source code

### Development Tools
- **VS Code** — code editor
- **Git + GitHub** — version control and repository hosting
- **Virtual environment (venv)** — isolated Python dependency management
