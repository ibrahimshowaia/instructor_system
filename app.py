from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3
from datetime import datetime
from io import StringIO
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ========== DATABASE CONNECTIONS ==========
def get_ast_conn():
    return sqlite3.connect('ast_database.db')

def get_rst_conn():
    return sqlite3.connect('rst_database.db')

def get_main_conn():
    return sqlite3.connect('database.db')

def get_db_connection(section):
    conn = sqlite3.connect(f"{section.lower()}_database.db")
    conn.row_factory = sqlite3.Row
    return conn

USERS = {
    "AST": [
        {"username": "ast", "password": "ast123"},
        {"username": "ast2", "password": "ast456"}
    ],
    "RST": [
        {"username": "rst", "password": "rst123"},
        {"username": "rst2", "password": "rst456"}
    ]
}

# ========== LOGIN ==========
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        section = request.form['section']
        username = request.form['username']
        password = request.form['password']

        users = USERS.get(section.upper(), [])
        for user in users:
            if user['username'] == username and user['password'] == password:
                session['section'] = section.lower()
                session['username'] = username
                return redirect(url_for('dashboard', section=section.lower()))

        flash("Invalid username or password.")
        return redirect(url_for('login'))

    return render_template('login.html')

# ========== DASHBOARD ==========
@app.route('/<section>/dashboard')
def dashboard(section):
    conn = get_db_connection(section)
    conn.row_factory = sqlite3.Row
    trainers = conn.execute(f"SELECT * FROM trainers_{section}").fetchall()
    conn.close()

    trainer_list = []
    for row in trainers:
        base_date = datetime.strptime(row['base_month'], "%Y-%m-%d")
        next_year = base_date.replace(year=base_date.year + 1)
        days_remaining = (next_year - datetime.today()).days
        trainer_list.append({
            'id': row['id'],
            'name': row['name'],
            'trainer_id': row['pn'],
            'base_month': row['base_month'],
            'days_remaining': days_remaining
        })

    return render_template(f'{section}/dashboard.html', trainers=trainer_list, section=section)


# ========== ADD TRAINER ==========
@app.route('/add_trainer/<section>', methods=['GET', 'POST'])
def add_trainer(section):
    if request.method == 'POST':
        name = request.form['name']
        pn = request.form['trainer_id']
        base_month = request.form['base_month']
        conn = get_db_connection(section)
        c = conn.cursor()
        c.execute(f"INSERT INTO trainers_{section} (name, pn, base_month) VALUES (?, ?, ?)", (name, pn, base_month))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard', section=section))
    return render_template(f'{section}/add_trainer.html', section=section)


# ========== EDIT TRAINER ==========
@app.route('/edit_trainer/<section>/<trainer_id>', methods=['GET', 'POST'])
def edit_trainer(section, trainer_id):
    conn = get_db_connection(section)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # جلب بيانات المدرب باستخدام pn وليس id
    c.execute(f"SELECT * FROM trainers_{section} WHERE pn = ?", (trainer_id,))
    trainer = c.fetchone()
    if not trainer:
        flash("Trainer not found.")
        conn.close()
        return redirect(url_for('dashboard', section=section))

    trainer_db_id = trainer['id']  # للحصول على الـ id الفعلي للتعديل في قاعدة البيانات

    if request.method == 'POST':
        name = request.form['name']
        base_month = request.form['base_month']
        c.execute(f"UPDATE trainers_{section} SET name=?, base_month=? WHERE id=?", (name, base_month, trainer_db_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard', section=section))

    conn.close()
    return render_template(f'{section}/edit_trainer.html', trainer=trainer, section=section)

# ========== DELETE TRAINER ==========
@app.route('/delete_trainer/<section>/<trainer_id>')
def delete_trainer(section, trainer_id):
    conn = get_db_connection(section)
    c = conn.cursor()
    c.execute(f"DELETE FROM trainers_{section} WHERE id=?", (trainer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard', section=section))


# ========== TRAINER DETAILS ==========
@app.route('/trainer/<section>/<trainer_id>', methods=['GET', 'POST'])
def trainer_detail(section, trainer_id):
    conn = get_db_connection(section)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # البحث عن المدرب باستخدام pn (مثل TR801)
    c.execute(f"SELECT * FROM trainers_{section} WHERE pn = ?", (trainer_id,))
    trainer = c.fetchone()
    if not trainer:
        flash("Trainer not found.")
        return redirect(url_for('dashboard', section=section))

    # جلب ID الفعلي للمدرب من السجل المسترجع
    trainer_db_id = trainer["id"]

    if request.method == 'POST':
        items = request.form.getlist('item[]')
        details = request.form.getlist('detail[]')
        categories = request.form.getlist('category[]')
        notes = request.form.get('general_notes')

        # حذف البيانات القديمة ثم حفظ الجديدة
        c.execute(f"DELETE FROM details_{section} WHERE trainer_id = ?", (trainer_db_id,))
        for i in range(len(items)):
            c.execute(f"INSERT INTO details_{section} (trainer_id, item, detail, category) VALUES (?, ?, ?, ?)",
                      (trainer_db_id, items[i], details[i], categories[i]))
        c.execute(f"UPDATE trainers_{section} SET notes = ? WHERE id = ?", (notes, trainer_db_id))
        conn.commit()
        flash("Details saved successfully.")

    # جلب التفاصيل الخاصة بالمدرب
    c.execute(f"SELECT item, detail, category FROM details_{section} WHERE trainer_id = ?", (trainer_db_id,))
    details = c.fetchall()
    conn.close()

    return render_template(f'{section}/trainer_detail.html', trainer=trainer, details=details, section=section, datetime=datetime)

# ---------- INITIAL ----------
@app.route('/initial/<section>/<int:trainer_id>', methods=['GET', 'POST'])
def initial_generic(section, trainer_id):
    if request.method == 'POST':
        conn_main = get_main_conn()
        c = conn_main.cursor()

        # حفظ بيانات الجدول
        courses = request.form.getlist('course[]')
        dates = request.form.getlist('date[]')
        verified = request.form.getlist('verified[]')

        for i in range(len(courses)):
            c.execute("INSERT INTO initial_records (section, trainer_id, course, date, verified) VALUES (?, ?, ?, ?, ?)",
                      (section, trainer_id, courses[i], dates[i], verified[i]))

        # حفظ التواقيع
        c.execute("INSERT INTO initial_signatures (section, trainer_id, designation, manager_name, manager_signature, manager_date, director_name, director_signature, director_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (section, trainer_id,
                   request.form['designation'],
                   request.form['manager_name'],
                   request.form['manager_signature'],
                   request.form['manager_date'],
                   request.form['director_name'],
                   request.form['director_signature'],
                   request.form['director_date']))
        
        conn_main.commit()
        conn_main.close()
        flash("Initial form submitted successfully.")
        return redirect(url_for('tcfoi_generic', section=section, trainer_id=trainer_id))

    # ==== جلب بيانات المدرب ====
    conn = get_ast_conn() if section == 'ast' else get_rst_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(f"SELECT * FROM trainers_{section} WHERE id=?", (trainer_id,))
    trainer = c.fetchone()

    # تحقق إذا المدرب غير موجود
    if not trainer:
        flash("Trainer not found.")
        return redirect(url_for('dashboard', section=section))

    # ==== جلب بيانات الجدول ====
    conn_main = get_main_conn()
    c_main = conn_main.cursor()
    c_main.execute("SELECT course, date, verified FROM initial_records WHERE section=? AND trainer_id=?", (section, trainer_id))
    records = [{'course': row[0], 'date': row[1], 'verified': row[2]} for row in c_main.fetchall()]
    conn_main.close()

    return render_template(f'{section}/initial.html', trainer=trainer, section=section,
                           current_date=datetime.now().strftime("%d %B %Y"), records=records)

#--------initial_generic-------
@app.route('/initial_print/<section>/<int:trainer_id>')
def initial_print_view(section, trainer_id):
    conn = get_ast_conn() if section == 'ast' else get_rst_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(f"SELECT * FROM trainers_{section} WHERE id=?", (trainer_id,))
    trainer = c.fetchone()

    if not trainer:
        return "Trainer not found"

    conn_main = get_main_conn()
    c_main = conn_main.cursor()
    c_main.execute("SELECT course, date, verified FROM initial_records WHERE section=? AND trainer_id=?", (section, trainer_id))
    records = [{'course': row[0], 'date': row[1], 'verified': row[2]} for row in c_main.fetchall()]
    conn_main.close()

    return render_template(f'{section}/initial.html', trainer=trainer, section=section,
                           current_date=datetime.now().strftime("%d %B %Y"), records=records)

# ---------- TCFOI ----------
@app.route('/tcfoi/<section>/<int:trainer_id>', methods=['GET', 'POST'])
def tcfoi_generic(section, trainer_id):
    conn = get_main_conn()
    c = conn.cursor()

    if request.method == 'POST':
        # استلام بيانات الجدول
        courses = request.form.getlist('instructor[]')
        completion_dates = request.form.getlist('completion_date[]')
        designations = request.form.getlist('designation[]')
        designation_dates = request.form.getlist('designation_date[]')

        # استلام بيانات التوقيع
        director_name = request.form['director_name']
        director_signature = request.form['director_signature']
        director_date = request.form['director_date']

        # حذف السجلات القديمة
        c.execute("DELETE FROM tcfoi_records WHERE section=? AND trainer_id=?", (section, trainer_id))
        c.execute("DELETE FROM tcfoi_signatures WHERE section=? AND trainer_id=?", (section, trainer_id))

        # حفظ السجلات الجديدة
        for i in range(len(courses)):
            c.execute('''
                INSERT INTO tcfoi_records (section, trainer_id, instructor, completion_date, designation, designation_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (section, trainer_id, courses[i], completion_dates[i], designations[i], designation_dates[i]))

        # حفظ التوقيع
        c.execute('''
            INSERT INTO tcfoi_signatures (section, trainer_id, director_name, director_signature, director_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (section, trainer_id, director_name, director_signature, director_date))

        conn.commit()
        conn.close()
        flash('Data saved successfully.')
        return redirect(url_for('tcfoi_generic', section=section, trainer_id=trainer_id))

    # عرض البيانات في حالة GET
    c.execute("SELECT * FROM tcfoi_records WHERE section=? AND trainer_id=?", (section, trainer_id))
    records = c.fetchall()

    c.execute("SELECT * FROM tcfoi_signatures WHERE section=? AND trainer_id=?", (section, trainer_id))
    signature = c.fetchone()

    conn.close()

    conn2 = get_db_connection(section)
    c2 = conn2.cursor()
    c2.execute("SELECT * FROM trainers_" + section.lower() + " WHERE id=?", (trainer_id,))
    trainer = c2.fetchone()
    conn2.close()

    current_date = datetime.now().strftime("%d-%b-%Y").upper()

    return render_template(f"{section}/tcfoi.html", section=section, trainer=trainer, records=records, signature=signature, current_date=current_date)

# ---------- RECURRENT ----------
@app.route('/<section>/recurrent/<int:trainer_id>', methods=['GET', 'POST'])
def recurrent_generic(section, trainer_id):
    conn_main = get_main_conn()  # ✅ استخدم قاعدة البيانات الرئيسية
    conn_main.row_factory = sqlite3.Row
    c = conn_main.cursor()

    if request.method == 'POST':
        courses = request.form.getlist('course[]')
        completion_dates = request.form.getlist('completion_date[]')
        verified_bys = request.form.getlist('verified_by[]')
        manager_name = request.form.get('manager_name')
        signature = request.form.get('signature')
        manager_date = request.form.get('manager_date')

        # حذف السجلات السابقة
        c.execute('DELETE FROM recurrent_records WHERE trainer_id = ?', (trainer_id,))
        c.execute('DELETE FROM recurrent_signatures WHERE trainer_id = ?', (trainer_id,))

        for course, date, verified in zip(courses, completion_dates, verified_bys):
            if course.strip():
                c.execute('''
                    INSERT INTO recurrent_records (section, trainer_id, course, completion_date, verified_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (section, trainer_id, course, date, verified))

        # حفظ التوقيع
        c.execute('''
            INSERT INTO recurrent_signatures (section, trainer_id, manager_name, signature, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (section, trainer_id, manager_name, signature, manager_date))

        conn_main.commit()

    # جلب البيانات من جدول recurrent
    c.execute('SELECT * FROM recurrent_records WHERE trainer_id = ?', (trainer_id,))
    records = c.fetchall()

    # جلب اسم المدرب من قاعدة البيانات الخاصة بالقسم
    conn_trainer = get_db_connection(section)
    conn_trainer.row_factory = sqlite3.Row
    c_trainer = conn_trainer.cursor()
    c_trainer.execute(f"SELECT name FROM trainers_{section} WHERE id = ?", (trainer_id,))
    trainer = c_trainer.fetchone()
    conn_trainer.close()

    trainer_name = trainer['name'] if trainer else 'Unknown'
    today = datetime.today().strftime('%Y-%m-%d')

    return render_template(f'{section}/recurrent.html',
                           trainer_name=trainer_name,
                           trainer_id=trainer_id,
                           date=today,
                           records=records,
                           section=section)

# ---------- ADD QUALIFICATION ----------
@app.route('/add_qualification/<section>/<int:trainer_id>', methods=['GET', 'POST'])
def add_qualification_generic(section, trainer_id):
    if request.method == 'POST':
        conn_main = get_main_conn()
        c = conn_main.cursor()

        # حفظ بيانات الجدول
        courses = request.form.getlist('course[]')
        dates = request.form.getlist('date[]')
        verified = request.form.getlist('verified[]')

        for i in range(len(courses)):
            c.execute("INSERT INTO add_qualification_records (section, trainer_id, course, date, verified) VALUES (?, ?, ?, ?, ?)",
                      (section, trainer_id, courses[i], dates[i], verified[i]))

        # حفظ التواقيع
        c.execute("""INSERT INTO add_qualification_signatures (
                        section, trainer_id, designation, manager_name, manager_signature, manager_date,
                        director_name, director_signature, director_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (section, trainer_id,
                   request.form['designation'],
                   request.form['manager_name'],
                   request.form['manager_signature'],
                   request.form['manager_date'],
                   request.form['director_name'],
                   request.form['director_signature'],
                   request.form['director_date']))

        conn_main.commit()
        conn_main.close()
        flash("Add Qualification form submitted successfully.")
        return redirect(url_for('tcfoi_generic', section=section, trainer_id=trainer_id))

    # ==== جلب بيانات المدرب ====
    conn = get_ast_conn() if section == 'ast' else get_rst_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(f"SELECT * FROM trainers_{section} WHERE id=?", (trainer_id,))
    trainer = c.fetchone()

    if not trainer:
        flash("Trainer not found.")
        return redirect(url_for('dashboard', section=section))

    # ==== جلب بيانات الجدول ====
    conn_main = get_main_conn()
    c_main = conn_main.cursor()
    c_main.execute("SELECT course, date, verified FROM add_qualification_records WHERE section=? AND trainer_id=?",
                   (section, trainer_id))
    records = [{'course': row[0], 'date': row[1], 'verified': row[2]} for row in c_main.fetchall()]
    conn_main.close()

    return render_template(f'{section}/add_qualification.html',
                           trainer=trainer, section=section,
                           current_date=datetime.now().strftime("%d %B %Y"),
                           records=records)

# -------- add_qualification_print_view --------
@app.route('/add_qualification_print/<section>/<int:trainer_id>')
def add_qualification_print_view(section, trainer_id):
    conn = get_ast_conn() if section == 'ast' else get_rst_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(f"SELECT * FROM trainers_{section} WHERE id=?", (trainer_id,))
    trainer = c.fetchone()

    if not trainer:
        return "Trainer not found"

    conn_main = get_main_conn()
    c_main = conn_main.cursor()
    c_main.execute("SELECT course, date, verified FROM add_qualification_records WHERE section=? AND trainer_id=?",
                   (section, trainer_id))
    records = [{'course': row[0], 'date': row[1], 'verified': row[2]} for row in c_main.fetchall()]
    conn_main.close()

    return render_template(f'{section}/add_qualification.html',
                           trainer=trainer, section=section,
                           current_date=datetime.now().strftime("%d %B %Y"),
                           records=records)

# ---------- EVALUATION ----------
@app.route('/evaluation/<section>/<int:trainer_id>', methods=['GET', 'POST'])
def evaluation_generic(section, trainer_id):
    if request.method == 'POST':
        data = {
            'instructor': request.form['instructor_name'],
            'course': request.form['course_name'],
            'observer': request.form['observer_name'],
            'date': request.form['date'],
            'recommendations': request.form['recommendations'],
            'comments': request.form['general_comments'],
            'observer_signature': request.form['observer_signature'],
            'observer_signature_name': request.form['observer_signature_name'],
            'observer_date': request.form['observer_date'],
            'instructor_signature': request.form['instructor_signature'],
            'instructor_signature_name': request.form['instructor_signature_name'],
            'instructor_date': request.form['instructor_date'],
            'manager_name': request.form['manager_name'],
            'manager_signature': request.form['manager_signature'],
            'manager_date': request.form['manager_date'],
        }

        conn = get_main_conn()
        c = conn.cursor()
        c.execute('''INSERT INTO evaluation_records (
                        section, trainer_id, instructor, course, observer, date, recommendations, comments,
                        observer_signature, observer_signature_name, observer_date,
                        instructor_signature, instructor_signature_name, instructor_date,
                        manager_name, manager_signature, manager_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (section, trainer_id, *data.values()))
        conn.commit()
        conn.close()
        flash("Evaluation submitted successfully.")
        return redirect(url_for('dashboard', section=section))

    return render_template(f'{section}/evaluation.html',
                           section=section,
                           trainer_id=trainer_id,
                           date=datetime.now().strftime("%d %B %Y"))

# ========== EXPORT TRAINERS TO EXCEL ==========
@app.route('/download_trainers_excel/<section>')
def download_trainers_excel(section):
    conn = get_db_connection(section)
    c = conn.cursor()
    c.execute(f"SELECT id, name, pn, base_month FROM trainers_{section}")
    trainers = c.fetchall()
    conn.close()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Name', 'PN', 'Base Month'])
    writer.writerows(trainers)

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment; filename={section}_trainers.csv"}
    )


# ========== LOGOUT ==========
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ========== RUN ==========
if __name__ == '__main__':
    app.run(debug=True)