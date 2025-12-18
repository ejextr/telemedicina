from flask_app import app, db
from werkzeug.security import generate_password_hash
from sqlalchemy import text
import os

with app.app_context():
    # Si la base de datos existe, eliminarla para recrear con el esquema actualizado
    db_path = 'medicapp.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed old database")

    db.create_all()

    # Crear usuarios por defecto
    from flask_app import User
    users = [
        {'username': 'admin', 'password': 'admin', 'role': 'doctor', 'specialty': 'General', 'on_shift': False},
        {'username': 'doc', 'password': 'doc', 'role': 'doctor', 'specialty': 'Cardiología', 'on_shift': True},
        {'username': 'paciente', 'password': 'paciente', 'role': 'patient', 'specialty': None, 'on_shift': False}
    ]
    for user_data in users:
        hashed_password = generate_password_hash(user_data['password'], method='pbkdf2:sha256')
        user = User(
            username=user_data['username'],
            password=hashed_password,
            role=user_data['role'],
            specialty=user_data['specialty'],
            on_shift=user_data['on_shift']
        )
        db.session.add(user)
    db.session.commit()
    print("Default users created:")
    for u in users:
        print(f"  - {u['username']} (password: {u['password']}, role: {u['role']})")
    print("Database initialized")