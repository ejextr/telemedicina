from flask_app import db, app, User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.drop_all()
    db.create_all()

    # Create default users
    default_users = [
        {'username': 'doc', 'password': 'doc', 'role': 'doctor', 'name': 'Doctor Default', 'specialty': 'General'},
        {'username': 'paciente', 'password': 'paciente', 'role': 'patient', 'name': 'Paciente Default'},
        {'username': 'admin', 'password': 'admin', 'role': 'admin', 'name': 'Admin'}
    ]

    for user_data in default_users:
        hashed_password = generate_password_hash(user_data['password'], method='pbkdf2:sha256')
        user = User(
            username=user_data['username'],
            password=hashed_password,
            role=user_data['role'],
            name=user_data['name'],
            specialty=user_data.get('specialty')
        )
        db.session.add(user)

    db.session.commit()
    print("Database reset completed. All tables recreated with current schema and default users added.")