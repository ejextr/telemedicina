from flask_app import db, app

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database reset completed. All tables recreated with current schema.")