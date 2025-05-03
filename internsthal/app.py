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


@app.route('/companies')
def companies():
    if not conn:
        return "Database not connected", 500

    try:
        cursor.execute("SELECT CompanyID, Name, ContactPerson, Email FROM Companies ORDER BY CompanyID")
        rows = cursor.fetchall()
        # Fetch column names too (optional for table headers)
        columns = [col[0] for col in cursor.description]
        return render_template("companies.html", companies=rows, columns=columns)
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
                SELECT * FROM Students
                WHERE Email = :username AND StudentID = :password
            """, {'username': username, 'password': password})

            user = cursor.fetchone()

            if user:
                session['user'] = username
                return redirect(url_for('home'))
            else:
                error = "Invalid login credentials."

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
            # Check if StudentID exists in Students table
            cursor.execute("SELECT * FROM Students WHERE StudentID = :sid", {'sid': student_id})
            student = cursor.fetchone()

            if not student:
                error = "Student ID not found. Please contact the administrator."
            else:
                # Check if account already exists for that StudentID
                cursor.execute("SELECT * FROM Users WHERE StudentID = :sid", {'sid': student_id})
                existing = cursor.fetchone()

                if existing:
                    error = "An account already exists for this Student ID."
                else:
                    # Insert into Users table
                    cursor.execute("""
                        INSERT INTO Users (UserID, StudentID, Username, Password)
                        VALUES (Users_seq.NEXTVAL, :sid, :uname, :pwd)
                    """, {
                        'sid': student_id,
                        'uname': username,
                        'pwd': password  # In production, hash this!
                    })
                    conn.commit()
                    success = "Account created successfully! You can now log in."

        except Exception as e:
            error = f"Registration failed: {str(e)}"

    return render_template('register.html', error=error, success=success)

if __name__ == '__main__':
    app.run(debug=True)
