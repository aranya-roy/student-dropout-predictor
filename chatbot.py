from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import warnings
warnings.filterwarnings("ignore")

# Try to import AI libraries, fallback to rule-based if not available
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️  AI libraries not found. Using rule-based responses.")
    print("   To enable full AI: pip install transformers torch")

app = Flask(__name__)
CORS(app)

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
    return jsonify({'status': 'healthy', 'service': 'chatbot'})

if __name__ == '__main__':
    print("\n🚀 Starting Academic Counselor Chatbot Service...")
    if AI_AVAILABLE and model is not None:
        print("🤖 Using Microsoft DialoGPT - Advanced AI responses enabled!")
    else:
        print("🤖 Using intelligent rule-based responses (no AI libraries needed)")
        print("   For advanced AI: pip install transformers torch")
    print("🌐 Server starting on http://localhost:5001")
    print("✅ Ready to provide personalized academic counseling!\n")
    app.run(host='0.0.0.0', port=5001, debug=False)
