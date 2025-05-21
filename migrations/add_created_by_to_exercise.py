import sys
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'db.sqlite')

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Créer une nouvelle table temporaire avec la nouvelle structure
        cursor.execute("""
        CREATE TABLE exercise_new (
            id INTEGER PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            exercise_type VARCHAR(50) NOT NULL,
            content TEXT,
            image_path VARCHAR(200),
            teacher_id INTEGER NOT NULL,
            created_at DATETIME,
            max_attempts INTEGER DEFAULT 3,
            created_by INTEGER NOT NULL,
            FOREIGN KEY(teacher_id) REFERENCES user(id),
            FOREIGN KEY(created_by) REFERENCES user(id)
        )
        """)
        
        # Copier les données de l'ancienne table vers la nouvelle
        cursor.execute("""
        INSERT INTO exercise_new (id, title, description, exercise_type, content, 
                                image_path, teacher_id, created_at, max_attempts, created_by)
        SELECT id, title, description, exercise_type, content, 
               image_path, teacher_id, created_at, max_attempts, teacher_id
        FROM exercise
        """)
        
        # Supprimer l'ancienne table
        cursor.execute('DROP TABLE exercise')
        
        # Renommer la nouvelle table
        cursor.execute('ALTER TABLE exercise_new RENAME TO exercise')
        
        conn.commit()
        print('Migration successful!')
        
    except Exception as e:
        conn.rollback()
        print(f'Error during migration: {e}')
        raise
    finally:
        conn.close()

def downgrade():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE exercise DROP COLUMN created_by')
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    upgrade()
