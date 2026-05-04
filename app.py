import os
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# -------- CONFIG --------
app.secret_key = os.environ.get("SECRET_KEY", "change-this-before-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///hospital.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_page"


# -------- MODELS --------

class UserAccount(db.Model):
    __tablename__ = "user_account"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Doctor(db.Model):
    """Doctor profile — stores name, specialisation, phone."""
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    specialisation  = db.Column(db.String(100), nullable=False)
    phone           = db.Column(db.String(20), nullable=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=True)
    is_active       = db.Column(db.Boolean, default=True)


class Patient(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(100), nullable=False)
    age       = db.Column(db.Integer, nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    user_id   = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=True)
    doctor    = db.relationship("Doctor", backref="patients")


class LabRequest(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    patient_id   = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    test         = db.Column(db.String(100), nullable=False)
    result       = db.Column(db.String(200), default="Pending")
    report_image = db.Column(db.Text, nullable=True)   # base64 encoded image
    


class Prescription(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    medicine   = db.Column(db.String(100), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False)


class Medicine(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Float, nullable=False, default=0.0)


class AuditLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.String(80))
    action     = db.Column(db.String(200))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now())


# -------- AUTH --------

class AuthUser(UserMixin):
    def __init__(self, u):
        self.id       = str(u.id)
        self.username = u.username
        self.role     = u.role

@login_manager.user_loader
def load_user(user_id):
    u = UserAccount.query.get(int(user_id))
    if u and u.is_active:
        return AuthUser(u)
    return None


# -------- HELPERS --------

def audit(action):
    try:
        db.session.add(AuditLog(
            user_id    = current_user.username if current_user.is_authenticated else "anon",
            action     = action,
            ip_address = request.remote_addr
        ))
        db.session.commit()
    except Exception:
        pass


def role_required(*roles):
    if current_user.role not in roles:
        return jsonify({"error": "Access denied"}), 403
    return None


LAB_TESTS = ["X-Ray", "Blood Test", "MRI", "CT Scan"]


# -------- SEED USERS --------

def seed_users():
    defaults = [
        ("admin",   "Admin@2024!",   "admin"),
        ("doctor",  "Doctor@2024!",  "doctor"),
        ("lab",     "Lab@2024!",     "lab"),
        ("pharma",  "Pharma@2024!",  "pharmacy"),
        ("patient", "Patient@2024!", "patient"),
    ]
    for username, password, role in defaults:
        if not UserAccount.query.filter_by(username=username).first():
            u = UserAccount(username=username, role=role)
            u.set_password(password)
            db.session.add(u)
    db.session.commit()


def init_db():
    """
    Initialize database tables and seed default users.
    Uses checkfirst to avoid crash when multiple Gunicorn workers
    all try to create tables at the same time.
    """
    with app.app_context():
        # create_all() skips tables that already exist — safe to call every time
        db.create_all()
        try:
            seed_users()
        except Exception:
            db.session.rollback()


init_db()


# ======================================================
# ROUTES
# ======================================================

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect("/dashboard")
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = UserAccount.query.filter_by(username=username, is_active=True).first()
    if user and user.check_password(password):
        login_user(AuthUser(user), remember=False)
        session.permanent = True
        audit(f"LOGIN username={username}")
        return jsonify({"msg": "ok"})

    audit(f"FAILED_LOGIN username={username}")
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/logout")
@login_required
def logout():
    audit("LOGOUT")
    logout_user()
    return redirect("/")


@app.route("/dashboard")
@login_required
def dashboard():
    templates = {
        "admin":    "admin.html",
        "doctor":   "doctor.html",
        "lab":      "lab.html",
        "pharmacy": "pharmacy.html",
        "patient":  "patient.html",
    }
    t = templates.get(current_user.role)
    if not t:
        return "Unknown role", 403
    return render_template(t)


# ======================================================
# ADMIN — DOCTOR MANAGEMENT
# ======================================================

@app.route("/doctors")
@login_required
def get_doctors():
    denied = role_required("admin", "doctor")
    if denied:
        return denied
    docs = Doctor.query.filter_by(is_active=True).all()
    return jsonify([{
        "id": d.id,
        "name": d.name,
        "specialisation": d.specialisation,
        "phone": d.phone or ""
    } for d in docs])


@app.route("/add_doctor", methods=["POST"])
@login_required
def add_doctor():
    denied = role_required("admin")
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    name           = str(data.get("name", "")).strip()
    specialisation = str(data.get("specialisation", "")).strip()
    phone          = str(data.get("phone", "")).strip()
    username       = str(data.get("username", "")).strip()
    password       = str(data.get("password", "")).strip()

    if not name:
        return jsonify({"error": "Doctor name is required"}), 400
    if not specialisation:
        return jsonify({"error": "Specialisation is required"}), 400

    # Strip "Dr." prefix if user typed it — the UI adds it automatically
    if name.lower().startswith("dr. "):
        name = name[4:].strip()
    elif name.lower().startswith("dr."):
        name = name[3:].strip()

    try:
        user_id = None
        # Optionally create a login account for this doctor
        if username and password:
            if UserAccount.query.filter_by(username=username).first():
                return jsonify({"error": f"Username '{username}' is already taken"}), 400
            u = UserAccount(username=username, role="doctor")
            u.set_password(password)
            db.session.add(u)
            db.session.flush()        # write to DB to generate id
            db.session.refresh(u)     # ensure u.id is populated from DB
            user_id = u.id

        doc = Doctor(
            name=name,
            specialisation=specialisation,
            phone=phone or None,
            user_id=user_id
        )
        db.session.add(doc)
        db.session.commit()
        audit(f"ADD_DOCTOR name={name}")
        return jsonify({"msg": "Doctor added", "id": doc.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add doctor"}), 500


@app.route("/delete_doctor/<int:doctor_id>", methods=["DELETE"])
@login_required
def delete_doctor(doctor_id):
    denied = role_required("admin")
    if denied:
        return denied

    doc = Doctor.query.get_or_404(doctor_id)
    doc_name = doc.name

    # Check if any patients are still assigned
    assigned = Patient.query.filter_by(doctor_id=doctor_id).count()
    if assigned > 0:
        return jsonify({"error": f"Cannot remove — {assigned} patient(s) are assigned to this doctor. Reassign them first."}), 400

    try:
        # Deactivate the linked login account if one exists
        if doc.user_id:
            linked_user = UserAccount.query.get(doc.user_id)
            if linked_user:
                linked_user.is_active = False

        # Hard delete the doctor record
        db.session.delete(doc)
        db.session.commit()
        audit(f"DELETE_DOCTOR id={doctor_id} name={doc_name}")
        return jsonify({"msg": f"Dr. {doc_name} removed successfully"})
    except Exception as e:
        db.session.rollback()
        # If FK error, give a helpful message
        err = str(e)
        if "foreign key" in err.lower() or "constraint" in err.lower():
            return jsonify({"error": "Cannot remove this doctor because they are referenced by other records. Contact your system administrator."}), 400
        return jsonify({"error": f"Failed to remove doctor: {err}"}), 500


@app.route("/update_doctor/<int:doctor_id>", methods=["POST"])
@login_required
def update_doctor(doctor_id):
    """Let admin fix doctor name or specialisation."""
    denied = role_required("admin")
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    doc  = Doctor.query.get_or_404(doctor_id)

    name = str(data.get("name", doc.name)).strip()
    spec = str(data.get("specialisation", doc.specialisation)).strip()

    # Strip accidental "Dr." prefix
    if name.lower().startswith("dr. "):
        name = name[4:].strip()
    elif name.lower().startswith("dr."):
        name = name[3:].strip()

    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400
    if not spec:
        return jsonify({"error": "Specialisation cannot be empty"}), 400

    try:
        doc.name           = name
        doc.specialisation = spec
        db.session.commit()
        audit(f"UPDATE_DOCTOR id={doctor_id} name={name}")
        return jsonify({"msg": "Doctor updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update: {str(e)}"}), 500


# ======================================================
# ADMIN — PATIENT MANAGEMENT
# ======================================================

@app.route("/add_patient", methods=["POST"])
@login_required
def add_patient():
    denied = role_required("admin")
    if denied:
        return denied

    data      = request.get_json(silent=True) or {}
    name      = str(data.get("name", "")).strip()
    age       = data.get("age")
    doctor_id = data.get("doctor_id")

    if not name:
        return jsonify({"error": "Patient name is required"}), 400
    if not doctor_id:
        return jsonify({"error": "Please select a doctor"}), 400

    try:
        age = int(age)
        if age < 0 or age > 150:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Age must be a number between 0 and 150"}), 400

    doctor = Doctor.query.get(int(doctor_id))
    if not doctor or not doctor.is_active:
        return jsonify({"error": "Selected doctor not found"}), 400

    try:
        db.session.add(Patient(name=name, age=age, doctor_id=doctor.id))
        db.session.commit()
        audit(f"ADD_PATIENT name={name} doctor_id={doctor_id}")
        return jsonify({"msg": "Patient added"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to add patient: {str(e)}"}), 500


@app.route("/patients")
@login_required
def patients():
    denied = role_required("admin", "doctor")
    if denied:
        return denied

    if current_user.role == "doctor":
        # If doctor has a linked profile, show only their patients
        # If no profile linked (account created via Staff tab), show all patients
        doctor = Doctor.query.filter_by(user_id=int(current_user.id)).first()
        if doctor:
            p = Patient.query.filter_by(doctor_id=doctor.id).all()
        else:
            p = Patient.query.all()
    else:
        # Admin sees all patients
        p = Patient.query.all()

    return jsonify([{
        "id":        x.id,
        "name":      x.name,
        "age":       x.age,
        "doctor":    x.doctor.name if x.doctor else "Unassigned",
        "doctor_id": x.doctor_id
    } for x in p])


@app.route("/delete_patient/<int:patient_id>", methods=["DELETE"])
@login_required
def delete_patient(patient_id):
    denied = role_required("admin")
    if denied:
        return denied

    patient = Patient.query.get_or_404(patient_id)
    try:
        db.session.delete(patient)
        db.session.commit()
        audit(f"DELETE_PATIENT id={patient_id}")
        return jsonify({"msg": "Deleted"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete"}), 500


# ======================================================
# ADMIN — STAFF / USER MANAGEMENT
# ======================================================

@app.route("/add_staff", methods=["POST"])
@login_required
def add_staff():
    """Create a login account for lab, pharmacy, or other roles."""
    denied = role_required("admin")
    if denied:
        return denied

    data     = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    role     = str(data.get("role", "")).strip()

    allowed_roles = ["doctor", "lab", "pharmacy", "patient"]
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if role not in allowed_roles:
        return jsonify({"error": f"Role must be one of: {', '.join(allowed_roles)}"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if UserAccount.query.filter_by(username=username).first():
        return jsonify({"error": f"Username '{username}' is already taken"}), 400

    try:
        u = UserAccount(username=username, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        audit(f"ADD_STAFF username={username} role={role}")
        return jsonify({"msg": f"Staff account created for {username}"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create account"}), 500


@app.route("/staff")
@login_required
def get_staff():
    denied = role_required("admin")
    if denied:
        return denied
    users = UserAccount.query.filter(
        UserAccount.role != "admin",
        UserAccount.is_active == True
    ).all()
    return jsonify([{
        "id":       u.id,
        "username": u.username,
        "role":     u.role
    } for u in users])


@app.route("/deactivate_staff/<int:user_id>", methods=["DELETE"])
@login_required
def deactivate_staff(user_id):
    denied = role_required("admin")
    if denied:
        return denied

    u = UserAccount.query.get_or_404(user_id)
    if u.role == "admin":
        return jsonify({"error": "Cannot deactivate an admin account"}), 400
    try:
        u.is_active = False
        db.session.commit()
        audit(f"DEACTIVATE_STAFF username={u.username}")
        return jsonify({"msg": "Account deactivated"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to deactivate"}), 500


# ======================================================
# ADMIN — DIAGNOSTICS
# ======================================================

@app.route("/debug/doctor_links")
@login_required
def debug_doctor_links():
    """Admin-only: shows which doctor accounts are linked to which profiles."""
    denied = role_required("admin")
    if denied:
        return denied

    doctors  = Doctor.query.all()
    accounts = UserAccount.query.filter_by(role="doctor").all()

    return jsonify({
        "doctor_profiles": [{
            "id":       d.id,
            "name":     d.name,
            "user_id":  d.user_id,
            "linked_username": UserAccount.query.get(d.user_id).username if d.user_id else None
        } for d in doctors],
        "doctor_accounts": [{
            "id":       u.id,
            "username": u.username,
            "is_active": u.is_active
        } for u in accounts]
    })


@app.route("/link_doctor", methods=["POST"])
@login_required
def link_doctor():
    """Admin: link an existing doctor login account to a doctor profile."""
    denied = role_required("admin")
    if denied:
        return denied

    data       = request.get_json(silent=True) or {}
    doctor_id  = data.get("doctor_id")
    account_id = data.get("account_id")

    if not doctor_id or not account_id:
        return jsonify({"error": "doctor_id and account_id are required"}), 400

    doctor  = Doctor.query.get_or_404(int(doctor_id))
    account = UserAccount.query.get_or_404(int(account_id))

    if account.role != "doctor":
        return jsonify({"error": "That account is not a doctor role"}), 400

    try:
        doctor.user_id  = account.id
        db.session.commit()
        audit(f"LINK_DOCTOR doctor_id={doctor_id} account_id={account_id}")
        return jsonify({"msg": f"Dr. {doctor.name} linked to account '{account.username}'"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ======================================================
# DOCTOR
# ======================================================

@app.route("/patient/<int:patient_id>")
@login_required
def patient_detail(patient_id):
    denied = role_required("doctor")
    if denied:
        return denied

    p = Patient.query.get_or_404(patient_id)

    # If doctor has a linked profile, verify patient is assigned to them
    # If no profile linked yet (e.g. account created via Staff tab), allow access
    doctor = Doctor.query.filter_by(user_id=int(current_user.id)).first()
    if doctor and p.doctor_id != doctor.id:
        return "Access denied — this patient is not assigned to you.", 403

    audit(f"VIEW_PATIENT id={patient_id}")
    return render_template("patient_form.html", patient=p, tests=LAB_TESTS)


@app.route("/prescribe", methods=["POST"])
@login_required
def prescribe():
    denied = role_required("doctor")
    if denied:
        return denied

    data       = request.get_json(silent=True) or {}
    patient_id = data.get("patient_id")
    medicine   = str(data.get("medicine", "")).strip()
    test       = str(data.get("test", "")).strip()

    try:
        qty = int(data.get("qty", 0))
        if qty < 1:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Quantity must be a positive number"}), 400

    if not medicine:
        return jsonify({"error": "Medicine name is required"}), 400

    patient = Patient.query.get_or_404(int(patient_id))

    # Security: if doctor has a linked profile, verify patient is assigned to them
    # If no profile linked (account created separately), allow prescribing
    doctor = Doctor.query.filter_by(user_id=int(current_user.id)).first()
    if doctor and patient.doctor_id != doctor.id:
        return jsonify({"error": "Access denied — this patient is not assigned to you."}), 403

    # Check stock BEFORE writing anything to DB
    med_record = Medicine.query.filter(
        db.func.lower(Medicine.name) == medicine.lower()
    ).first()
    if med_record and med_record.stock < qty:
        return jsonify({"error": f"Insufficient stock for {medicine}. Available: {med_record.stock}"}), 400

    try:
        db.session.add(Prescription(
            patient_id=patient.id,
            medicine=medicine,
            quantity=qty
        ))
        if test and test in LAB_TESTS:
            db.session.add(LabRequest(
                patient_id=patient.id,
                test=test,
                result="Pending"
            ))
        # Deduct stock
        if med_record:
            med_record.stock -= qty
        db.session.commit()
        audit(f"PRESCRIBE patient_id={patient.id} medicine={medicine} qty={qty}")
        return jsonify({"msg": "Saved"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to save prescription: {str(e)}"}), 500


# ======================================================
# LAB
# ======================================================

@app.route("/lab")
@login_required
def lab():
    denied = role_required("lab", "doctor", "admin")
    if denied:
        return denied
    requests = (
        db.session.query(LabRequest, Patient)
        .join(Patient, LabRequest.patient_id == Patient.id)
        .all()
    )
    return jsonify([{
        "id":           l.id,
        "patient_id":   l.patient_id,
        "patient_name": p.name,
        "doctor_name":  p.doctor.name if p.doctor else "Unassigned",
        "test":         l.test,
        "result":       l.result,
        "has_image":    bool(l.report_image),
        "report_image": l.report_image or ""
    } for l, p in requests])


@app.route("/lab_update", methods=["POST"])
@login_required
def lab_update():
    denied = role_required("lab")
    if denied:
        return denied

    data         = request.get_json(silent=True) or {}
    lab_id       = data.get("id")
    result       = str(data.get("result", "")).strip()
    report_image = data.get("report_image", None)   # base64 string or None

    if not result:
        return jsonify({"error": "Result text is required"}), 400

    lr = LabRequest.query.get_or_404(int(lab_id))
    try:
        lr.result = result
        if report_image:
            # Validate it looks like a base64 image
            if report_image.startswith("data:image/"):
                lr.report_image = report_image
            else:
                return jsonify({"error": "Invalid image format"}), 400
        db.session.commit()
        audit(f"LAB_UPDATE id={lab_id} result={result} has_image={bool(report_image)}")
        return jsonify({"msg": "Updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update: {str(e)}"}), 500


@app.route("/lab_image/<int:lab_id>")
@login_required
def lab_image(lab_id):
    """Return just the image for a specific lab request — accessible by doctor and lab."""
    denied = role_required("lab", "doctor", "admin", "patient")
    if denied:
        return denied
    lr = LabRequest.query.get_or_404(lab_id)
    return jsonify({
        "id":           lr.id,
        "report_image": lr.report_image or "",
        "has_image":    bool(lr.report_image)
    })


# ======================================================
# PHARMACY
# ======================================================

@app.route("/add_med", methods=["POST"])
@login_required
def add_med():
    denied = role_required("pharmacy")
    if denied:
        return denied

    data  = request.get_json(silent=True) or {}
    name  = str(data.get("name", "")).strip()

    try:
        stock = int(data.get("stock", 0))
        price = float(data.get("price", 0))
        if stock < 0 or price < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Stock and price must be valid positive numbers"}), 400

    if not name:
        return jsonify({"error": "Medicine name is required"}), 400

    try:
        db.session.add(Medicine(name=name, stock=stock, price=price))
        db.session.commit()
        audit(f"ADD_MEDICINE name={name}")
        return jsonify({"msg": "Added"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to add medicine"}), 500


@app.route("/meds")
@login_required
def meds():
    denied = role_required("pharmacy", "doctor", "admin")
    if denied:
        return denied
    return jsonify([{
        "id":    m.id,
        "name":  m.name,
        "stock": m.stock,
        "price": m.price
    } for m in Medicine.query.all()])


@app.route("/delete_med/<int:med_id>", methods=["DELETE"])
@login_required
def delete_med(med_id):
    denied = role_required("pharmacy")
    if denied:
        return denied
    med = Medicine.query.get_or_404(med_id)
    try:
        db.session.delete(med)
        db.session.commit()
        audit(f"DELETE_MEDICINE id={med_id} name={med.name}")
        return jsonify({"msg": "Medicine deleted"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete medicine"}), 500


@app.route("/update_stock/<int:med_id>", methods=["POST"])
@login_required
def update_stock(med_id):
    denied = role_required("pharmacy")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    med = Medicine.query.get_or_404(med_id)
    try:
        new_stock = int(data.get("stock", 0))
        new_price = float(data.get("price", med.price))
        if new_stock < 0 or new_price < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Stock and price must be valid positive numbers"}), 400
    try:
        med.stock = new_stock
        med.price = new_price
        db.session.commit()
        audit(f"UPDATE_STOCK id={med_id} stock={new_stock} price={new_price}")
        return jsonify({"msg": "Updated"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update"}), 500


# ======================================================
# PATIENT self-view
# ======================================================

@app.route("/my")
@login_required
def my():
    denied = role_required("patient")
    if denied:
        return denied

    p = Patient.query.filter_by(user_id=current_user.id).first()
    if not p:
        return jsonify({"error": "No patient record linked to your account"}), 404

    audit(f"PATIENT_SELF_VIEW patient_id={p.id}")
    return jsonify({
        "patient": p.name,
        "doctor":  p.doctor.name if p.doctor else "Not assigned",
        "labs": [
            {
                "test":      l.test,
                "result":    l.result,
                "has_image": bool(l.report_image),
                "image":     l.report_image or ""
            }
            for l in LabRequest.query.filter_by(patient_id=p.id).all()
        ],
        "pres": [
            {"medicine": pr.medicine, "quantity": pr.quantity}
            for pr in Prescription.query.filter_by(patient_id=p.id).all()
        ]
    })


# ======================================================
# DEBUG — admin only, remove in production
# ======================================================

@app.route("/debug/doctor_link")
@login_required
def debug_doctor_link():
    """Shows the logged-in doctor's account link status."""
    if current_user.role not in ("admin", "doctor"):
        return jsonify({"error": "forbidden"}), 403
    uid = int(current_user.id)
    doctor = Doctor.query.filter_by(user_id=uid).first()
    all_doctors = Doctor.query.all()
    return jsonify({
        "current_user_id":       uid,
        "current_user_username": current_user.username,
        "current_user_role":     current_user.role,
        "doctor_profile_found":  doctor is not None,
        "doctor_name":           doctor.name if doctor else None,
        "doctor_user_id":        doctor.user_id if doctor else None,
        "all_doctors": [{
            "id": d.id,
            "name": d.name,
            "user_id": d.user_id
        } for d in all_doctors]
    })


# ======================================================
# ERROR HANDLERS
# ======================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Access denied"}), 403

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error"}), 500


# ======================================================
# RUN
# ======================================================

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
