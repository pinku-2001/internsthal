from flask import Flask, render_template
import oracledb
import bcrypt


from flask import Flask, render_template, request, redirect, url_for, session


app = Flask(__name__)
app.secret_key = "bdnjbkdjfgnb56sdf"  # Required for session management


db_user = "jchiguru"
db_password = "02597053"  # fill in
connect_string = "vu2025.cypibltd7eim.us-east-2.rds.amazonaws.com/ORCL"

try:
    conn = oracledb.connect(user=db_user, password=db_password, dsn=connect_string)
    cursor = conn.cursor()
    print("Connected to Oracle DB")
except Exception as e:
    print("Database connection failed:", e)
    conn = None

@app.route('/')
def home():
    tables = []
    if conn:
        try:
            cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
            tables = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            tables = [f"Error: {e}"]
    return render_template("index.html", tables=tables)


@app.route('/companies', methods=['GET', 'POST'])
def companies():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    search_query = request.form.get('search') if request.method == 'POST' else None

    try:
        if search_query:
            cursor.execute("""
                SELECT CompanyID, Name, ContactPerson, Email 
                FROM Companies 
                WHERE LOWER(Name) LIKE :search
                ORDER BY CompanyID
            """, {'search': f"%{search_query.lower()}%"})
        else:
            cursor.execute("""
                SELECT CompanyID, Name, ContactPerson, Email 
                FROM Companies 
                ORDER BY CompanyID
            """)
        
        companies = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return render_template('companies.html', companies=companies, columns=columns, search=search_query)

    except Exception as e:
        return f"Error fetching companies: {str(e)}", 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            cursor.execute("""
                SELECT R.Username, R.Password, R.StudentID, S.Name
                FROM StudentRegistrations R
                JOIN Students S ON R.StudentID = S.StudentID
                WHERE R.Username = :uname
            """, {'uname': username})

            user = cursor.fetchone()

            if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
                session['student_id'] = user[2]
                session['username'] = user[0]
                session['name'] = user[3] 
                return redirect("/studenthome")
            else:
                error = "Invalid username or password."
        except Exception as e:
            error = f"Login failed: {str(e)}"

    return render_template('login.html', error=error)



@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None

    if request.method == 'POST':
        student_id = request.form['student_id']
        username = request.form['username']
        password = request.form['password']

        try:
            # 1. Check if StudentID exists in Students table
            cursor.execute("SELECT * FROM Students WHERE StudentID = :sid", {'sid': student_id})
            student = cursor.fetchone()

            if not student:
                error = "Student ID not found. Please contact the administrator."
            else:
                # 2. Check if already registered
                cursor.execute("SELECT * FROM StudentRegistrations WHERE StudentID = :sid", {'sid': student_id})
                existing = cursor.fetchone()

                if existing:
                    error = "An account already exists for this Student ID."
                else:
                    # 3. Hash the password
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

                    # 4. Insert into StudentRegistrations
                    cursor.execute("""
                        INSERT INTO StudentRegistrations (RegID, StudentID, Username, Password)
                        VALUES (Reg_seq.NEXTVAL, :sid, :uname, :pwd)
                    """, {
                        'sid': student_id,
                        'uname': username,
                        'pwd': hashed_password.decode('utf-8')
                    })

                    conn.commit()
                    success = "Account created successfully! You can now log in."

        except Exception as e:
            error = f"Registration failed: {str(e)}"

    return render_template('register.html', error=error, success=success)

@app.route('/studenthome', methods=['GET', 'POST'])
def studenthome():
    return render_template("studentindex.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session['student_id']
    return f"Welcome, Student {student_id}!"


@app.route('/jobs', methods=['GET', 'POST'])
def jobs():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session['student_id']
    search_query = request.form.get('search') if request.method == 'POST' else None

    try:
        # Fetch applied job IDs
        cursor.execute("SELECT JobID FROM Applications WHERE StudentID = :sid", {'sid': student_id})
        applied_jobs = {row[0] for row in cursor.fetchall()}

        # Get job listings with company info
        if search_query:
            cursor.execute("""
                SELECT J.JobID, C.Name AS Company, J.Title, J.Description, J.Deadline, J.Salary, J.Location
                FROM JobPostings J
                JOIN Companies C ON J.CompanyID = C.CompanyID
                WHERE LOWER(J.Title) LIKE :query OR LOWER(J.Location) LIKE :query
                ORDER BY J.Deadline
            """, {'query': f"%{search_query.lower()}%"})
        else:
            cursor.execute("""
                SELECT J.JobID, C.Name AS Company, J.Title, J.Description, J.Deadline, J.Salary, J.Location
                FROM JobPostings J
                JOIN Companies C ON J.CompanyID = C.CompanyID
                ORDER BY J.Deadline
            """)

        jobs = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        return render_template('jobs.html', jobs=jobs, columns=columns, search=search_query, applied_jobs=applied_jobs)

    except Exception as e:
        return f"Error fetching jobs: {str(e)}", 500


@app.route('/apply/<int:job_id>', methods=['POST'])
def apply(job_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))

    try:
        student_id = session['student_id']

        # Optional: Prevent duplicate applications
        cursor.execute("""
            SELECT * FROM Applications 
            WHERE StudentID = :sid AND JobID = :jid
        """, {'sid': student_id, 'jid': job_id})

        if cursor.fetchone():
            return "You have already applied for this job.", 400

        # Insert application with default status and current date
        cursor.execute("""
            INSERT INTO Applications (ApplicationID, StudentID, JobID, ApplyDate, Status)
            VALUES (App_seq.NEXTVAL, :sid, :jid, SYSDATE, 'Pending')
        """, {'sid': student_id, 'jid': job_id})

        conn.commit()
        return redirect(url_for('jobs'))

    except Exception as e:
        return f"Failed to apply: {str(e)}", 500

@app.route('/applications')
def applications():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    try:
        student_id = session['student_id']

        cursor.execute("""
            SELECT J.Title, C.Name, A.Status, TO_CHAR(A.ApplyDate, 'YYYY-MM-DD')
            FROM Applications A
            JOIN JobPostings J ON A.JobID = J.JobID
            JOIN Companies C ON J.CompanyID = C.CompanyID
            WHERE A.StudentID = :sid
            ORDER BY A.ApplyDate DESC
        """, {'sid': student_id})

        applications = cursor.fetchall()
        return render_template('applications.html', applications=applications)

    except Exception as e:
        return f"Error retrieving applications: {str(e)}", 500

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            cursor.execute("""
                SELECT AdminID, Name FROM Admins
                WHERE Username = :uname AND Password = :pwd
            """, {'uname': username, 'pwd': password})

            admin = cursor.fetchone()

            if admin:
                session['admin_id'] = admin[0]
                session['admin_name'] = admin[1]
                return redirect(url_for('adminhome'))  # or home
            else:
                error = "Invalid admin credentials."

        except Exception as e:
            error = f"Login failed: {str(e)}"

    return render_template('admin_login.html', error=error)

@app.route('/adminhome', methods=['GET', 'POST'])
def adminhome():
    return render_template("adminindex.html")

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    success = None
    error = None

    if request.method == 'POST':
        try:
            student_id = int(request.form['student_id'])
            name = request.form['name']
            email = request.form['email']
            gpa = float(request.form['gpa'])
            program_id = int(request.form['program_id'])
            grad_year = int(request.form['grad_year'])

            cursor.execute("""
                INSERT INTO Students (StudentID, Name, GPA, Email, ProgramID, GradYear)
                VALUES (:sid, :name, :gpa, :email, :pid, :grad)
            """, {
                'sid': student_id,
                'name': name,
                'gpa': gpa,
                'email': email,
                'pid': program_id,
                'grad': grad_year
            })

            conn.commit()
            success = f"Student {name} (ID: {student_id}) added successfully."

        except Exception as e:
            error = f"Error adding student: {str(e)}"

    return render_template('add_student.html', success=success, error=error)

@app.route('/show_students')
def show_students():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    try:
        cursor.execute("""
            SELECT StudentID, Name, Email, GPA, ProgramID, GradYear
            FROM Students
            ORDER BY StudentID
        """)
        students = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return render_template('show_students.html', students=students, columns=columns)
    except Exception as e:
        return f"Error fetching students: {str(e)}", 500

@app.route('/add_company', methods=['GET', 'POST'])
def add_company():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    success = None
    error = None

    if request.method == 'POST':
        try:
            name = request.form['name']
            contact_person = request.form['contact_person']
            email = request.form['email']

            cursor.execute("""
                INSERT INTO Companies (CompanyID, Name, ContactPerson, Email)
                VALUES (Company_seq.NEXTVAL, :name, :cperson, :email)
            """, {
                'name': name,
                'cperson': contact_person,
                'email': email
            })

            conn.commit()
            success = f"Company '{name}' added successfully."

        except Exception as e:
            error = f"Error adding company: {str(e)}"

    return render_template('add_company.html', success=success, error=error)


@app.route('/admincompanies')
def admincompanies():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    try:
        cursor.execute("""
            SELECT CompanyID, Name, ContactPerson, Email FROM Companies ORDER BY CompanyID
        """)
        companies = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        return render_template('show_companies.html', companies=companies, columns=columns)
    except Exception as e:
        return f"Error fetching companies: {str(e)}", 500

@app.route('/company_login', methods=['GET', 'POST'])
def company_login():
    error = None

    if request.method == 'POST':
        company_id = request.form['company_id']
        email = request.form['email']

        try:
            cursor.execute("""
                SELECT CompanyID, Name FROM Companies
                WHERE CompanyID = :cid AND Email = :email
            """, {'cid': company_id, 'email': email})

            company = cursor.fetchone()

            if company:
                session['company_id'] = company[0]
                session['company_name'] = company[1]
                session['role'] = 'company'
                return redirect(url_for('companyhome'))  # or 'company_dashboard' if you create one
            else:
                error = "Invalid Company ID or Email."

        except Exception as e:
            error = f"Login failed: {str(e)}"

    return render_template('company_login.html', error=error)

@app.route('/companyhome', methods=['GET', 'POST'])
def companyhome():
    return render_template("companyhome.html")

@app.route('/company_applications', methods=['GET', 'POST'])
def company_applications():
    if 'company_id' not in session:
        return redirect(url_for('company_login'))

    company_id = session['company_id']

    if request.method == 'POST':
        application_id = request.form.get('application_id')
        action = request.form.get('action')

        if action in ['Accepted', 'Rejected']:
            try:
                cursor.execute("""
                    UPDATE Applications
                    SET Status = :status
                    WHERE ApplicationID = :appid
                """, {'status': action, 'appid': application_id})
                conn.commit()
            except Exception as e:
                return f"Error updating application: {str(e)}", 500

    try:
        cursor.execute("""
            SELECT A.ApplicationID, S.StudentID, S.Name, S.Email, J.Title, A.ApplyDate, A.Status
            FROM Applications A
            JOIN Students S ON A.StudentID = S.StudentID
            JOIN JobPostings J ON A.JobID = J.JobID
            WHERE J.CompanyID = :cid
            ORDER BY A.ApplyDate DESC
        """, {'cid': company_id})

        applications = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        return render_template("company_applications.html", applications=applications, columns=columns)

    except Exception as e:
        return f"Error loading applications: {str(e)}", 500
    
@app.route('/company_interviews', methods=['GET', 'POST'])
def company_interviews():
    if 'company_id' not in session:
        return redirect(url_for('company_login'))

    company_id = session['company_id']

    if request.method == 'POST':
        app_id = request.form['application_id']
        interview_date = request.form['interview_date']  # format: YYYY-MM-DD
        mode = request.form['mode']

        try:
            cursor.execute("""
                INSERT INTO Interviews (
                    InterviewID,
                    ApplicationID,
                    InterviewDate,
                    InterviewMode
                ) VALUES (
                    Interview_seq.NEXTVAL,
                    :app_id,
                    TO_DATE(:int_date, 'YYYY-MM-DD'),
                    :int_mode
                )
            """, {
                'app_id': app_id,
                'int_date': interview_date,
                'int_mode': mode
            })
            conn.commit()
        except Exception as e:
            return f"Failed to schedule interview: {str(e)}", 500

    cursor.execute("""
        SELECT A.ApplicationID, S.StudentID, S.Name, J.Title, A.ApplyDate,
               TO_CHAR(I.InterviewDate, 'YYYY-MM-DD') AS InterviewDate,
               I.InterviewMode
        FROM Applications A
        JOIN Students S ON A.StudentID = S.StudentID
        JOIN JobPostings J ON A.JobID = J.JobID
        LEFT JOIN Interviews I ON A.ApplicationID = I.ApplicationID
        WHERE A.Status = 'Accepted' AND J.CompanyID = :cid
        ORDER BY A.ApplyDate DESC
    """, {'cid': company_id})

    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]

    return render_template('company_interviews.html', rows=rows, cols=cols)





@app.route('/student_interviews')
def student_interviews():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session['student_id']

    try:
        cursor.execute("""
            SELECT I.InterviewDate,
                   I.InterviewMode,
                   J.Title AS JobTitle,
                   C.Name AS CompanyName
            FROM Interviews I
            JOIN Applications A ON I.ApplicationID = A.ApplicationID
            JOIN JobPostings J ON A.JobID = J.JobID
            JOIN Companies C ON J.CompanyID = C.CompanyID
            WHERE A.StudentID = :sid
            ORDER BY I.InterviewDate ASC
        """, {'sid': student_id})

        interviews = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        return render_template('student_interviews.html', interviews=interviews, columns=columns)

    except Exception as e:
        return f"Error fetching interviews: {str(e)}", 500


if __name__ == '__main__':
    app.run(debug=True)
