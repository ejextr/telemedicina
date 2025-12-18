from flask_app import app, db
from werkzeug.security import generate_password_hash
from sqlalchemy import text

with app.app_context():
    db.create_all()

    # Migraciones simples: agregar columnas si no existen
    engine = db.engine

    # Verificar y agregar on_shift a user
    result = engine.execute(text("PRAGMA table_info(user)"))
    columns = [row[1] for row in result]
    if 'on_shift' not in columns:
        engine.execute(text("ALTER TABLE user ADD COLUMN on_shift BOOLEAN DEFAULT 0"))
        print("Added on_shift column to user table")

    # Crear usuario admin por defecto si no existe
    from flask_app import User
    if not User.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
        admin_user = User(username='admin', password=hashed_password, role='doctor', specialty='General', on_shift=False)
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: username='admin', password='admin'")
    print("Database initialized and migrated")