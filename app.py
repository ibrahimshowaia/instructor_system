from flask import Flask, render_template,  request, redirect, url_for, session, flash, send_file
import sqlite3, os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from io import BytesIO

app = Flask(__name__)
app.secret_key = "your_secret_key"

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

USERS = {
    "AST": {"username": "ast", "password": "ast123"},
    "AMT": {"username": "amt", "password": "amt123"},
    "RST": {"username": "rst", "password": "rst123"}
}

# ------------------------- AUTH -------------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        dept = request.form.get("department", "").upper()
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        creds = USERS.get(dept)
        if creds and creds["username"] == username and creds["password"] == password:
            session["logged_in"] = True
            session["department"] = dept
            return redirect(url_for("dashboard"))
        flash("Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ---------------------- DASHBOARD -----------------------
@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    # اتصال بقاعدة البيانات
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # جلب جميع المدربين
    cur.execute("SELECT * FROM trainers")
    trainers = cur.fetchall()

    # إعداد البيانات ومعالجة التاريخ
    current_date = datetime.today().date()
    alert_messages = []
    updated_trainers = []

    for trainer in trainers:
        try:
            base_date = datetime.strptime(trainer['base_month'], '%Y-%m-%d').date()
        except:
            base_date = current_date

        # حساب الفرق
        days_remaining = (base_date - current_date).days

        # تنبيه إذا اقترب الانتهاء (60 يوم)
        if 0 <= days_remaining <= 60:
            alert_messages.append(f"⚠️ Trainer {trainer['name']}'s qualification expires in {days_remaining} days!")
        # تنبيه إذا انتهت الصلاحية
        elif days_remaining < 0:
            alert_messages.append(f"❌ Trainer {trainer['name']}'s qualification expired {-days_remaining} days ago!")

        # إضافة التاريخ المعالج والفرق
        trainer_dict = dict(trainer)
        trainer_dict['base_month'] = base_date
        trainer_dict['days_remaining'] = days_remaining
        updated_trainers.append(trainer_dict)

    # ترتيب حسب الأقرب للانتهاء
    updated_trainers.sort(key=lambda t: t['days_remaining'])

    # البحث إذا وُجد
    search_query = request.args.get('search', '').lower()
    if search_query:
        updated_trainers = [
            t for t in updated_trainers
            if search_query in t['name'].lower() or search_query in t['trainer_id'].lower()
        ]

    return render_template('ast/dashboard.html',
                           trainers=updated_trainers,
                           current_date=current_date,
                           alerts=alert_messages,
                           search_query=search_query)

# ---------------------- ADD TRAINER ---------------------
@app.route("/add_trainer", methods=["GET", "POST"])
def add_trainer():
    if request.method == "POST":
        name = request.form.get("name")
        trainer_id = request.form.get("trainer_id")
        base_month = request.form.get("base_month")
        try:
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("INSERT INTO trainers (name, trainer_id, base_month) VALUES (?, ?, ?)",
                      (name, trainer_id, base_month))
            conn.commit()
            conn.close()
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash(f"Error saving data: {e}", "danger")
            return redirect(url_for("add_trainer"))
    return render_template("ast/add_trainer.html")

# ------------------- TRAINER DETAILS --------------------
@app.route("/trainer/<trainer_id>", methods=["GET", "POST"])
def trainer_detail(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == "POST":
        items = request.form.getlist("item[]")
        details = request.form.getlist("details[]")
        c.execute("DELETE FROM trainer_details WHERE trainer_id = ?", (trainer_id,))
        for item, detail in zip(items, details):
            c.execute("INSERT INTO trainer_details (trainer_id, item, details) VALUES (?, ?, ?)",
                      (trainer_id, item, detail))
        conn.commit()
    trainer = c.execute("SELECT * FROM trainers WHERE trainer_id = ?", (trainer_id,)).fetchone()
    records = c.execute("SELECT item, details FROM trainer_details WHERE trainer_id = ?", (trainer_id,)).fetchall()
    conn.close()
    return render_template("ast/trainer_detail.html", trainer=trainer, records=records)

# ---------------------- INITIAL -------------------------
@app.route("/initial/<int:trainer_id>", methods=["GET", "POST"])
def initial_page(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    trainer_name = trainer["name"]
    trainer_code = trainer["trainer_id"]

    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("date[]")
        verified = request.form.getlist("verified[]")

        c.execute("DELETE FROM ttfoi_records WHERE trainer_id = ?", (trainer_code,))
        for course, date, ver in zip(courses, dates, verified):
            c.execute("""INSERT INTO ttfoi_records (trainer_name, trainer_id, course, date, verified)
                         VALUES (?, ?, ?, ?, ?)""", (trainer_name, trainer_code, course, date, ver))

        conn.commit()
        conn.close()
        flash("✅ Initial records saved.")
        return redirect(url_for("tcfoi_page", trainer_id=trainer_id))

    # ✅ هذا الجزء هو اللي يضمن الطباعة بشكل سليم
    records = c.execute("SELECT * FROM ttfoi_records WHERE trainer_id = ?", (trainer_code,)).fetchall()
    current_date = datetime.today().strftime("%Y-%m-%d")
    conn.close()
    return render_template("ast/initial.html", trainer=trainer, trainer_id=trainer_id, records=records, current_date=current_date)

# ------------------------ TCFOI --------------------------
@app.route("/tcfoi/<int:trainer_id>", methods=["GET", "POST"])
def tcfoi_page(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()

    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("completion_date[]")
        verified_by = request.form.getlist("verified_by[]")

        trainer_name = trainer["name"]
        trainer_code = trainer["trainer_id"]

        c.execute("DELETE FROM tcfoi_records WHERE trainer_id = ?", (trainer_code,))
        for course, date, verified in zip(courses, dates, verified_by):
            c.execute("""INSERT INTO tcfoi_records (trainer_id, trainer_name, course, completion_date, verified_by)
                         VALUES (?, ?, ?, ?, ?)""", (trainer_code, trainer_name, course, date, verified))

        conn.commit()
        conn.close()
        flash("✅ TCFOI updated.")
        return redirect(url_for("tcfoi_page", trainer_id=trainer_id))

    current_date = datetime.today().strftime("%Y-%m-%d")
    records = c.execute("SELECT * FROM tcfoi_records WHERE trainer_id = ?", (trainer["trainer_id"],)).fetchall()
    conn.close()
    return render_template("ast/tcfoi.html", trainer=trainer, records=records, current_date=current_date)

# --------------------- RECURRENT ------------------------
@app.route("/recurrent/<int:trainer_id>", methods=["GET", "POST"])
def recurrent_page(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    trainer_code = trainer["trainer_id"]

    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("completion_date[]")
        verified_by = request.form.getlist("verified_by[]")

        c.execute("DELETE FROM recurrent_records WHERE trainer_id = ?", (trainer_code,))
        for course, date, verified in zip(courses, dates, verified_by):
            c.execute("""INSERT INTO recurrent_records (trainer_id, trainer_name, course, completion_date, verified_by)
                         VALUES (?, ?, ?, ?, ?)""", (trainer_code, trainer["name"], course, date, verified))

        conn.commit()
        conn.close()
        flash("✅ Recurrent records saved.")
        return redirect(url_for("trainer_detail", trainer_id=trainer_code))

    records = c.execute("SELECT * FROM recurrent_records WHERE trainer_id = ?", (trainer_code,)).fetchall()
    current_date = datetime.today().strftime("%Y-%m-%d")
    conn.close()
    return render_template("ast/recurrent.html", trainer_name=trainer["name"], trainer_id=trainer_code,
                           date=current_date, trainer_id_value=trainer_id, records=records)

# ------------------ ADD QUALIFICATION -------------------
@app.route("/add_qualification/<int:trainer_id>", methods=["GET", "POST"])
def add_qualification(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    trainer_code = trainer["trainer_id"]

    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("date[]")
        verified_by = request.form.getlist("verified[]")

        c.execute("DELETE FROM qualification_records WHERE trainer_id = ?", (trainer_code,))
        for course, date, verified in zip(courses, dates, verified_by):
            c.execute("""INSERT INTO qualification_records (trainer_id, course, completion_date, verified_by)
                         VALUES (?, ?, ?, ?)""", (trainer_code, course, date, verified))

        conn.commit()
        conn.close()
        flash("✅ Qualification saved.")
        return redirect(url_for("trainer_detail", trainer_id=trainer_code))

    records = c.execute("SELECT * FROM qualification_records WHERE trainer_id = ?", (trainer_code,)).fetchall()
    conn.close()
    return render_template("ast/add_qualification.html", trainer=trainer, trainer_id=trainer_id, records=records)

# ---------------------- EVALUATION ----------------------
@app.route("/evaluation/<int:trainer_id>", methods=["GET", "POST"])
def evaluation(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    trainer_code = trainer["trainer_id"]

    if request.method == "POST":
        evaluator = request.form.get("evaluator")
        evaluation_date = request.form.get("evaluation_date")
        rating = request.form.get("rating")
        weak_reason = request.form.get("weak_reason")
        notes = request.form.get("notes")
        file = request.files.get("file")
        filename = None
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        c.execute("""INSERT INTO evaluation_records
                     (trainer_id, trainer_name, evaluator, evaluation_date, rating, weak_reason, notes, file_name)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (trainer_code, trainer["name"], evaluator, evaluation_date, rating, weak_reason, notes, filename))
        conn.commit()
        conn.close()
        flash("✅ Evaluation saved.")
        return redirect(url_for("trainer_detail", trainer_id=trainer_code))

    conn.close()
    return render_template("ast/evaluation.html", trainer=trainer)

# ------------------- DOWNLOAD TRAINERS -------------------
@app.route("/download_trainers_excel")
def download_trainers_excel():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT name, trainer_id, base_month FROM trainers")
    data = c.fetchall()
    conn.close()

    import csv
    from io import StringIO, BytesIO
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Name", "Trainer ID", "Base Month"])
    cw.writerows(data)

    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="trainers.csv")

if __name__ == "__main__":
    app.run(debug=True)
