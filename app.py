from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3, os, csv
from datetime import datetime
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO

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

def calculate_days_remaining(base_month):
    try:
        base_date = datetime.strptime(base_month, "%Y-%m-%d")
        next_year = base_date.replace(year=base_date.year + 1)
        return (next_year - datetime.today()).days
    except:
        return 0

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM trainers")
    trainers = c.fetchall()
    updated_trainers = [{
        'name': t['name'],
        'trainer_id': t['trainer_id'],
        'base_month': t['base_month'],
        'days_remaining': calculate_days_remaining(t['base_month'])
    } for t in trainers]
    conn.close()
    return render_template('ast/dashboard.html', trainers=updated_trainers)

@app.route('/add_trainer', methods=['GET', 'POST'])
def add_trainer():
    if request.method == 'POST':
        name = request.form['name']
        trainer_id = request.form['trainer_id']
        base_month = request.form['base_month']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO trainers (name, trainer_id, base_month) VALUES (?, ?, ?)", (name, trainer_id, base_month))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('ast/add_trainer.html')

@app.route('/edit_trainer/<trainer_id>', methods=['GET', 'POST'])
def edit_trainer(trainer_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        base_month = request.form['base_month']
        c.execute("UPDATE trainers SET name=?, base_month=? WHERE trainer_id=?", (name, base_month, trainer_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    c.execute("SELECT * FROM trainers WHERE trainer_id=?", (trainer_id,))
    trainer = c.fetchone()
    conn.close()
    return render_template('ast/edit_trainer.html', trainer=trainer)

@app.route('/delete_trainer/<trainer_id>', methods=['POST'])
def delete_trainer(trainer_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM trainers WHERE trainer_id=?", (trainer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route("/trainer/<trainer_id>", methods=["GET", "POST"])
def trainer_detail(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == "POST":
        items = request.form.getlist("item[]")
        details = request.form.getlist("detail[]")
        c.execute("DELETE FROM trainer_details WHERE trainer_id = ?", (trainer_id,))
        for item, detail in zip(items, details):
            c.execute("INSERT INTO trainer_details (trainer_id, item, detail) VALUES (?, ?, ?)", (trainer_id, item, detail))
        conn.commit()
    trainer = c.execute("SELECT * FROM trainers WHERE trainer_id = ?", (trainer_id,)).fetchone()
    records = c.execute("SELECT item, detail FROM trainer_details WHERE trainer_id = ?", (trainer_id,)).fetchall()
    conn.close()
    return render_template("ast/trainer_detail.html", trainer=trainer, details=records)

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
    records = c.execute("SELECT * FROM ttfoi_records WHERE trainer_id = ?", (trainer_code,)).fetchall()
    current_date = datetime.today().strftime("%Y-%m-%d")
    conn.close()
    return render_template("ast/initial.html", trainer=trainer, trainer_id=trainer_id, records=records, current_date=current_date)

@app.route("/tcfoi/<int:trainer_id>", methods=["GET", "POST"])
def tcfoi_page(trainer_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    trainer = c.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    trainer_name = trainer["name"]
    trainer_code = trainer["trainer_id"]
    if request.method == "POST":
        courses = request.form.getlist("course[]")
        dates = request.form.getlist("completion_date[]")
        verified_by = request.form.getlist("verified_by[]")
        c.execute("DELETE FROM tcfoi_records WHERE trainer_id = ?", (trainer_code,))
        for course, date, verified in zip(courses, dates, verified_by):
            c.execute("""INSERT INTO tcfoi_records (trainer_id, trainer_name, course, completion_date, verified_by)
                         VALUES (?, ?, ?, ?, ?)""", (trainer_code, trainer_name, course, date, verified))
        conn.commit()
        conn.close()
        flash("✅ TCFOI updated.")
        return redirect(url_for("tcfoi_page", trainer_id=trainer_id))
    current_date = datetime.today().strftime("%Y-%m-%d")
    records = c.execute("SELECT * FROM tcfoi_records WHERE trainer_id = ?", (trainer_code,)).fetchall()
    conn.close()
    return render_template("ast/tcfoi.html", trainer=trainer, records=records, current_date=current_date)

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
    return render_template("ast/recurrent.html", trainer_name=trainer["name"], trainer_id=trainer_code, date=current_date, trainer_id_value=trainer_id, records=records)

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

@app.route("/download_trainers_excel")
def download_trainers_excel():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT name, trainer_id, base_month FROM trainers")
    data = c.fetchall()
    conn.close()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Name", "Trainer ID", "Base Month"])
    cw.writerows(data)
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="trainers.csv")

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
