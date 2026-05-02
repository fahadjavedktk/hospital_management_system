import pytest
from app import app, db, seed_users


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        seed_users()

    with app.test_client() as client:
        yield client


def login_as(client, username, password):
    return client.post(
        "/login",
        json={"username": username, "password": password},
        content_type="application/json"
    )


# -------- HOME --------

def test_home_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Hospital Management System" in res.data


# -------- LOGIN --------

def test_login_page_loads(client):
    res = client.get("/login")
    assert res.status_code == 200


def test_login_valid_admin(client):
    res = login_as(client, "admin", "Admin@2024!")
    assert res.status_code == 200
    assert b"ok" in res.data


def test_login_valid_doctor(client):
    res = login_as(client, "doctor", "Doctor@2024!")
    assert res.status_code == 200


def test_login_wrong_password(client):
    res = login_as(client, "admin", "wrongpassword")
    assert res.status_code == 401


def test_login_unknown_user(client):
    res = login_as(client, "nobody", "abc123")
    assert res.status_code == 401


def test_login_empty_credentials(client):
    res = login_as(client, "", "")
    assert res.status_code == 400


# -------- AUTH PROTECTION --------

def test_dashboard_requires_login(client):
    res = client.get("/dashboard")
    assert res.status_code == 302  # redirect to login


def test_patients_requires_login(client):
    res = client.get("/patients")
    assert res.status_code == 302


def test_lab_requires_login(client):
    res = client.get("/lab")
    assert res.status_code == 302


# -------- ADMIN ROUTES --------

def test_add_patient_as_admin(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post(
        "/add_patient",
        json={"name": "Test Patient", "age": 30, "doctor": "Dr. Smith"},
        content_type="application/json"
    )
    assert res.status_code == 200


def test_add_patient_missing_name(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post(
        "/add_patient",
        json={"name": "", "age": 30, "doctor": "Dr. Smith"},
        content_type="application/json"
    )
    assert res.status_code == 400


def test_add_patient_invalid_age(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post(
        "/add_patient",
        json={"name": "Test", "age": 999, "doctor": "Dr. Smith"},
        content_type="application/json"
    )
    assert res.status_code == 400


def test_add_patient_as_doctor_forbidden(client):
    login_as(client, "doctor", "Doctor@2024!")
    res = client.post(
        "/add_patient",
        json={"name": "Test", "age": 25, "doctor": "Dr. Smith"},
        content_type="application/json"
    )
    assert res.status_code == 403


# -------- ROLE ISOLATION --------

def test_patient_cannot_access_all_patients(client):
    login_as(client, "patient", "Patient@2024!")
    res = client.get("/patients")
    assert res.status_code == 403


def test_pharmacy_cannot_view_lab(client):
    login_as(client, "pharma", "Pharma@2024!")
    res = client.get("/lab")
    assert res.status_code == 403


def test_lab_cannot_add_medicine(client):
    login_as(client, "lab", "Lab@2024!")
    res = client.post(
        "/add_med",
        json={"name": "Paracetamol", "stock": 100, "price": 10.0},
        content_type="application/json"
    )
    assert res.status_code == 403
