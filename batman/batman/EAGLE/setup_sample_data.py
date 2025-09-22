
#!/usr/bin/env python3
"""
Setup clean data for the task management system
"""

from database import Database
import os

def setup_clean_data():
    """Create minimal setup with just admin user"""
    
    # Remove existing database to start fresh
    if os.path.exists("task_management.db"):
        os.remove("task_management.db")
        print("🗑️  Removed existing database")
    
    db = Database()
    
    print("🏢 Creating main company...")
    
    # Create main company
    if db.create_company("Eagle Tech Solutions"):
        print("✅ Created company: Eagle Tech Solutions")
    
    print("\n👥 Creating admin user...")
    
    # Create main admin user
    if db.create_user("admin", "admin123", "Admin", 1):
        print("✅ Created admin user: admin")
    
    print("\n🎉 Clean setup complete!")
    print("\n🔑 Login Credentials:")
    print("="*50)
    print("Admin User:")
    print("  • Username: admin")
    print("  • Password: admin123")
    print("  • Company: Eagle Tech Solutions")
    print("="*50)
    print("\nYou can now create users and companies through the admin panel!")

if __name__ == "__main__":
    setup_clean_data()
