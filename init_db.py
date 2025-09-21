import sqlite3
import os

def init_database():
    """Initialize the database with required tables and default admin user"""
    
    # Create Database directory if it doesn't exist
    if not os.path.exists('Database'):
        os.makedirs('Database')
    
    conn = sqlite3.connect('Database/data.db')
    c = conn.cursor()
    
    # Create student_data table
    c.execute('''
        CREATE TABLE IF NOT EXISTS student_data ( 
            roll_num INT PRIMARY KEY,
            student_name VARCHAR(100),
            student_cgpa REAL,
            student_attendance REAL,
            disciplinary_issues VARCHAR(4),
            medical_issues VARCHAR(4),
            student_risk VARCHAR(10),
            risk_percentage REAL,
            student_pass VARCHAR(100)
        )
    ''')
    
    # Create admin_data table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_data (
            admin_name VARCHAR(100),
            admin_type VARCHAR(10),
            admin_password VARCHAR(100)
        )
    ''')
    
    # Insert default admin user if not exists
    c.execute("SELECT COUNT(*) FROM admin_data WHERE admin_name = 'admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO admin_data (admin_name, admin_type, admin_password) VALUES ('admin', 'super', 'admin123')")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()
