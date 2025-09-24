
#!/usr/bin/env python3
"""
Eagle Task Management System - Web Application Only
"""

from database import Database
import sys
import os

def setup_initial_data():
    """Setup initial admin user and sample company""" 
    db = Database()
    
    # Create a sample company
    if db.create_company("TechCorp"):
        print("✅ Created sample company: TechCorp")
    
    # Create initial admin user
    if db.create_user("admin", "admin123", "Admin", 1):
        print("✅ Created initial admin user")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Role: Admin")
    else:
        print("ℹ️  Admin user already exists")

def main():
    """Main function - starts web application directly"""
    print("🚀 Starting Eagle Task Management System...")
    
    try:
        # Setup initial data
        setup_initial_data()
        
        print("\n" + "="*60)
        print("EAGLE TASK MANAGEMENT SYSTEM")
        print("="*60)
        print("📋 Features:")
        print("   • Multi-company support")
        print("   • Role-based access control")
        print("   • Task assignment and tracking")
        print("   • Real-time messaging")
        print("   • File attachments")
        print("   • Telegram notifications")
        print("   • Email notifications")
        print("\n🌐 Web Interface Starting...")
        print("   • Access at: http://0.0.0.0:5000")
        print("   • Username: admin")
        print("   • Password: admin123")
        print("="*60)
        
        # Import and start web app
        from web_app import app, socketio
        
        # Run the web application
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
        
    except KeyboardInterrupt:
        print("\n\n👋 Application terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
