from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medicapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'doctor' or 'patient'
    specialty = db.Column(db.String(100), nullable=True)  # Only for doctors
    on_shift = db.Column(db.Boolean, default=False)  # For doctors

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    medical_history = db.Column(db.Text, nullable=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    patient = db.relationship('Patient', backref=db.backref('appointments', lazy=True))
    doctor = db.relationship('User', backref=db.backref('appointments', lazy=True))

class WaitingRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    patient = db.relationship('Patient', backref=db.backref('waiting_rooms', lazy=True))
    doctor = db.relationship('User', backref=db.backref('waiting_rooms', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        specialty = request.form.get('specialty') if role == 'doctor' else None
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, role=role, specialty=specialty)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful, please login')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'doctor':
        return render_template('doctor_dashboard.html')
    return render_template('dashboard.html')

@app.route('/patients')
@login_required
def patients():
    patients = Patient.query.all()
    return render_template('patients.html', patients=patients)

@app.route('/appointments')
@login_required
def appointments():
    appointments = Appointment.query.all()
    return render_template('appointments.html', appointments=appointments)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        return jsonify({'message': 'Login successful'})
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/patients', methods=['GET'])
@login_required
def api_patients():
    patients = Patient.query.all()
@app.route('/toggle_shift', methods=['POST'])
@login_required
def toggle_shift():
    if current_user.role != 'doctor':
        return jsonify({'error': 'Not a doctor'}), 403
    current_user.on_shift = not current_user.on_shift
    db.session.commit()
    return jsonify({'on_shift': current_user.on_shift})

@app.route('/guardias')
@login_required
def guardias():
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    doctors_on_shift = User.query.filter_by(role='doctor', on_shift=True).all()
    return render_template('guardias.html', doctors=doctors_on_shift)

@app.route('/enter_waiting_room/<int:doctor_id>', methods=['POST'])
@login_required
def enter_waiting_room(doctor_id):
    if current_user.role != 'patient':
        return jsonify({'error': 'Not a patient'}), 403
    symptoms = request.form.get('symptoms')
    if not symptoms:
        return jsonify({'error': 'Symptoms required'}), 400
    waiting = WaitingRoom(patient_id=current_user.id, doctor_id=doctor_id, symptoms=symptoms)
    db.session.add(waiting)
    db.session.commit()
    doctor = User.query.get(doctor_id)
    return jsonify({'message': f'Se ha solicitado entrar a la sala de espera del doctor {doctor.username}'})

@app.route('/waiting_requests')
@login_required
def waiting_requests():
    if current_user.role != 'doctor':
        return redirect(url_for('dashboard'))
    requests = WaitingRoom.query.filter_by(doctor_id=current_user.id, status='pending').all()
    return render_template('waiting_requests.html', requests=requests)

@app.route('/accept_waiting/<int:id>', methods=['POST'])
@login_required
def accept_waiting(id):
    if current_user.role != 'doctor':
        return jsonify({'error': 'Not a doctor'}), 403
    waiting = WaitingRoom.query.get(id)
    if waiting and waiting.doctor_id == current_user.id:
        waiting.status = 'accepted'
        db.session.commit()
    return redirect(url_for('waiting_requests'))

@app.route('/reject_waiting/<int:id>', methods=['POST'])
@login_required
def reject_waiting(id):
    if current_user.role != 'doctor':
        return jsonify({'error': 'Not a doctor'}), 403
    waiting = WaitingRoom.query.get(id)
    if waiting and waiting.doctor_id == current_user.id:
        waiting.status = 'rejected'
        db.session.commit()
    return redirect(url_for('waiting_requests'))

@app.route('/api/appointments', methods=['GET'])
@login_required
def api_appointments():
    appointments = Appointment.query.all()
    return jsonify([{'id': a.id, 'patient_name': a.patient.name, 'doctor_name': a.doctor.username, 'date': a.date.isoformat(), 'reason': a.reason} for a in appointments])
    appointments = Appointment.query.all()
    return jsonify([{'id': a.id, 'patient_name': a.patient.name, 'doctor_name': a.doctor.username, 'date': a.date.isoformat(), 'reason': a.reason} for a in appointments])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)