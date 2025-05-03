import oracledb
from flask import Flask, render_template

app = Flask(__name__)

# Database credentials (fill in your actual values)
db_user = "jchiguru"
db_password = "02597053"
connect_string = "vu2025.cypibltd7eim.us-east-2.rds.amazonaws.com/ORCL"

# Connect to Oracle DB
try:
    conn = oracledb.connect(user=db_user, password=db_password, dsn=connect_string)
    cursor = conn.cursor()
    print("Connected to Oracle DB")
except Exception as e:
    print("Database connection failed:", e)
    conn = None

@app.route('/')
def home():
    db_version = conn.version if conn else "DB not connected"
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)
