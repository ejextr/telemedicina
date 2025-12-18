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

    # Crear usuario admin por defecto
    from flask_app import User
    hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
    admin_user = User(username='admin', password=hashed_password, role='doctor', specialty='General', on_shift=False)
    db.session.add(admin_user)
    db.session.commit()
    print("Admin user created: username='admin', password='admin'")
    print("Database initialized")