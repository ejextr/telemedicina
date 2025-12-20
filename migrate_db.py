from flask_app import db, app

with app.app_context():
    # Add read column to message table if not exists
    try:
        db.engine.execute(db.text("ALTER TABLE message ADD COLUMN read BOOLEAN DEFAULT 0"))
        print("Added 'read' column to message table")
    except Exception as e:
        print(f"Column 'read' might already exist: {e}")

    # Add feedback_submitted column to waiting_room table if not exists
    try:
        db.engine.execute(db.text("ALTER TABLE waiting_room ADD COLUMN feedback_submitted BOOLEAN DEFAULT 0"))
        print("Added 'feedback_submitted' column to waiting_room table")
    except Exception as e:
        print(f"Column 'feedback_submitted' might already exist: {e}")

print("Migration completed")