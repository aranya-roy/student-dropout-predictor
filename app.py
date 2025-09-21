from flask import *
import sqlite3
import os
from init_db import init_database

app = Flask(__name__)

# Initialize database on startup
init_database()

@app.route("/")
def root_page():
    return render_template('home.html')

@app.route("/admin")
def admin_page():
    return render_template('admin.html')

@app.route("/student")
def student_page():
    conn = sqlite3.connect("Database/data.db")  
    c = conn.cursor()
    c.execute("SELECT * FROM student_data")
    all_students = c.fetchall()
    conn.close()
    print(all_students)
    if not all_students:
        return render_template('nostudent.html')
    return render_template('student.html')

@app.route("/admin-page", methods=["POST"])
def adminpage_page():
    username = request.form["username"]
    password = request.form["password"]
    conn = sqlite3.connect("Database/data.db")  
    c = conn.cursor()
    c.execute("SELECT * FROM admin_data")
    all_admins = c.fetchall()
    conn.close()
    bool_value=False
    for i in all_admins:
        admin_name=i[0]
        admin_type=i[1]
        admin_password=i[2]
        if admin_name==username:
            if admin_password==password:
                bool_value=True
    if bool_value==True: 
        return render_template('admin-page1.html')
    else:
        return render_template('admin-page0.html')
    
@app.route("/admin-output", methods=["POST"])
def output_page():
    try:
        conn = sqlite3.connect("Database/data.db")  
        c = conn.cursor()
        file=request.files["csvfile"]
        
        if not file or file.filename == '':
            return render_template('admin-upload-error.html')
            
        if not file.filename.lower().endswith('.csv'):
            return render_template('admin-upload-error.html')
            
        lines = file.read().decode("utf-8").splitlines()
        
        if len(lines) < 2:
            return render_template('admin-upload-error.html')
            
        for i in range(1, len(lines), 1):
            second_line = lines[i].strip()
            if not second_line:  # Skip empty lines
                continue
            try:
                roll_number, student_name, student_cgpa, student_attendance, disciplinary_issues, medical_issues = second_line.split(",")
            except ValueError:
                continue  # Skip malformed lines

            try:
                student_cgpa = float(student_cgpa)
                student_attendance = float(student_attendance)
            except ValueError:
                continue  # Skip lines with invalid numeric data

            risk_score = 0
        
            cgpa_risk = max(0, (10 - student_cgpa) / 10 * 50)
            risk_score += cgpa_risk

            attendance_risk = max(0, (100 - student_attendance) / 100 * 30)
            risk_score += attendance_risk

            if disciplinary_issues == "True":
                risk_score += 10

            if medical_issues == "True":
                risk_score += 10

            risk_percentage = round(min(max(risk_score, 1), 99), 2)

            if risk_percentage >= 70:
                student_risk = "High Risk"
            elif risk_percentage >= 40:
                student_risk = "Medium Risk"
            else:
                student_risk = "Low Risk"

            try:
                c.execute("""
                    INSERT INTO student_data 
                    (roll_num, student_name, student_cgpa, student_attendance, disciplinary_issues, medical_issues, student_risk, risk_percentage, student_pass) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (roll_number, student_name, student_cgpa, student_attendance, disciplinary_issues, medical_issues, student_risk, risk_percentage, None))
            except sqlite3.IntegrityError:
                continue  # Skip duplicate roll numbers
                
        conn.commit()
        c.execute("SELECT * FROM student_data")
        all_students = c.fetchall()
        conn.close()
        return render_template('admin-output.html',all_students=all_students)
        
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return render_template('admin-upload-error.html')

@app.route("/student-page", methods=["POST"])
def studentpage_page():
    conn = sqlite3.connect("Database/data.db")  
    c = conn.cursor()
    c.execute("SELECT * FROM student_data")
    all_students = c.fetchall()
    conn.close()
    roll_number=int(request.form["roll_number"])
    password=request.form["password"]
    check=False
    student_password=None
    rollnum=None
    name=None
    cgpa=None
    attendance=None
    disciplinary_issues=None
    medical_issues=None
    
    for i in all_students:
        if roll_number==i[0]:
            check=True
            rollnum=i[0]
            name=i[1]
            cgpa=i[2]
            attendance=i[3]
            disciplinary_issues=i[4]
            medical_issues=i[5]
            student_password=i[8]
            break
            
    if check==False:
        return render_template("nostudent1.html")
        
    if student_password==None:
        return render_template("student-nothere.html")
        
    bool_value=False
    if roll_number==rollnum:
        if password==student_password:
            bool_value=True
    if bool_value==True: 
        return render_template('student-page1.html',rollnum=rollnum,name=name,cgpa=cgpa,attendance=attendance,disciplinary_issues=disciplinary_issues,medical_issues=medical_issues)
    else:
        return render_template('student-page0.html')
    
@app.route("/admin-upload")
def admin_upload():
    return render_template('admin-page1.html')

@app.route("/create-student", methods=["POST"])
def create_student():
    return render_template("create-student.html")

@app.route("/student-creation", methods=["POST"])
def student_creation():
    rollnum=request.form["roll_number"]
    password=request.form["password"]
    conn = sqlite3.connect("Database/data.db")  
    c = conn.cursor()
    c.execute("SELECT * FROM student_data")
    all_students = c.fetchall()
    check=False
    for i in all_students:
        if int(rollnum)==i[0]:
            check=True
    if check==False:
        conn.close()
        return render_template("nostudent1.html")
    c.execute("""
            UPDATE student_data
            SET student_pass=? 
            WHERE roll_num=?
        """, (password, int(rollnum)))
    conn.commit()
    conn.close()
    return redirect('/student')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
