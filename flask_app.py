from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
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
    name = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)
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
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, in_room, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    queue_order = db.Column(db.Integer, default=0)  # For ordering pending requests
    feedback_submitted = db.Column(db.Boolean, default=False)
    chat_enabled = db.Column(db.Boolean, default=False)
    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('patient_waiting_rooms', lazy=True))
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref=db.backref('doctor_waiting_rooms', lazy=True))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy=True))

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref=db.backref('given_feedbacks', lazy=True))
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref=db.backref('received_feedbacks', lazy=True))

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
        name = request.form.get('name')
        description = request.form.get('description')
        role = request.form.get('role')
        specialty = request.form.get('specialty') if role == 'doctor' else None
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, role=role, name=name, description=description, specialty=specialty)
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
    doctors = []
    for doctor in User.query.filter_by(role='doctor', on_shift=True):
        avg_rating = db.session.query(func.avg(Feedback.rating)).filter(Feedback.to_user_id == doctor.id).scalar() or 0
        doctor.avg_rating = round(avg_rating, 1) if avg_rating else 0
        doctors.append(doctor)
    # Check if patient is in any waiting room
    current_waiting = WaitingRoom.query.filter_by(patient_id=current_user.id, status='pending').first()
    position = None
    if current_waiting:
        # Count how many pending requests have lower queue_order for the same doctor
        position = WaitingRoom.query.filter(
            WaitingRoom.doctor_id == current_waiting.doctor_id,
            WaitingRoom.status == 'pending',
            WaitingRoom.queue_order <= current_waiting.queue_order
        ).count()
    return render_template('guardias.html', doctors=doctors, current_waiting=current_waiting, position=position)

@app.route('/enter_waiting_room/<int:doctor_id>', methods=['POST'])
@login_required
def enter_waiting_room(doctor_id):
    if current_user.role != 'patient':
        return jsonify({'error': 'Not a patient'}), 403
    symptoms = request.form.get('symptoms')
    if not symptoms:
        return jsonify({'error': 'Symptoms required'}), 400
    # Get the next queue order
    max_order = db.session.query(func.max(WaitingRoom.queue_order)).filter_by(doctor_id=doctor_id, status='pending').scalar() or 0
    waiting = WaitingRoom(patient_id=current_user.id, doctor_id=doctor_id, symptoms=symptoms, queue_order=max_order + 1)
    db.session.add(waiting)
    db.session.commit()
    doctor = User.query.get(doctor_id)
    return jsonify({'message': f'Se ha solicitado entrar a la sala de espera del doctor {doctor.username}'})

@app.route('/waiting_requests')
@login_required
def waiting_requests():
    if current_user.role != 'doctor':
        return redirect(url_for('dashboard'))
    now = datetime.utcnow()
    yesterday = now - timedelta(hours=24)
    active_requests = WaitingRoom.query.filter(WaitingRoom.doctor_id == current_user.id, WaitingRoom.status.in_(['pending', 'accepted', 'in_room'])).order_by(WaitingRoom.queue_order).all()
    today_consultations = WaitingRoom.query.filter(WaitingRoom.doctor_id == current_user.id, WaitingRoom.status == 'completed', WaitingRoom.end_time >= yesterday).order_by(WaitingRoom.end_time.desc()).all()
    history_consultations = WaitingRoom.query.filter(WaitingRoom.doctor_id == current_user.id, WaitingRoom.status == 'completed', WaitingRoom.end_time < yesterday).order_by(WaitingRoom.end_time.desc()).all()
    return render_template('waiting_requests.html', active_requests=active_requests, today_consultations=today_consultations, history_consultations=history_consultations)

@app.route('/accept_waiting/<int:id>', methods=['POST'])
@login_required
def accept_waiting(id):
    if current_user.role != 'doctor':
        return jsonify({'error': 'Not a doctor'}), 403
    waiting = WaitingRoom.query.get(id)
    if waiting and waiting.doctor_id == current_user.id:
        try:
            # Assign queue order for accepted requests
            max_order = db.session.query(func.max(WaitingRoom.queue_order)).filter(WaitingRoom.doctor_id == current_user.id, WaitingRoom.status.in_(['accepted', 'in_room'])).scalar() or 0
            waiting.queue_order = max_order + 1
            waiting.status = 'accepted'
            db.session.commit()
            # Send notification message to patient
            message = Message(sender_id=current_user.id, receiver_id=waiting.patient_id, content=f"Tu solicitud ha sido aceptada por el doctor {current_user.name or current_user.username}.")
            db.session.add(message)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Error al aceptar la solicitud.', 'error')
            return redirect(url_for('waiting_requests'))
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
        # Send notification message to patient
        message = Message(sender_id=current_user.id, receiver_id=waiting.patient_id, content=f"Tu solicitud ha sido rechazada por el doctor {current_user.name or current_user.username}.")
        db.session.add(message)
        db.session.commit()
    return redirect(url_for('waiting_requests'))

@app.route('/enable_chat/<int:id>', methods=['POST'])
@login_required
def enable_chat(id):
    if current_user.role != 'doctor':
        return jsonify({'error': 'Not a doctor'}), 403
    waiting = WaitingRoom.query.get(id)
    if waiting and waiting.doctor_id == current_user.id:
        waiting.chat_enabled = True
        db.session.commit()
    return redirect(url_for('waiting_requests'))

@app.route('/messages')
@login_required
def messages():
    if current_user.role == 'patient':
        # Find if patient has chat enabled with a doctor
        waiting = WaitingRoom.query.filter_by(patient_id=current_user.id, chat_enabled=True).first()
        if waiting:
            return redirect(url_for('chat', user_id=waiting.doctor_id))
    elif current_user.role == 'doctor':
        # Show list of patients with chat enabled
        waitings = WaitingRoom.query.filter_by(doctor_id=current_user.id, chat_enabled=True).all()
        return render_template('messages.html', waitings=waitings)
    return render_template('messages.html', waitings=[])

@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    other_user = User.query.get(user_id)
    if not other_user:
        return redirect(url_for('messages'))
    # Check if allowed to chat
    if current_user.role == 'patient':
        waiting = WaitingRoom.query.filter_by(patient_id=current_user.id, doctor_id=user_id, chat_enabled=True).first()
        if not waiting:
            return redirect(url_for('messages'))
    elif current_user.role == 'doctor':
        waiting = WaitingRoom.query.filter_by(doctor_id=current_user.id, patient_id=user_id, chat_enabled=True).first()
        if not waiting:
            return redirect(url_for('messages'))
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()
    room_name = f"medicapp-{min(current_user.id, user_id)}-{max(current_user.id, user_id)}"
    recent_call = any(m.content.startswith("Videollamada") and (datetime.utcnow() - m.timestamp) < timedelta(hours=1) for m in messages)
    waiting_id = waiting.id if waiting else None
    return render_template('chat.html', other_user=other_user, messages=messages, room_name=room_name, show_feedback=recent_call, waiting_id=waiting_id)

@app.route('/send_message/<int:user_id>', methods=['POST'])
@login_required
def send_message(user_id):
    content = request.form.get('content')
    if content:
        message = Message(sender_id=current_user.id, receiver_id=user_id, content=content)
        db.session.add(message)
        db.session.commit()
    return redirect(url_for('chat', user_id=user_id))

@app.route('/start_video_call/<int:user_id>', methods=['POST'])
@login_required
def start_video_call(user_id):
    if current_user.role != 'doctor':
        return redirect(url_for('dashboard'))
    # Update waiting room status to in_room
    waiting = WaitingRoom.query.filter_by(doctor_id=current_user.id, patient_id=user_id, status='accepted').first()
    if waiting:
        waiting.status = 'in_room'
    room_name = f"medicapp-{min(current_user.id, user_id)}-{max(current_user.id, user_id)}"
    message_content = f"Videollamada iniciada. Unirse: https://meet.jit.si/{room_name}"
    message = Message(sender_id=current_user.id, receiver_id=user_id, content=message_content)
    db.session.add(message)
    db.session.commit()
    # Redirect to the room for the doctor
    return redirect(f"https://meet.jit.si/{room_name}")

@app.route('/complete_call/<int:waiting_id>', methods=['POST'])
@login_required
def complete_call(waiting_id):
    waiting = WaitingRoom.query.get(waiting_id)
    if waiting and waiting.patient_id == current_user.id and waiting.status == 'in_room':
        waiting.status = 'completed'
        waiting.end_time = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('feedback_form', waiting_id=waiting_id))
    return '', 204

@app.route('/feedback/<int:waiting_id>')
@login_required
def feedback_form(waiting_id):
    waiting = WaitingRoom.query.get(waiting_id)
    if not waiting or waiting.patient_id != current_user.id or waiting.status != 'completed':
        flash('No tienes permiso para acceder a esta página')
        return redirect(url_for('dashboard'))
    if waiting.feedback_submitted:
        flash('Ya has enviado feedback para esta consulta')
        return redirect(url_for('dashboard'))
    return render_template('feedback.html', waiting=waiting)

@app.route('/submit_feedback/<int:waiting_id>', methods=['POST'])
@login_required
def submit_feedback(waiting_id):
    waiting = WaitingRoom.query.get(waiting_id)
    if not waiting or waiting.patient_id != current_user.id or waiting.status != 'completed' or waiting.feedback_submitted:
        flash('No puedes enviar feedback')
        return redirect(url_for('dashboard'))
    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment')
    if rating and 1 <= rating <= 5:
        feedback = Feedback(from_user_id=current_user.id, to_user_id=waiting.doctor_id, rating=rating, comment=comment)
        db.session.add(feedback)
        waiting.feedback_submitted = True
        db.session.commit()
        flash('Feedback enviado correctamente')
    else:
        flash('Rating inválido')
    return redirect(url_for('dashboard'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.description = request.form.get('description')
        if current_user.role == 'doctor':
            current_user.specialty = request.form.get('specialty')
        new_password = request.form.get('password')
        if new_password:
            current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        flash('Perfil actualizado.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')

@app.route('/update_queue_order', methods=['POST'])
@login_required
def update_queue_order():
    if current_user.role != 'doctor':
        return jsonify({'error': 'Not authorized'}), 403
    data = request.get_json()
    order_ids = data.get('order', [])
    for index, waiting_id in enumerate(order_ids):
        waiting = WaitingRoom.query.get(waiting_id)
        if waiting and waiting.doctor_id == current_user.id and waiting.status == 'pending':
            waiting.queue_order = index + 1
    db.session.commit()
    return jsonify({'success': True})

@app.route('/move_up/<int:id>', methods=['POST'])
@login_required
def move_up(id):
    if current_user.role != 'doctor':
        return jsonify({'error': 'Not authorized'}), 403
    waiting = WaitingRoom.query.get(id)
    if not waiting or waiting.doctor_id != current_user.id or waiting.status not in ['accepted', 'in_room']:
        return jsonify({'error': 'Invalid request'}), 400
    prev = WaitingRoom.query.filter(WaitingRoom.doctor_id == current_user.id, WaitingRoom.status.in_(['accepted', 'in_room']), WaitingRoom.queue_order < waiting.queue_order).order_by(WaitingRoom.queue_order.desc()).first()
    if prev:
        temp = waiting.queue_order
        waiting.queue_order = prev.queue_order
        prev.queue_order = temp
        db.session.commit()
    return jsonify({'success': True})

@app.route('/move_down/<int:id>', methods=['POST'])
@login_required
def move_down(id):
    if current_user.role != 'doctor':
        return jsonify({'error': 'Not authorized'}), 403
    waiting = WaitingRoom.query.get(id)
    if not waiting or waiting.doctor_id != current_user.id or waiting.status not in ['accepted', 'in_room']:
        return jsonify({'error': 'Invalid request'}), 400
    next_ = WaitingRoom.query.filter(WaitingRoom.doctor_id == current_user.id, WaitingRoom.status.in_(['accepted', 'in_room']), WaitingRoom.queue_order > waiting.queue_order).order_by(WaitingRoom.queue_order).first()
    if next_:
        temp = waiting.queue_order
        waiting.queue_order = next_.queue_order
        next_.queue_order = temp
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/queue_position')
@login_required
def api_queue_position():
    if current_user.role != 'patient':
        return jsonify({'position': None})
    pending = WaitingRoom.query.filter_by(patient_id=current_user.id, status='pending').order_by(WaitingRoom.queue_order).first()
    if not pending:
        return jsonify({'position': None})
    position = db.session.query(func.count(WaitingRoom.id)).filter(
        WaitingRoom.doctor_id == pending.doctor_id,
        WaitingRoom.status == 'pending',
        WaitingRoom.queue_order < pending.queue_order
    ).scalar() + 1
    return jsonify({'position': position})

@app.route('/api/active_consultations')
@login_required
def api_active_consultations():
    if current_user.role == 'doctor':
        waitings = WaitingRoom.query.filter_by(doctor_id=current_user.id).filter(WaitingRoom.status.in_(['accepted', 'in_room'])).order_by(WaitingRoom.queue_order).all()
    else:
        waitings = WaitingRoom.query.filter_by(patient_id=current_user.id).filter(WaitingRoom.status.in_(['accepted', 'in_room'])).all()
    data = []
    for w in waitings:
        data.append({
            'id': w.id,
            'other_user_id': w.patient_id if current_user.role == 'doctor' else w.doctor_id,
            'status': w.status,
            'queue_order': w.queue_order if hasattr(w, 'queue_order') else 0
        })
    return jsonify(data)

@app.route('/api/waiting_requests')
@login_required
def api_waiting_requests():
    if current_user.role != 'doctor':
        return jsonify([])
    pending = WaitingRoom.query.filter_by(doctor_id=current_user.id, status='pending').order_by(WaitingRoom.queue_order).all()
    accepted = WaitingRoom.query.filter_by(doctor_id=current_user.id).filter(WaitingRoom.status.in_(['accepted', 'in_room'])).order_by(WaitingRoom.queue_order).all()
    return jsonify({
        'pending': [{'id': w.id, 'patient_name': w.patient.name or w.patient.username, 'symptoms': w.symptoms} for w in pending],
        'accepted': [{'id': w.id, 'patient_name': w.patient.name or w.patient.username, 'status': w.status} for w in accepted]
    })

@app.route('/api/chat_messages/<int:user_id>')
@login_required
def api_chat_messages(user_id):
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    # Mark messages from user_id as read
    for m in messages:
        if m.sender_id == user_id and m.receiver_id == current_user.id:
            m.read = True
    db.session.commit()
    return jsonify([{
        'id': m.id,
        'sender_id': m.sender_id,
        'content': m.content,
        'timestamp': m.timestamp.strftime('%H:%M')
    } for m in messages])

@app.route('/api/unread_count')
@login_required
def api_unread_count():
    count = Message.query.filter_by(receiver_id=current_user.id, read=False).count()
    return jsonify({'unread': count})

@app.route('/api/latest_unread_message')
@login_required
def api_latest_unread_message():
    message = Message.query.filter_by(receiver_id=current_user.id, read=False).order_by(Message.timestamp.desc()).first()
    if message:
        return jsonify({'message': {'content': message.content, 'sender': message.sender.username}})
    return jsonify({'message': None})

@app.route('/migrate_db')
def migrate_db():
    try:
        db.session.execute(db.text('ALTER TABLE waiting_room ADD COLUMN feedback_submitted BOOLEAN DEFAULT 0'))
        db.session.commit()
        return 'Migration completed'
    except Exception as e:
        return f'Error: {e}'

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
        # Add missing columns if needed
        try:
            db.session.execute(db.text('ALTER TABLE waiting_room ADD COLUMN feedback_submitted BOOLEAN DEFAULT 0'))
            db.session.commit()
        except:
            pass  # Column already exists
    app.run(debug=True)