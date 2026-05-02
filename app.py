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

# -------- CONFIG (all from environment variables) --------
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
    """Stores all users (admin, doctor, lab, pharmacy, patient)."""
    __tablename__ = "user_account"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    doctor = db.Column(db.String(100), nullable=False)
    # Links a patient record to a UserAccount with role=patient
    user_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=True)


class LabRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    test = db.Column(db.String(100), nullable=False)
    result = db.Column(db.String(200), default="Pending")


class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    medicine = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)


class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Float, nullable=False, default=0.0)


class AuditLog(db.Model):
    """Records every sensitive action for compliance."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80))
    action = db.Column(db.String(200))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now())


# -------- AUTH USER CLASS --------

class AuthUser(UserMixin):
    def __init__(self, user_account):
        self.id = str(user_account.id)
        self.username = user_account.username
        self.role = user_account.role

@login_manager.user_loader
def load_user(user_id):
    u = UserAccount.query.get(int(user_id))
    if u and u.is_active:
        return AuthUser(u)
    return None


# -------- HELPERS --------

def audit(action):
    """Write an audit log entry for the current request."""
    try:
        log = AuditLog(
            user_id=current_user.username if current_user.is_authenticated else "anon",
            action=action,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass  # Never let audit failure crash the main request


def role_required(*roles):
    """Return 403 JSON if current user's role is not in the allowed list."""
    if current_user.role not in roles:
        return jsonify({"error": "Access denied"}), 403
    return None


LAB_TESTS = ["X-Ray", "Blood Test", "MRI", "CT Scan"]


# -------- SEED DEFAULT USERS --------

def seed_users():
    """Create default users on first run if they don't exist."""
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


with app.app_context():
    db.create_all()
    seed_users()


# -------- ROUTES --------

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
        auth_user = AuthUser(user)
        login_user(auth_user, remember=False)
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
    role_template = {
        "admin": "admin.html",
        "doctor": "doctor.html",
        "lab": "lab.html",
        "pharmacy": "pharmacy.html",
        "patient": "patient.html",
    }
    template = role_template.get(current_user.role)
    if not template:
        return "Unknown role", 403
    return render_template(template)


# -------- ADMIN --------

@app.route("/add_patient", methods=["POST"])
@login_required
def add_patient():
    denied = role_required("admin")
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    age = data.get("age")
    doctor = str(data.get("doctor", "")).strip()

    if not name or not doctor:
        return jsonify({"error": "Name and doctor are required"}), 400
    try:
        age = int(age)
        if age < 0 or age > 150:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Age must be a number between 0 and 150"}), 400

    try:
        db.session.add(Patient(name=name, age=age, doctor=doctor))
        db.session.commit()
        audit(f"ADD_PATIENT name={name}")
        return jsonify({"msg": "Patient added"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to add patient"}), 500


@app.route("/patients")
@login_required
def patients():
    denied = role_required("admin", "doctor")
    if denied:
        return denied
    p = Patient.query.all()
    return jsonify([{
        "id": x.id, "name": x.name,
        "age": x.age, "doctor": x.doctor
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


# -------- DOCTOR --------

@app.route("/patient/<int:patient_id>")
@login_required
def patient_detail(patient_id):
    denied = role_required("doctor")
    if denied:
        return denied

    p = Patient.query.get_or_404(patient_id)
    audit(f"VIEW_PATIENT id={patient_id}")
    return render_template("patient_form.html", patient=p, tests=LAB_TESTS)


@app.route("/prescribe", methods=["POST"])
@login_required
def prescribe():
    denied = role_required("doctor")
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    patient_id = data.get("patient_id")
    medicine = str(data.get("medicine", "")).strip()
    test = str(data.get("test", "")).strip()

    try:
        qty = int(data.get("qty", 0))
        if qty < 1:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Quantity must be a positive number"}), 400

    if not medicine:
        return jsonify({"error": "Medicine name is required"}), 400

    patient = Patient.query.get_or_404(int(patient_id))

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
        db.session.commit()
        audit(f"PRESCRIBE patient_id={patient.id} medicine={medicine}")
        return jsonify({"msg": "Saved"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to save prescription"}), 500


# -------- LAB --------

@app.route("/lab")
@login_required
def lab():
    denied = role_required("lab", "doctor", "admin")
    if denied:
        return denied
    return jsonify([{
        "id": l.id,
        "patient_id": l.patient_id,
        "test": l.test,
        "result": l.result
    } for l in LabRequest.query.all()])


@app.route("/lab_update", methods=["POST"])
@login_required
def lab_update():
    denied = role_required("lab")
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    lab_id = data.get("id")
    result = str(data.get("result", "")).strip()

    if not result:
        return jsonify({"error": "Result is required"}), 400

    lr = LabRequest.query.get_or_404(int(lab_id))
    try:
        lr.result = result
        db.session.commit()
        audit(f"LAB_UPDATE id={lab_id} result={result}")
        return jsonify({"msg": "Updated"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update"}), 500


# -------- PHARMACY --------

@app.route("/add_med", methods=["POST"])
@login_required
def add_med():
    denied = role_required("pharmacy")
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()

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
        "id": m.id, "name": m.name,
        "stock": m.stock, "price": m.price
    } for m in Medicine.query.all()])


# -------- PATIENT (self-view) --------

@app.route("/my")
@login_required
def my():
    denied = role_required("patient")
    if denied:
        return denied

    # Find the Patient record linked to the logged-in user account
    p = Patient.query.filter_by(user_id=current_user.id).first()
    if not p:
        return jsonify({"error": "No patient record found for your account"}), 404

    audit(f"PATIENT_SELF_VIEW patient_id={p.id}")
    return jsonify({
        "patient": p.name,
        "labs": [
            {"test": l.test, "result": l.result}
            for l in LabRequest.query.filter_by(patient_id=p.id).all()
        ],
        "pres": [
            {"medicine": pr.medicine, "quantity": pr.quantity}
            for pr in Prescription.query.filter_by(patient_id=p.id).all()
        ]
    })


# -------- ERROR HANDLERS --------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Access denied"}), 403

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error"}), 500


# -------- RUN --------

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
