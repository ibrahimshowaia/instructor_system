import sqlite3

# إنشاء أو الاتصال بقاعدة البيانات
conn = sqlite3.connect("database.db")
c = conn.cursor()

# جدول المدربين
c.execute("""
CREATE TABLE IF NOT EXISTS trainers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    trainer_id TEXT NOT NULL UNIQUE,
    base_month TEXT NOT NULL,
    initial TEXT,
    recurrent TEXT,
    add_course TEXT,
    evaluate TEXT
)
""")

# تفاصيل المدرب (✅ تعديل هنا: detail بدلًا من details)
c.execute("""
CREATE TABLE IF NOT EXISTS trainer_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id TEXT NOT NULL,
    item TEXT,
    detail TEXT
)
""")

# TT/F01 - Initial Qualification
c.execute("""
CREATE TABLE IF NOT EXISTS ttfoi_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_name TEXT NOT NULL,
    trainer_id TEXT NOT NULL,
    course TEXT,
    date TEXT,
    verified TEXT
)
""")

# TC/F01 - Designation
c.execute("""
CREATE TABLE IF NOT EXISTS tcfoi_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_name TEXT NOT NULL,
    trainer_id TEXT NOT NULL,
    course TEXT,
    completion_date TEXT,
    verified_by TEXT
)
""")

# Recurrent
c.execute("""
CREATE TABLE IF NOT EXISTS recurrent_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_name TEXT NOT NULL,
    trainer_id TEXT NOT NULL,
    course TEXT,
    completion_date TEXT,
    verified_by TEXT
)
""")

# Additional Qualifications
c.execute("""
CREATE TABLE IF NOT EXISTS qualification_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id TEXT NOT NULL,
    course TEXT,
    completion_date TEXT,
    verified_by TEXT
)
""")

# Evaluation
c.execute("""
CREATE TABLE IF NOT EXISTS evaluation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id TEXT,
    trainer_name TEXT,
    evaluator TEXT,
    evaluation_date TEXT,
    rating TEXT,
    weak_reason TEXT,
    notes TEXT,
    file_name TEXT
)
""")

# Users
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    phone_number TEXT
)
""")

# تنظيف البيانات القديمة (اختياري للتطوير فقط)
c.execute("DELETE FROM trainers")
c.execute("DELETE FROM trainer_details")
c.execute("DELETE FROM ttfoi_records")
c.execute("DELETE FROM tcfoi_records")
c.execute("DELETE FROM recurrent_records")
c.execute("DELETE FROM qualification_records")
c.execute("DELETE FROM evaluation_records")
c.execute("DELETE FROM users")

# بيانات تجريبية
sample_trainers = [
    ("John Smith", "TR001", "2025-04-01", "", "", "", ""),
    ("Jane Doe", "TR002", "2025-05-15", "", "", "", ""),
    ("Ali Ahmad", "TR003", "2025-01-10", "", "", "", "")
]
c.executemany("""
    INSERT INTO trainers (name, trainer_id, base_month, initial, recurrent, add_course, evaluate)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", sample_trainers)

sample_users = [
    ("admin", "admin", "+966500000000")
]
c.executemany("""
    INSERT INTO users (username, password, phone_number)
    VALUES (?, ?, ?)
""", sample_users)

conn.commit()
conn.close()

print("✅ Database and all tables created successfully with sample data.")
