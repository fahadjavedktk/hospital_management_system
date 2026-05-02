# Hospital Management System
 
A role-based hospital management web application built with **Python Flask**, **SQLAlchemy**, and **Bootstrap 5**. Supports five user roles — Admin, Doctor, Lab, Pharmacy, and Patient — each with their own secure dashboard.
 
Containerised with Docker and shipped with a GitHub Actions CI/CD pipeline.
 
---
 
## Features
 
| Role | What they can do |
|------|-----------------|
| **Admin** | Add / delete patients, manage all records |
| **Doctor** | View patient list, write prescriptions, order lab tests |
| **Lab** | View pending lab requests, enter results |
| **Pharmacy** | Add medicines, manage stock and pricing |
| **Patient** | View their own lab results and prescriptions only |
 
**Security highlights**
- Passwords hashed with Werkzeug (bcrypt-backed)
- Role-based access control on every API endpoint
- Session expires after 8 hours of inactivity
- Full audit log — every sensitive action is recorded with user, action, and IP
- Input validation on all POST routes
- Database rollback on every failed write
- No secrets in source code — all config via environment variables
---
 
## Project Structure
 
```
hospital_fixed/
├── app.py                  # Main Flask application (routes, models, auth)
├── test_app.py             # Pytest test suite (18 tests)
├── requirements.txt        # Python dependencies with pinned versions
├── Dockerfile              # Production Docker image (Gunicorn)
├── docker-compose.yml      # Full stack: app + PostgreSQL
├── ci-cd.yml               # GitHub Actions pipeline
├── .env.example            # Template for environment variables
├── .gitignore
└── templates/
    ├── base.html           # Shared navbar layout
    ├── home.html           # Public landing page
    ├── login.html          # Login form
    ├── admin.html          # Admin dashboard
    ├── doctor.html         # Doctor dashboard
    ├── patient_form.html   # Doctor prescription form
    ├── lab.html            # Lab dashboard
    ├── pharmacy.html       # Pharmacy dashboard
    ├── patient.html        # Patient self-view
    └── user.html           # General user panel
```
 
---
 
## Requirements
 
- Python 3.10 or higher
- pip
- Docker + Docker Compose (for containerised deployment)
---
 
## How to Run
 
### Option 1 — Run locally (quickest, for development)
 
**Step 1 — Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/hospital-management-system.git
cd hospital-management-system
```
 
**Step 2 — Create a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate
 
# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```
 
**Step 3 — Install dependencies**
```bash
pip install -r requirements.txt
```
 
**Step 4 — Create your environment file**
```bash
# Copy the example file
cp .env.example .env
```
 
Open `.env` and set your `SECRET_KEY`:
```
SECRET_KEY=any-long-random-string-you-choose
DATABASE_URL=sqlite:///hospital.db
FLASK_DEBUG=false
```
 
Generate a proper secret key with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
 
**Step 5 — Run the app**
```bash
python app.py
```
 
Open your browser at: **http://localhost:5000**
 
---
 
### Option 2 — Run with Docker (recommended for production)
 
**Step 1 — Clone and enter the project**
```bash
git clone https://github.com/YOUR_USERNAME/hospital-management-system.git
cd hospital-management-system
```
 
**Step 2 — Create your environment file**
```bash
cp .env.example .env
```
 
Edit `.env` with real values:
```
SECRET_KEY=your-long-random-secret-key
DATABASE_URL=postgresql://hospital_user:YOUR_PASSWORD@db:5432/hospital
DB_PASSWORD=YOUR_PASSWORD
FLASK_DEBUG=false
```
 
**Step 3 — Build and start**
```bash
docker compose up --build
```
 
Open your browser at: **http://localhost:5000**
 
To run in the background:
```bash
docker compose up --build -d
```
 
To stop:
```bash
docker compose down
```
 
To stop and delete all data:
```bash
docker compose down -v
```
 
---
 
### Option 3 — Run with SQLite only (no PostgreSQL)
 
If you do not want to use PostgreSQL, keep the `.env` as:
```
DATABASE_URL=sqlite:///hospital.db
```
 
Then just run:
```bash
python app.py
```
 
SQLite is fine for development and small deployments. For a real hospital with multiple concurrent users, use PostgreSQL (Option 2).
 
---
 
## Default Login Credentials
 
> **Change all passwords immediately after first login in production.**
 
| Username | Password | Role |
|----------|----------|------|
| `admin` | `Admin@2024!` | Admin |
| `doctor` | `Doctor@2024!` | Doctor |
| `lab` | `Lab@2024!` | Lab |
| `pharma` | `Pharma@2024!` | Pharmacy |
| `patient` | `Patient@2024!` | Patient |
 
These are created automatically on first startup.
 
---
 
## Running the Tests
 
```bash
# Make sure your virtual environment is active
pytest
 
# With coverage report
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```
 
The test suite covers:
- Home page loads correctly
- Login succeeds / fails / rejects empty credentials
- All dashboards redirect unauthenticated users
- Admin can add patients, invalid data is rejected
- Role isolation — patients cannot access patient list, pharmacy cannot view lab, etc.
---
 
## CI/CD Pipeline
 
The GitHub Actions pipeline runs automatically on every push to `main`:
 
1. **Checkout** — pulls the latest code
2. **Setup Python 3.10**
3. **Install dependencies**
4. **Lint** — `flake8` checks code style (max line length 120)
5. **Security scan** — `bandit` scans for Python security issues
6. **Run tests** — `pytest` with 70% minimum coverage requirement
7. **Build Docker image** — verifies the container builds cleanly
8. **Smoke test** — starts the container and checks `http://localhost:5000/` returns 200
To use the pipeline, push your code to GitHub with the `ci-cd.yml` file at `.github/workflows/ci-cd.yml`.
 
---
 
## Database
 
### Development
Uses **SQLite** by default. The database file `hospital.db` is created automatically in the project folder on first run. No setup needed.
 
### Production (PostgreSQL)
For hospital deployment, switch to PostgreSQL by setting:
```
DATABASE_URL=postgresql://hospital_user:PASSWORD@db:5432/hospital
```
This is already configured in `docker-compose.yml`. PostgreSQL handles concurrent users, provides proper transactions, and supports automated backups.
 
### Database tables
 
| Table | Purpose |
|-------|---------|
| `user_account` | All system users with hashed passwords and roles |
| `patient` | Patient records linked to user accounts |
| `prescription` | Doctor-issued prescriptions (medicine + quantity) |
| `lab_request` | Lab test orders and results |
| `medicine` | Pharmacy inventory with stock and price |
| `audit_log` | Immutable record of every sensitive action |
 
---
 
## Environment Variables Reference
 
| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask session signing key. Must be random and secret. |
| `DATABASE_URL` | Yes | SQLAlchemy connection string. |
| `DB_PASSWORD` | Docker only | PostgreSQL password used by docker-compose. |
| `FLASK_DEBUG` | No | Set to `true` only for local dev. Default: `false`. |
 
---
 
## Deployment Checklist (before going live)
 
- [ ] Change all default passwords in the database
- [ ] Set a strong random `SECRET_KEY` (32+ characters)
- [ ] Switch `DATABASE_URL` to PostgreSQL
- [ ] Set `FLASK_DEBUG=false`
- [ ] Put Nginx in front of the app for HTTPS (SSL certificate via Let's Encrypt)
- [ ] Set up automated daily PostgreSQL backups (`pg_dump`)
- [ ] Restrict server firewall to ports 80 and 443 only
- [ ] Add users through the admin panel instead of using default accounts
---
 
## Tech Stack
 
| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10, Flask 3.0 |
| Database ORM | Flask-SQLAlchemy |
| Authentication | Flask-Login + Werkzeug password hashing |
| Database (dev) | SQLite |
| Database (prod) | PostgreSQL 15 |
| Frontend | Bootstrap 5.3, Vanilla JS |
| Server | Gunicorn (4 workers) |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Testing | Pytest + pytest-flask |
 
---
 
## License
 
MIT License. Free to use and modify.