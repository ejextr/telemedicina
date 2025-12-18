from flask_app import app, db
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    # Crear usuario admin por defecto si no existe
    from flask_app import User
    if not User.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
        admin_user = User(username='admin', password=hashed_password, role='doctor', specialty='General', on_shift=False)
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: username='admin', password='admin'")
    print("Database initialized")