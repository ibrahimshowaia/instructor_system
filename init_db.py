import sqlite3

# ========== AST DATABASE ==========
def create_ast_db():
    conn = sqlite3.connect('ast_database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS trainers_ast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pn TEXT NOT NULL,
            base_month TEXT NOT NULL,
            notes TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS details_ast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER,
            item TEXT,
            detail TEXT,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ========== RST DATABASE ==========
def create_rst_db():
    conn = sqlite3.connect('rst_database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS trainers_rst (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pn TEXT NOT NULL,
            base_month TEXT NOT NULL,
            notes TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS details_rst (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER,
            item TEXT,
            detail TEXT,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ========== MAIN DATABASE ==========
def create_main_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # INITIAL
    c.execute('''
        CREATE TABLE IF NOT EXISTS initial_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            course TEXT,
            date TEXT,
            verified TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS initial_signatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            designation TEXT,
            manager_name TEXT,
            manager_signature TEXT,
            manager_date TEXT,
            director_name TEXT,
            director_signature TEXT,
            director_date TEXT
        )
    ''')

    # TCFOI
    c.execute('''
        CREATE TABLE IF NOT EXISTS tcfoi_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            instructor TEXT,
            completion_date TEXT,
            designation TEXT,
            designation_date TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tcfoi_signatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            director_name TEXT,
            director_signature TEXT,
            director_date TEXT
        )
    ''')

    # RECURRENT
    c.execute('''
        CREATE TABLE IF NOT EXISTS recurrent_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            course TEXT,
            completion_date TEXT,
            verified_by TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS recurrent_signatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            manager_name TEXT,
            signature TEXT,
            date TEXT
        )
    ''')

    # ADD QUALIFICATION
    c.execute('''
        CREATE TABLE IF NOT EXISTS add_qualification_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            course TEXT,
            date TEXT,
            verified TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS add_qualification_signatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            designation TEXT,
            manager_name TEXT,
            manager_signature TEXT,
            manager_date TEXT,
            director_name TEXT,
            director_signature TEXT,
            director_date TEXT
        )
    ''')

    # EVALUATION
    c.execute('''
        CREATE TABLE IF NOT EXISTS evaluation_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            trainer_id INTEGER,
            instructor TEXT,
            course TEXT,
            observer TEXT,
            date TEXT,
            recommendations TEXT,
            comments TEXT,
            observer_signature TEXT,
            observer_signature_name TEXT,
            observer_date TEXT,
            instructor_signature TEXT,
            instructor_signature_name TEXT,
            instructor_date TEXT,
            manager_name TEXT,
            manager_signature TEXT,
            manager_date TEXT
        )
    ''')

    conn.commit()
    conn.close()

# ========== RUN ALL ==========
if __name__ == '__main__':
    create_ast_db()
    create_rst_db()
    create_main_db()
    print("✅ All databases initialized successfully.")