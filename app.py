from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sres_super_secret_key_2025_academic'

DATABASE = 'sres.db'

# Database helpers
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript('''
        CREATE TABLE IF NOT EXISTS admins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            email       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS students (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    TEXT    UNIQUE NOT NULL,
            first_name    TEXT    NOT NULL,
            last_name     TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password      TEXT    NOT NULL,
            phone         TEXT,
            date_of_birth TEXT,
            address       TEXT,
            program       TEXT,
            year_of_study INTEGER DEFAULT 1,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS courses (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code    TEXT    UNIQUE NOT NULL,
            course_name    TEXT    NOT NULL,
            credits        INTEGER NOT NULL,
            capacity       INTEGER DEFAULT 30,
            enrolled_count INTEGER DEFAULT 0,
            description    TEXT,
            status         TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            course_id   INTEGER NOT NULL,
            status      TEXT DEFAULT 'pending',
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (course_id)  REFERENCES courses(id),
            UNIQUE(student_id, course_id)
        );
    ''')

    # Default admin
    try:
        cur.execute("INSERT INTO admins (username, password, email) VALUES (?,?,?)",
                    ('admin', generate_password_hash('admin123'), 'admin@sres.edu'))
    except sqlite3.IntegrityError:
        pass

    # Seed courses
    courses = [
        ('AI',   'Artificial Intelligence',              3, 70, 'Study of AI algorithms and intelligent systems.'),
        ('ML',   'Machine Learning',                     3, 70, 'Machine learning concepts, algorithms & applications.'),
        ('SE',   'Software Engineering',                 3, 70, 'Software development lifecycle and methodologies.'),
        ('DVA',  'Data Visualisation and Analytics',     3, 70, 'Data analysis, visualisation and statistical tools.'),
        ('DL',   'Deep Learning',                        3, 70, 'Neural networks and deep learning architectures.'),
        ('NLP',  'Natural Language Processing',          3, 70, 'Processing and understanding human language with AI.'),
        ('ED',   'Entrepreneurship Development',         2, 70, 'Business development and entrepreneurship skills.'),
        ('CN',   'Computer Networks',                    3, 70, 'Network protocols, architecture and communication.'),
        ('FLAT', 'Formal Language Automata Theory',      3, 70, 'Formal languages, grammars and computation theory.'),
        ('OB',   'Organizational Behaviour',             2, 70, 'Human behaviour and dynamics in organisations.'),
    ]
    for code, name, credits, cap, desc in courses:
        try:
            cur.execute(
                "INSERT INTO courses (course_code,course_name,credits,capacity,description) VALUES (?,?,?,?,?)",
                (code, name, credits, cap, desc))
        except sqlite3.IntegrityError:
            pass

    # Update capacity for all seeded courses (handles existing DB with old values)
    seeded = ('AI','ML','SE','DVA','DL','NLP','ED','CN','FLAT','OB')
    cur.execute(
        f"UPDATE courses SET capacity=70 WHERE course_code IN ({','.join('?'*len(seeded))})",
        seeded)

    conn.commit()

    # Migrate: add semester column if it doesn't exist yet
    try:
        cur.execute('ALTER TABLE students ADD COLUMN semester INTEGER DEFAULT 1')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.close()

# ─────────────────────────────────────────
#  Auth decorators
# ─────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'student_id' not in session:
            flash('Please login to continue.', 'error')
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin access required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
#  Landing
# ─────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ═══════════════════════════════════════════
#  STUDENT ROUTES
# ═══════════════════════════════════════════

@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        first_name      = request.form.get('first_name', '').strip()
        last_name       = request.form.get('last_name', '').strip()
        email           = request.form.get('email', '').strip().lower()
        password        = request.form.get('password', '')
        confirm_pass    = request.form.get('confirm_password', '')
        phone           = request.form.get('phone', '').strip()
        dob             = request.form.get('date_of_birth', '')
        address         = request.form.get('address', '').strip()
        program         = request.form.get('program', '').strip()
        semester        = int(request.form.get('semester', 1))
        year_of_study   = (semester + 1) // 2   # auto-calc: sem1-2→yr1, sem3-4→yr2 …

        errors = []
        if not first_name or not last_name:
            errors.append('First and last name are required.')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_pass:
            errors.append('Passwords do not match.')
        if not program:
            errors.append('Please select your program.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('student/register.html', form_data=request.form)

        conn = get_db()
        cur  = conn.cursor()
        cur.execute('SELECT id FROM students WHERE email = ?', (email,))
        if cur.fetchone():
            flash('Email already registered. Please login.', 'error')
            conn.close()
            return render_template('student/register.html', form_data=request.form)

        year  = datetime.now().year
        cur.execute('SELECT COUNT(*) AS cnt FROM students')
        count = cur.fetchone()['cnt'] + 1
        student_id = f'STU{year}{count:04d}'

        try:
            cur.execute('''
                INSERT INTO students
                  (student_id,first_name,last_name,email,password,phone,date_of_birth,address,program,year_of_study,semester)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ''', (student_id, first_name, last_name, email,
                  generate_password_hash(password), phone, dob, address, program, year_of_study, semester))
            conn.commit()
            flash(f'Registration successful! Your Student ID: {student_id}. Please login.', 'success')
            return redirect(url_for('student_login'))
        except Exception:
            flash('Registration failed. Please try again.', 'error')
        finally:
            conn.close()

    return render_template('student/register.html', form_data={})


@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if 'student_id' in session:
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db()
        cur  = conn.cursor()
        cur.execute('SELECT * FROM students WHERE email = ?', (email,))
        student = cur.fetchone()
        conn.close()

        if student and check_password_hash(student['password'], password):
            session['student_id']   = student['id']
            session['student_name'] = f"{student['first_name']} {student['last_name']}"
            session['student_uid']  = student['student_id']
            flash(f'Welcome back, {student["first_name"]}! 👋', 'success')
            return redirect(url_for('student_dashboard'))
        flash('Invalid email or password.', 'error')

    return render_template('student/login.html')


@app.route('/student/logout')
def student_logout():
    session.pop('student_id', None)
    session.pop('student_name', None)
    session.pop('student_uid', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))


@app.route('/student/dashboard')
@login_required
def student_dashboard():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM students WHERE id = ?', (session['student_id'],))
    student = cur.fetchone()

    cur.execute('''
        SELECT e.*, c.course_name, c.course_code, c.credits
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.student_id = ?
        ORDER BY e.enrolled_at DESC
    ''', (session['student_id'],))
    enrollments = cur.fetchall()
    conn.close()

    approved = [e for e in enrollments if e['status'] == 'approved']
    pending  = [e for e in enrollments if e['status'] == 'pending']
    total_credits = sum(e['credits'] for e in approved)

    return render_template('student/dashboard.html',
                           student=student,
                           enrollments=enrollments,
                           approved_count=len(approved),
                           pending_count=len(pending),
                           total_credits=total_credits)


@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    conn = get_db()
    cur  = conn.cursor()

    if request.method == 'POST':
        first_name    = request.form.get('first_name', '').strip()
        last_name     = request.form.get('last_name', '').strip()
        phone         = request.form.get('phone', '').strip()
        dob           = request.form.get('date_of_birth', '')
        address       = request.form.get('address', '').strip()
        program       = request.form.get('program', '').strip()
        semester      = int(request.form.get('semester', 1))
        year_of_study = (semester + 1) // 2   # auto-calc from semester
        cur_pass      = request.form.get('current_password', '')
        new_pass      = request.form.get('new_password', '')
        cnf_pass      = request.form.get('confirm_new_password', '')

        if new_pass:
            cur.execute('SELECT password FROM students WHERE id = ?', (session['student_id'],))
            row = cur.fetchone()
            if not check_password_hash(row['password'], cur_pass):
                flash('Current password is incorrect.', 'error')
                conn.close()
                return redirect(url_for('student_profile'))
            if len(new_pass) < 6:
                flash('New password must be at least 6 characters.', 'error')
                conn.close()
                return redirect(url_for('student_profile'))
            if new_pass != cnf_pass:
                flash('New passwords do not match.', 'error')
                conn.close()
                return redirect(url_for('student_profile'))
            cur.execute('''
                UPDATE students SET first_name=?,last_name=?,phone=?,date_of_birth=?,
                address=?,program=?,year_of_study=?,semester=?,password=? WHERE id=?
            ''', (first_name, last_name, phone, dob, address, program,
                  year_of_study, semester, generate_password_hash(new_pass), session['student_id']))
        else:
            cur.execute('''
                UPDATE students SET first_name=?,last_name=?,phone=?,date_of_birth=?,
                address=?,program=?,year_of_study=?,semester=? WHERE id=?
            ''', (first_name, last_name, phone, dob, address, program,
                  year_of_study, semester, session['student_id']))

        conn.commit()
        session['student_name'] = f"{first_name} {last_name}"
        flash('Profile updated successfully!', 'success')
        conn.close()
        return redirect(url_for('student_profile'))

    cur.execute('SELECT * FROM students WHERE id = ?', (session['student_id'],))
    student = cur.fetchone()
    conn.close()
    return render_template('student/profile.html', student=student)


@app.route('/student/courses')
@login_required
def student_courses():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''
        SELECT c.*, e.status AS enrollment_status, e.id AS enrollment_id
        FROM courses c
        LEFT JOIN enrollments e ON c.id = e.course_id AND e.student_id = ?
        WHERE c.status = 'active'
        ORDER BY c.course_code
    ''', (session['student_id'],))
    courses = cur.fetchall()
    conn.close()
    return render_template('student/courses.html', courses=courses)


@app.route('/student/enroll/<int:course_id>', methods=['POST'])
@login_required
def student_enroll(course_id):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM courses WHERE id=? AND status='active'", (course_id,))
    course = cur.fetchone()

    if not course:
        flash('Course not available.', 'error')
        conn.close()
        return redirect(url_for('student_courses'))
    if course['enrolled_count'] >= course['capacity']:
        flash(f'{course["course_name"]} is at full capacity.', 'error')
        conn.close()
        return redirect(url_for('student_courses'))

    cur.execute('SELECT id FROM enrollments WHERE student_id=? AND course_id=?',
                (session['student_id'], course_id))
    if cur.fetchone():
        flash('You already have an enrollment request for this course.', 'warning')
        conn.close()
        return redirect(url_for('student_courses'))

    try:
        cur.execute("INSERT INTO enrollments (student_id,course_id,status) VALUES (?,?,'pending')",
                    (session['student_id'], course_id))
        conn.commit()
        flash(f'Enrollment request for {course["course_name"]} submitted! Awaiting approval.', 'success')
    except Exception:
        flash('Enrollment failed. Please try again.', 'error')
    finally:
        conn.close()
    return redirect(url_for('student_courses'))


@app.route('/student/enrollments')
@login_required
def student_enrollments():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''
        SELECT e.*, c.course_name, c.course_code, c.credits
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.student_id = ?
        ORDER BY e.enrolled_at DESC
    ''', (session['student_id'],))
    enrollments = cur.fetchall()
    conn.close()
    return render_template('student/enrollments.html', enrollments=enrollments)


# ═══════════════════════════════════════════
#  ADMIN ROUTES
# ═══════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        cur  = conn.cursor()
        cur.execute('SELECT * FROM admins WHERE username = ?', (username,))
        admin = cur.fetchone()
        conn.close()

        if admin and check_password_hash(admin['password'], password):
            session['admin_id']       = admin['id']
            session['admin_username'] = admin['username']
            flash(f'Welcome, {admin["username"]}! 🛡️', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials.', 'error')

    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute('SELECT COUNT(*) AS c FROM students')
    student_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM courses WHERE status='active'")
    course_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status='pending'")
    pending_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status='approved'")
    approved_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status='rejected'")
    rejected_count = cur.fetchone()['c']

    cur.execute('''
        SELECT e.*, s.first_name, s.last_name, s.student_id AS stu_id,
               c.course_name, c.course_code
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        JOIN courses  c ON e.course_id  = c.id
        ORDER BY e.enrolled_at DESC
        LIMIT 10
    ''')
    recent = cur.fetchall()
    conn.close()

    return render_template('admin/dashboard.html',
                           student_count=student_count,
                           course_count=course_count,
                           pending_count=pending_count,
                           approved_count=approved_count,
                           rejected_count=rejected_count,
                           recent_enrollments=recent)


@app.route('/admin/students')
@admin_required
def admin_students():
    conn    = get_db()
    cur     = conn.cursor()
    search  = request.args.get('search', '').strip()

    if search:
        like = f'%{search}%'
        cur.execute('''
            SELECT s.*, COUNT(e.id) AS enrollment_count
            FROM students s
            LEFT JOIN enrollments e ON s.id = e.student_id AND e.status = 'approved'
            WHERE s.first_name LIKE ? OR s.last_name LIKE ?
               OR s.email LIKE ? OR s.student_id LIKE ?
            GROUP BY s.id ORDER BY s.created_at DESC
        ''', (like, like, like, like))
    else:
        cur.execute('''
            SELECT s.*, COUNT(e.id) AS enrollment_count
            FROM students s
            LEFT JOIN enrollments e ON s.id = e.student_id AND e.status = 'approved'
            GROUP BY s.id ORDER BY s.created_at DESC
        ''')

    students = cur.fetchall()
    conn.close()
    return render_template('admin/students.html', students=students, search=search)


@app.route('/admin/students/<int:sid>/delete', methods=['POST'])
@admin_required
def admin_delete_student(sid):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT course_id FROM enrollments WHERE student_id=? AND status='approved'", (sid,))
    for row in cur.fetchall():
        cur.execute('UPDATE courses SET enrolled_count = enrolled_count - 1 WHERE id=?', (row['course_id'],))
    cur.execute('DELETE FROM enrollments WHERE student_id=?', (sid,))
    cur.execute('DELETE FROM students WHERE id=?', (sid,))
    conn.commit()
    conn.close()
    flash('Student deleted successfully.', 'success')
    return redirect(url_for('admin_students'))


@app.route('/admin/courses')
@admin_required
def admin_courses():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM courses ORDER BY course_code')
    courses = cur.fetchall()
    conn.close()
    return render_template('admin/courses.html', courses=courses)


@app.route('/admin/courses/add', methods=['GET', 'POST'])
@admin_required
def admin_add_course():
    if request.method == 'POST':
        code    = request.form.get('course_code', '').strip().upper()
        name    = request.form.get('course_name', '').strip()
        credits = int(request.form.get('credits', 3))
        cap     = int(request.form.get('capacity', 30))
        desc    = request.form.get('description', '').strip()
        status  = request.form.get('status', 'active')

        if not code or not name:
            flash('Course code and name are required.', 'error')
            return render_template('admin/course_form.html', action='Add', course={})

        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO courses (course_code,course_name,credits,capacity,description,status) VALUES (?,?,?,?,?,?)',
                (code, name, credits, cap, desc, status))
            conn.commit()
            flash('Course added successfully!', 'success')
            return redirect(url_for('admin_courses'))
        except sqlite3.IntegrityError:
            flash('Course code already exists.', 'error')
        finally:
            conn.close()

    return render_template('admin/course_form.html', action='Add', course={})


@app.route('/admin/courses/<int:cid>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(cid):
    conn = get_db()
    cur  = conn.cursor()

    if request.method == 'POST':
        name    = request.form.get('course_name', '').strip()
        credits = int(request.form.get('credits', 3))
        cap     = int(request.form.get('capacity', 30))
        desc    = request.form.get('description', '').strip()
        status  = request.form.get('status', 'active')

        cur.execute('''
            UPDATE courses SET course_name=?,credits=?,capacity=?,description=?,status=?
            WHERE id=?
        ''', (name, credits, cap, desc, status, cid))
        conn.commit()
        conn.close()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('admin_courses'))

    cur.execute('SELECT * FROM courses WHERE id=?', (cid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        flash('Course not found.', 'error')
        return redirect(url_for('admin_courses'))
    # Convert Row → dict so Jinja2 template can use .get() safely
    course = dict(row)
    return render_template('admin/course_form.html', action='Edit', course=course)


@app.route('/admin/courses/<int:cid>/delete', methods=['POST'])
@admin_required
def admin_delete_course(cid):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('DELETE FROM enrollments WHERE course_id=?', (cid,))
    cur.execute('DELETE FROM courses WHERE id=?', (cid,))
    conn.commit()
    conn.close()
    flash('Course deleted.', 'success')
    return redirect(url_for('admin_courses'))


@app.route('/admin/enrollments')
@admin_required
def admin_enrollments():
    conn   = get_db()
    cur    = conn.cursor()
    status = request.args.get('status', 'all')

    query = '''
        SELECT e.*, s.first_name, s.last_name, s.student_id AS stu_id,
               c.course_name, c.course_code
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        JOIN courses  c ON e.course_id  = c.id
        {where}
        ORDER BY e.enrolled_at DESC
    '''
    if status == 'all':
        cur.execute(query.format(where=''))
    else:
        cur.execute(query.format(where='WHERE e.status = ?'), (status,))

    enrollments = cur.fetchall()
    conn.close()
    return render_template('admin/enrollments.html', enrollments=enrollments, status_filter=status)


@app.route('/admin/enrollments/<int:eid>/approve', methods=['POST'])
@admin_required
def admin_approve_enrollment(eid):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM enrollments WHERE id=?', (eid,))
    enr = cur.fetchone()

    if enr and enr['status'] == 'pending':
        cur.execute('SELECT * FROM courses WHERE id=?', (enr['course_id'],))
        course = cur.fetchone()
        if course['enrolled_count'] >= course['capacity']:
            flash('Cannot approve: course is at full capacity.', 'error')
        else:
            cur.execute("UPDATE enrollments SET status='approved',updated_at=CURRENT_TIMESTAMP WHERE id=?", (eid,))
            cur.execute('UPDATE courses SET enrolled_count=enrolled_count+1 WHERE id=?', (enr['course_id'],))
            conn.commit()
            flash('Enrollment approved!', 'success')
    conn.close()
    return redirect(url_for('admin_enrollments', status=request.args.get('status', 'all')))


@app.route('/admin/enrollments/<int:eid>/reject', methods=['POST'])
@admin_required
def admin_reject_enrollment(eid):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM enrollments WHERE id=?', (eid,))
    enr = cur.fetchone()
    if enr and enr['status'] == 'approved':
        # Decrement on rejection of approved enrollment
        cur.execute('UPDATE courses SET enrolled_count=enrolled_count-1 WHERE id=?', (enr['course_id'],))
    cur.execute("UPDATE enrollments SET status='rejected',updated_at=CURRENT_TIMESTAMP WHERE id=?", (eid,))
    conn.commit()
    conn.close()
    flash('Enrollment rejected.', 'success')
    return redirect(url_for('admin_enrollments', status=request.args.get('status', 'all')))


@app.route('/admin/reports')
@admin_required
def admin_reports():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute('''
        SELECT c.course_code, c.course_name, c.credits, c.capacity, c.enrolled_count,
               COUNT(CASE WHEN e.status='pending'  THEN 1 END) AS pending_cnt,
               COUNT(CASE WHEN e.status='rejected' THEN 1 END) AS rejected_cnt
        FROM courses c
        LEFT JOIN enrollments e ON c.id = e.course_id
        GROUP BY c.id ORDER BY c.course_code
    ''')
    course_stats = cur.fetchall()

    cur.execute('''
        SELECT program, COUNT(*) AS cnt FROM students
        WHERE program IS NOT NULL AND program != ''
        GROUP BY program ORDER BY cnt DESC
    ''')
    program_stats = cur.fetchall()

    cur.execute('SELECT COUNT(*) AS c FROM students')
    total_students = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status='approved'")
    total_approved = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status='pending'")
    total_pending = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status='rejected'")
    total_rejected = cur.fetchone()['c']

    conn.close()
    return render_template('admin/reports.html',
                           course_stats=course_stats,
                           program_stats=program_stats,
                           total_students=total_students,
                           total_approved=total_approved,
                           total_pending=total_pending,
                           total_rejected=total_rejected)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
