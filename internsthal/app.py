from flask import Flask, render_template
import oracledb

app = Flask(__name__)

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



if __name__ == '__main__':
    app.run(debug=True)
