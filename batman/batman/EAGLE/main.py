
#!/usr/bin/env python3
"""
Task Management System
A CLI-based task management application with role-based access control
"""
#import os 
#import sys
 #sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))
#initializing the path to the parent directory of the current file 
#os.path.dirname(__file__) gets the directory name of the current file 
#then os.path.abspath() gets the absolute path of that directory
#kill the  process and restart the application 
#tm.db.kill_process()
#os.system('python3 main.py')
#operatorreload module os used to reload the model


from cli_interface import CLIInterface
from task_manager import TaskManager
import sys

def setup_initial_data():
    """Setup initial admin user and sample company""" 
    tm = TaskManager()
    
    # Create a sample company
    if tm.db.create_company("TechCorp"):
        print("✅ Created sample company: TechCorp")
    
    # Create initial admin user
    if tm.db.create_user("admin", "admin123", "Admin", 1):
        print("✅ Created initial admin user")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Role: Admin")
    else:
        print("ℹ️  Admin user already exists")

def main():
    """Main function"""
    print("🚀 Initializing Task Management System...")
    
    try:
        # Setup initial data
        setup_initial_data()
        
        print("\n" + "="*60)
        print("TASK MANAGEMENT SYSTEM")
        print("="*60)
        print("📋 Features:")
        print("   • Multi-company support (up to 7 companies)")
        print("   • Role-based access control (Admin, Manager, Employee)")
        print("   • Task assignment and status tracking")
        print("   • Company data isolation")
        print("\n🔑 Initial Login Credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print("="*60)
        
        input("\nPress Enter to start the application...")
        
        # Start the CLI interface
        cli = CLIInterface()
        cli.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 Application terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
