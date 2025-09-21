from flask import *
from flask_cors import CORS
import sqlite3
import os
import random
import warnings
from init_db import init_database

warnings.filterwarnings("ignore")

# Try to import AI libraries, fallback to rule-based if not available
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️  AI libraries not found. Using rule-based responses.")

app = Flask(__name__)
CORS(app)

# Initialize database on startup
init_database()

# Initialize the local AI model (runs without API key)
model = None
tokenizer = None

if AI_AVAILABLE:
    print("🚀 Loading AI model... This may take a few minutes on first run.")
    try:
        # Use a lightweight conversational model
        model_name = "microsoft/DialoGPT-medium"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        
        # Add padding token if it doesn't exist
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        print("✅ AI model loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        model = None
        tokenizer = None
else:
    print("🤖 Using rule-based counselor mode")

def get_student_context(roll_num):
    """Retrieve student data from database"""
    try:
        conn = sqlite3.connect('Database/data.db')
        c = conn.cursor()
        c.execute("SELECT * FROM student_data WHERE roll_num = ?", (roll_num,))
        student = c.fetchone()
        conn.close()
        
        if student:
            return {
                'roll_num': student[0],
                'name': student[1],
                'cgpa': student[2],
                'attendance': student[3],
                'disciplinary_issues': student[4],
                'medical_issues': student[5],
                'risk_level': student[6],
                'risk_percentage': student[7]
            }
        return None
    except Exception as e:
        print(f"Database error: {e}")
        return None

def generate_contextual_response(user_message, student_data):
    """Generate contextual response based on student data and message"""
    name = student_data['name']
    cgpa = student_data['cgpa']
    attendance = student_data['attendance']
    risk_level = student_data['risk_level']
    
    # Create context-aware prompt for the conversation
    context = f"Student {name} (CGPA: {cgpa}, Attendance: {attendance}%, Risk: {risk_level}) says: {user_message}. As an academic counselor, respond supportively:"
    
    return context

def generate_rule_based_response(user_message, student_data):
    """Generate rule-based responses when AI is not available"""
    message_lower = user_message.lower()
    name = student_data['name']
    cgpa = student_data['cgpa']
    attendance = student_data['attendance']
    risk_level = student_data['risk_level']
    
    # Rule-based responses based on keywords and student data
    if any(word in message_lower for word in ['drop', 'quit', 'leaving', 'give up']):
        if float(cgpa) >= 7.0:
            return f"Hi {name}, I see you're considering leaving, but your CGPA of {cgpa} shows real potential. What's been the main challenge you're facing?"
        else:
            return f"Hello {name}, I understand you're going through a tough time. With some support, we can work on improving your {cgpa} CGPA. What's been most difficult for you?"
    
    elif any(word in message_lower for word in ['grade', 'cgpa', 'marks', 'score']):
        if float(cgpa) >= 8.0:
            return f"Your CGPA of {cgpa} is actually quite strong, {name}! What specific subjects are you most concerned about?"
        elif float(cgpa) >= 6.0:
            return f"Your {cgpa} CGPA shows you have the foundation, {name}. Which areas would you like to focus on improving?"
        else:
            return f"I see your CGPA is {cgpa}, {name}. Let's work together on a plan to bring that up. What subjects are most challenging?"
    
    elif any(word in message_lower for word in ['attendance', 'absent', 'miss', 'skip']):
        if float(attendance) >= 80:
            return f"Your attendance of {attendance}% is good, {name}. Are there specific days or classes that are harder to attend?"
        else:
            return f"I see your attendance is at {attendance}%, {name}. What's been making it difficult to attend classes regularly?"
    
    elif any(word in message_lower for word in ['stress', 'pressure', 'worried', 'anxious', 'overwhelmed']):
        return f"It's completely normal to feel stressed, {name}. Many students with {risk_level.lower()} profiles face similar challenges. What's been weighing on your mind the most?"
    
    elif any(word in message_lower for word in ['help', 'support', 'advice']):
        return f"I'm here to help you, {name}. Looking at your academic profile, I think we can definitely create a positive path forward. What area concerns you most?"
    
    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return f"Hello {name}! I'm your academic counselor. I can see you're classified as {risk_level.lower()} - how are you feeling about your studies lately?"
    
    elif any(word in message_lower for word in ['study', 'studying', 'learn']):
        return f"Great that you're focusing on studying, {name}! With your current CGPA of {cgpa}, what study methods have been working best for you?"
    
    elif any(word in message_lower for word in ['time', 'schedule', 'manage']):
        return f"Time management is so important, {name}. With your {attendance}% attendance, would a structured study schedule help? What's your current routine like?"
    
    else:
        # Generic supportive responses
        responses = [
            f"I understand, {name}. Can you tell me more about what's been on your mind regarding your studies?",
            f"That's a valid concern, {name}. Based on your {risk_level.lower()} status, there are definitely ways we can address this together.",
            f"Thank you for sharing that, {name}. How do you think this is affecting your overall academic experience?",
            f"I hear you, {name}. What would be the most helpful thing we could work on right now?"
        ]
        return random.choice(responses)

def generate_ai_response(prompt_text):
    """Generate response using local AI model"""
    if not AI_AVAILABLE or model is None or tokenizer is None:
        return None  # Will fallback to rule-based
    
    try:
        # Encode the prompt
        input_ids = tokenizer.encode(prompt_text, return_tensors='pt', max_length=512, truncation=True)
        
        # Generate response
        with torch.no_grad():
            output = model.generate(
                input_ids,
                max_new_tokens=100,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                attention_mask=torch.ones(input_ids.shape, dtype=torch.long)
            )
        
        # Decode response
        response = tokenizer.decode(output[0], skip_special_tokens=True)
        
        # Extract only the new part (response after the prompt)
        if prompt_text in response:
            response = response.replace(prompt_text, "").strip()
        
        # If response is empty or too short, return None for fallback
        if len(response.strip()) < 10:
            return None
        
        # Clean up and limit response length
        response = response.split('.')[0] + '.' if '.' in response else response
        return response[:200]  # Limit response length
        
    except Exception as e:
        print(f"AI generation error: {e}")
        return None  # Will fallback to rule-based

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

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        roll_num = data.get('roll_num')
        chat_history = data.get('history', [])
        
        if not user_message or not roll_num:
            return jsonify({'error': 'Message and roll number are required'}), 400
        
        # Get student context
        student_data = get_student_context(roll_num)
        if not student_data:
            return jsonify({'error': 'Student data not found'}), 404
        
        # Try AI response first, fallback to rule-based
        bot_response = None
        response_type = "rule_based"
        
        if AI_AVAILABLE:
            prompt = generate_contextual_response(user_message, student_data)
            bot_response = generate_ai_response(prompt)
            if bot_response:
                response_type = "ai_generated"
        
        # Fallback to rule-based if AI failed or unavailable
        if not bot_response:
            bot_response = generate_rule_based_response(user_message, student_data)
        
        return jsonify({
            'response': bot_response,
            'success': True,
            'model_type': response_type,
            'ai_enabled': AI_AVAILABLE
        })
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({
            'response': 'I\'m sorry, I\'m having some technical issues. Please consider speaking with your academic advisor or counselor about your academic concerns.',
            'error': 'An unexpected error occurred'
        }), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'student-dropout-predictor'})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
