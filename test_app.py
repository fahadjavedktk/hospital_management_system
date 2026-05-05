import pytest
from app import app, db, seed_users, Doctor


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        seed_users()
        d = Doctor(name="Test Doctor", specialisation="General")
        db.session.add(d)
        db.session.commit()

    with app.test_client() as c:
        yield c


def login_as(client, username, password):
    return client.post(
        "/login",
        json={"username": username, "password": password},
        content_type="application/json"
    )


def get_first_doctor_id(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.get("/doctors")
    data = res.get_json()
    if not data:
        return None
    return data[0]["id"]


# ── HOME ────────────────────────────────────────────────────────
def test_home_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Hospital" in res.data


# ── LOGIN ────────────────────────────────────────────────────────
def test_login_valid_admin(client):
    assert login_as(client, "admin", "Admin@2024!").status_code == 200

def test_login_valid_doctor(client):
    assert login_as(client, "doctor", "Doctor@2024!").status_code == 200

def test_login_wrong_password(client):
    assert login_as(client, "admin", "wrong").status_code == 401

def test_login_unknown_user(client):
    assert login_as(client, "nobody", "abc").status_code == 401

def test_login_empty_credentials(client):
    assert login_as(client, "", "").status_code == 400


# ── AUTH PROTECTION ──────────────────────────────────────────────
def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302

def test_patients_requires_login(client):
    assert client.get("/patients").status_code == 302

def test_doctors_requires_login(client):
    assert client.get("/doctors").status_code == 302

def test_lab_requires_login(client):
    assert client.get("/lab").status_code == 302


# ── DOCTOR MANAGEMENT ────────────────────────────────────────────
def test_add_doctor_as_admin(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post("/add_doctor",
        json={"name": "Ahmed", "specialisation": "Cardiology"},
        content_type="application/json")
    assert res.status_code == 200

def test_add_doctor_missing_name(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post("/add_doctor",
        json={"name": "", "specialisation": "Cardiology"},
        content_type="application/json")
    assert res.status_code == 400

def test_add_doctor_missing_spec(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post("/add_doctor",
        json={"name": "Dr X", "specialisation": ""},
        content_type="application/json")
    assert res.status_code == 400

def test_doctor_cannot_add_doctor(client):
    login_as(client, "doctor", "Doctor@2024!")
    res = client.post("/add_doctor",
        json={"name": "Rogue", "specialisation": "X"},
        content_type="application/json")
    assert res.status_code == 403


# ── PATIENT MANAGEMENT ───────────────────────────────────────────
def test_add_patient_as_admin(client):
    login_as(client, "admin", "Admin@2024!")
    doc_id = get_first_doctor_id(client)
    res = client.post("/add_patient",
        json={"name": "Ali Khan", "age": 35, "doctor_id": doc_id},
        content_type="application/json")
    assert res.status_code == 200

def test_add_patient_no_doctor(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post("/add_patient",
        json={"name": "Ali Khan", "age": 35, "doctor_id": None},
        content_type="application/json")
    assert res.status_code == 400

def test_add_patient_invalid_age(client):
    """Age field removed — test invalid date_of_birth instead."""
    login_as(client, "admin", "Admin@2024!")
    doc_id = get_first_doctor_id(client)
    res = client.post("/add_patient",
        json={"name": "Ali", "date_of_birth": "not-a-date", "doctor_id": doc_id},
        content_type="application/json")
    assert res.status_code == 400


# ── STAFF MANAGEMENT ─────────────────────────────────────────────
def test_add_staff_as_admin(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post("/add_staff",
        json={"username": "lab2", "password": "Lab@12345", "role": "lab"},
        content_type="application/json")
    assert res.status_code == 200

def test_add_staff_weak_password(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post("/add_staff",
        json={"username": "lab3", "password": "abc", "role": "lab"},
        content_type="application/json")
    assert res.status_code == 400

def test_add_staff_invalid_role(client):
    login_as(client, "admin", "Admin@2024!")
    res = client.post("/add_staff",
        json={"username": "x", "password": "Password1!", "role": "hacker"},
        content_type="application/json")
    assert res.status_code == 400


# ── ROLE ISOLATION ───────────────────────────────────────────────
def test_patient_cannot_see_all_patients(client):
    login_as(client, "patient", "Patient@2024!")
    assert client.get("/patients").status_code == 403

def test_pharmacy_cannot_view_lab(client):
    login_as(client, "pharma", "Pharma@2024!")
    assert client.get("/lab").status_code == 403

def test_lab_cannot_add_medicine(client):
    login_as(client, "lab", "Lab@2024!")
    res = client.post("/add_med",
        json={"name": "Paracetamol", "stock": 100, "price": 10.0},
        content_type="application/json")
    assert res.status_code == 403


# ── PHARMACY ─────────────────────────────────────────────────────
def test_pharmacy_add_and_delete_medicine(client):
    login_as(client, "pharma", "Pharma@2024!")
    res = client.post("/add_med",
        json={"name": "Aspirin", "stock": 100, "price": 5.0},
        content_type="application/json")
    assert res.status_code == 200
    meds = client.get("/meds").get_json()
    med_id = meds[0]["id"]
    assert client.delete(f"/delete_med/{med_id}").status_code == 200

def test_pharmacy_update_stock(client):
    login_as(client, "pharma", "Pharma@2024!")
    client.post("/add_med",
        json={"name": "Ibuprofen", "stock": 50, "price": 10.0},
        content_type="application/json")
    meds = client.get("/meds").get_json()
    med_id = meds[0]["id"]
    res = client.post(f"/update_stock/{med_id}",
        json={"stock": 200, "price": 12.0},
        content_type="application/json")
    assert res.status_code == 200

def test_lab_cannot_delete_medicine(client):
    login_as(client, "pharma", "Pharma@2024!")
    client.post("/add_med",
        json={"name": "TestMed", "stock": 10, "price": 1.0},
        content_type="application/json")
    meds = client.get("/meds").get_json()
    med_id = meds[0]["id"]
    login_as(client, "lab", "Lab@2024!")
    assert client.delete(f"/delete_med/{med_id}").status_code == 403


# ── PRESCRIPTION ─────────────────────────────────────────────────
def test_prescription_saves_and_deducts_stock(client):
    # Add medicine
    login_as(client, "pharma", "Pharma@2024!")
    client.post("/add_med",
        json={"name": "Paracetamol", "stock": 100, "price": 5.0},
        content_type="application/json")

    # Add patient
    login_as(client, "admin", "Admin@2024!")
    doc_id = get_first_doctor_id(client)
    client.post("/add_patient",
        json={"name": "Test Patient", "age": 30, "doctor_id": doc_id},
        content_type="application/json")

    # Prescribe
    login_as(client, "doctor", "Doctor@2024!")
    patients = client.get("/patients").get_json()
    pid = patients[0]["id"]
    res = client.post("/prescribe",
        json={"patient_id": pid, "medicine": "Paracetamol", "qty": 10, "test": ""},
        content_type="application/json")
    assert res.status_code == 200

    # Verify stock deducted
    login_as(client, "pharma", "Pharma@2024!")
    meds = client.get("/meds").get_json()
    paracetamol = next((m for m in meds if m["name"] == "Paracetamol"), None)
    assert paracetamol is not None
    assert paracetamol["stock"] == 90


# ── LAB ──────────────────────────────────────────────────────────
def test_lab_can_view_requests(client):
    login_as(client, "lab", "Lab@2024!")
    res = client.get("/lab")
    assert res.status_code == 200

def test_lab_update_result(client):
    # Create a lab request via prescription
    login_as(client, "admin", "Admin@2024!")
    doc_id = get_first_doctor_id(client)
    client.post("/add_patient",
        json={"name": "Lab Patient", "age": 25, "doctor_id": doc_id},
        content_type="application/json")

    login_as(client, "doctor", "Doctor@2024!")
    patients = client.get("/patients").get_json()
    pid = patients[0]["id"]
    client.post("/prescribe",
        json={"patient_id": pid, "medicine": "TestMed", "qty": 1, "test": "X-Ray"},
        content_type="application/json")

    # Update result
    login_as(client, "lab", "Lab@2024!")
    labs = client.get("/lab").get_json()
    lab_id = labs[0]["id"]
    res = client.post("/lab_update",
        json={"id": lab_id, "result": "Normal"},
        content_type="application/json")
    assert res.status_code == 200
