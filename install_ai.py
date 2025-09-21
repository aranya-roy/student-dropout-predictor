#!/usr/bin/env python3
"""
Helper script to install AI dependencies for the chatbot
"""
import subprocess
import sys

def install_packages():
    """Install required packages for AI functionality"""
    packages = [
        'transformers',
        'torch',
        'flask-cors'
    ]
    
    print("🤖 Installing AI Chatbot Dependencies")
    print("=" * 40)
    
    for package in packages:
        print(f"📦 Installing {package}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False
    
    print("\n🎉 All dependencies installed successfully!")
    print("💡 The chatbot will now use advanced AI responses")
    print("🚀 Run: python chatbot.py")
    return True

if __name__ == '__main__':
    success = install_packages()
    if success:
        print("\n✨ Setup complete! You can now use the AI-powered chatbot.")
    else:
        print("\n⚠️  Some packages failed to install. The chatbot will use rule-based responses.")
    
    input("\nPress Enter to continue...")