from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
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
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("home"))
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, name, trainer_id, base_month FROM trainers")
    trainers = c.fetchall()
    conn.close()

    alerts = []
    today = datetime.today().date()
    for trainer in trainers:
        try:
            base_date = datetime.strptime(trainer["base_month"], "%Y-%m-%d").date()
            expiry_date = base_date + timedelta(days=365)
            remaining = (expiry_date - today).days
            if remaining <= 60:
                alerts.append(f"⚠ Trainer {trainer['name']}'s qualification expires in {remaining} days!")
        except:
            continue
    return render_template("ast/dashboard.html", trainers=trainers, alerts=alerts)

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

    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("date[]")
        verified_by = request.form.getlist("verified[]")

        # ✅ اجلب اسم المدرب
        trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
        trainer_name = trainer["name"]

        # ✅ احذف السجلات القديمة وأضف الجديدة
        c.execute("DELETE FROM ttfoi_records WHERE trainer_id = ?", (trainer_id,))
        for course, date, verified in zip(courses, dates, verified_by):
            c.execute("""INSERT INTO ttfoi_records (trainer_name, trainer_id, course, date, verified)
                         VALUES (?, ?, ?, ?, ?)""", (trainer_name, trainer_id, course, date, verified))

        conn.commit()
        conn.close()
        return redirect(url_for("tcfoi_page", trainer_id=trainer_id))

    # ✅ جزء عرض الصفحة
    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    records = c.execute("SELECT * FROM ttfoi_records WHERE trainer_id = ?", (trainer_id,)).fetchall()
    current_date = datetime.today().strftime("%Y-%m-%d")
    return render_template("ast/initial.html", trainer=trainer, records=records, current_date=current_date)

# ------------------------ TCFOI --------------------------
@app.route("/tcfoi/<int:trainer_id>", methods=["GET", "POST"])
def tcfoi_page(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("completion_date[]")
        verified_by = request.form.getlist("verified_by[]")
        c.execute("DELETE FROM tcfoi_records WHERE trainer_id = ?", (trainer_id,))
        for course, date, verified in zip(courses, dates, verified_by):
            c.execute("""INSERT INTO tcfoi_records (trainer_id, course, completion_date, verified_by)
                         VALUES (?, ?, ?, ?)""", (trainer_id, course, date, verified))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    current_date = datetime.today().strftime("%Y-%m-%d")
    return render_template("ast/tcfoi.html", trainer=trainer, current_date=current_date)

# --------------------- RECURRENT ------------------------
@app.route("/recurrent/<int:trainer_id>", methods=["GET", "POST"])
def recurrent_page(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("completion_date[]")
        verified_by = request.form.getlist("verified_by[]")
        c.execute("DELETE FROM recurrent_records WHERE trainer_id = ?", (trainer_id,))
        for course, date, verified in zip(courses, dates, verified_by):
            c.execute("""INSERT INTO recurrent_records (trainer_id, course, completion_date, verified_by)
                         VALUES (?, ?, ?, ?)""", (trainer_id, course, date, verified))
        conn.commit()
    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    records = c.execute("SELECT * FROM recurrent_records WHERE trainer_id = ?", (trainer_id,)).fetchall()
    current_date = datetime.today().strftime("%Y-%m-%d")
    return render_template("ast/recurrent.html", trainer_name=trainer["name"], trainer_id=trainer["trainer_id"],
                           date=current_date, trainer_id_value=trainer_id, records=records)

# ------------------ ADD QUALIFICATION -------------------
@app.route("/add_qualification/<int:trainer_id>", methods=["GET", "POST"])
def add_qualification(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("date[]")
        verified_by = request.form.getlist("verified[]")
        c.execute("DELETE FROM qualification_records WHERE trainer_id = ?", (trainer_id,))
        for course, date, verified in zip(courses, dates, verified_by):
            c.execute("""INSERT INTO qualification_records (trainer_id, course, completion_date, verified_by)
                         VALUES (?, ?, ?, ?)""", (trainer_id, course, date, verified))
        conn.commit()
        conn.close()
        flash("✅ Qualification saved.")
        return redirect(url_for("trainer_detail", trainer_id=trainer_id))

    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    records = c.execute("SELECT * FROM qualification_records WHERE trainer_id = ?", (trainer_id,)).fetchall()
    conn.close()
    return render_template("ast/add_qualification.html", trainer=trainer, trainer_id=trainer_id, records=records)

# ---------------------- EVALUATION ----------------------
@app.route("/evaluation/<int:trainer_id>", methods=["GET", "POST"])
def evaluation(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()

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
                  (trainer["id"], trainer["name"], evaluator, evaluation_date, rating, weak_reason, notes, filename))
        conn.commit()
        conn.close()
        flash("✅ Evaluation saved.")
        return redirect(url_for("trainer_detail", trainer_id=trainer["trainer_id"]))

    return render_template("ast/evaluation.html", trainer=trainer)

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
