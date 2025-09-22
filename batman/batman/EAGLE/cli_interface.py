
import os
from task_manager import TaskManager

class CLIInterface:
    def __init__(self):
        self.task_manager = TaskManager()
    
    def clear_screen(self):
        """Clear the screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """Print a formatted header"""
        print("=" * 60)
        print(f"{title:^60}")
        print("=" * 60)
    
    def print_menu_options(self, options: list):
        """Print menu options"""
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        print("0. Exit/Logout")
    
    def get_user_choice(self, max_option: int) -> int:
        """Get user menu choice"""
        while True:
            try:
                choice = int(input(f"\nEnter your choice (0-{max_option}): "))
                if 0 <= choice <= max_option:
                    return choice
                else:
                    print(f"Please enter a number between 0 and {max_option}")
            except ValueError:
                print("Please enter a valid number")
    
    def login_screen(self):
        """Login screen"""
        self.clear_screen()
        self.print_header("TASK MANAGEMENT SYSTEM - LOGIN")
        
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        if self.task_manager.login(username, password):
            user = self.task_manager.get_current_user()
            print(f"\n✅ Welcome, {user['username']} ({user['role']})!")
            input("Press Enter to continue...")
            return True
        else:
            print("\n❌ Invalid username or password!")
            input("Press Enter to try again...")
            return False
    
    def admin_menu(self):
        """Admin main menu"""
        while True:
            self.clear_screen()
            user = self.task_manager.get_current_user()
            self.print_header(f"ADMIN PANEL - {user['username']}")
            
            options = [
                "Register Company",
                "Create User",
                "Assign Task",
                "View All Tasks",
                "View Task Statistics"
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice(len(options))
            
            if choice == 0:
                break
            elif choice == 1:
                self.register_company()
            elif choice == 2:
                self.create_user()
            elif choice == 3:
                self.assign_task()
            elif choice == 4:
                self.view_all_tasks()
            elif choice == 5:
                self.view_task_statistics()
    
    def manager_employee_menu(self):
        """Manager/Employee main menu"""
        while True:
            self.clear_screen()
            user = self.task_manager.get_current_user()
            self.print_header(f"{user['role'].upper()} PANEL - {user['username']}")
            
            options = [
                "View My Tasks",
                "Update Task Status"
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice(len(options))
            
            if choice == 0:
                break
            elif choice == 1:
                self.view_my_tasks()
            elif choice == 2:
                self.update_my_task_status()
    
    def register_company(self):
        """Register a new company"""
        self.clear_screen()
        self.print_header("REGISTER COMPANY")
        
        companies = self.task_manager.get_companies()
        if len(companies) >= 7:
            print("❌ Maximum of 7 companies allowed!")
            input("Press Enter to continue...")
            return
        
        print(f"Current companies: {len(companies)}/7")
        for company in companies:
            print(f"  - {company['name']}")
        
        print()
        name = input("Enter company name: ").strip()
        
        if not name:
            print("❌ Company name cannot be empty!")
            input("Press Enter to continue...")
            return
        
        if self.task_manager.register_company(name):
            print(f"✅ Company '{name}' registered successfully!")
        else:
            print("❌ Company name already exists!")
        
        input("Press Enter to continue...")
    
    def create_user(self):
        """Create a new user"""
        self.clear_screen()
        self.print_header("CREATE USER")
        
        # Show companies
        companies = self.task_manager.get_companies()
        if not companies:
            print("❌ No companies available! Please register a company first.")
            input("Press Enter to continue...")
            return
        
        print("Available companies:")
        for i, company in enumerate(companies, 1):
            print(f"{i}. {company['name']}")
        
        try:
            company_choice = int(input("\nSelect company (number): ")) - 1
            if company_choice < 0 or company_choice >= len(companies):
                print("❌ Invalid company selection!")
                input("Press Enter to continue...")
                return
        except ValueError:
            print("❌ Please enter a valid number!")
            input("Press Enter to continue...")
            return
        
        selected_company = companies[company_choice]
        
        print(f"\nCreating user for company: {selected_company['name']}")
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()
        
        print("\nSelect role:")
        print("1. Admin")
        print("2. Manager") 
        print("3. Employee")
        
        try:
            role_choice = int(input("Enter choice (1-3): "))
            roles = ["Admin", "Manager", "Employee"]
            if role_choice < 1 or role_choice > 3:
                print("❌ Invalid role selection!")
                input("Press Enter to continue...")
                return
            role = roles[role_choice - 1]
        except ValueError:
            print("❌ Please enter a valid number!")
            input("Press Enter to continue...")
            return
        
        if not username or not password:
            print("❌ Username and password cannot be empty!")
            input("Press Enter to continue...")
            return
        
        if self.task_manager.create_user(username, password, role, selected_company['id']):
            print(f"✅ User '{username}' created successfully as {role}!")
        else:
            print("❌ Username already exists!")
        
        input("Press Enter to continue...")
    
    def assign_task(self):
        """Assign task to user"""
        self.clear_screen()
        self.print_header("ASSIGN TASK")
        
        user = self.task_manager.get_current_user()
        users = self.task_manager.get_company_users(user['company_id'])
        
        if not users:
            print("❌ No users available in your company!")
            input("Press Enter to continue...")
            return
        
        print("Available users:")
        for i, u in enumerate(users, 1):
            print(f"{i}. {u['username']} ({u['role']})")
        
        try:
            user_choice = int(input("\nSelect user to assign task (number): ")) - 1
            if user_choice < 0 or user_choice >= len(users):
                print("❌ Invalid user selection!")
                input("Press Enter to continue...")
                return
        except ValueError:
            print("❌ Please enter a valid number!")
            input("Press Enter to continue...")
            return
        
        selected_user = users[user_choice]
        
        print(f"\nAssigning task to: {selected_user['username']}")
        title = input("Enter task title: ").strip()
        description = input("Enter task description: ").strip()
        
        if not title:
            print("❌ Task title cannot be empty!")
            input("Press Enter to continue...")
            return
        
        if self.task_manager.assign_task(title, description, selected_user['id']):
            print(f"✅ Task '{title}' assigned to {selected_user['username']}!")
        else:
            print("❌ Failed to assign task!")
        
        input("Press Enter to continue...")
    
    def view_all_tasks(self):
        """View all tasks (Admin only)"""
        self.clear_screen()
        self.print_header("ALL TASKS")
        
        tasks = self.task_manager.view_all_tasks()
        
        if not tasks:
            print("No tasks found.")
        else:
            print(f"Total tasks: {len(tasks)}\n")
            for task in tasks:
                status_icon = "✅" if task['status'] == 'Completed' else "🔄" if task['status'] == 'In Progress' else "⏳"
                print(f"{status_icon} [{task['status']}] {task['title']}")
                print(f"   Assigned to: {task['assigned_to'] or 'Unassigned'}")
                print(f"   Description: {task['description']}")
                print(f"   Created: {task['created_at']}")
                print(f"   Updated: {task['updated_at']}")
                print("-" * 50)
        
        input("\nPress Enter to continue...")
    
    def view_task_statistics(self):
        """View task statistics (Admin only)"""
        self.clear_screen()
        self.print_header("TASK STATISTICS")
        
        tasks = self.task_manager.view_all_tasks()
        
        if not tasks:
            print("No tasks found.")
        else:
            pending = sum(1 for task in tasks if task['status'] == 'Pending')
            in_progress = sum(1 for task in tasks if task['status'] == 'In Progress')
            completed = sum(1 for task in tasks if task['status'] == 'Completed')
            
            print(f"📊 Task Statistics:")
            print(f"   Total Tasks: {len(tasks)}")
            print(f"   ⏳ Pending: {pending}")
            print(f"   🔄 In Progress: {in_progress}")
            print(f"   ✅ Completed: {completed}")
            print(f"   📈 Completion Rate: {(completed/len(tasks)*100):.1f}%")
        
        input("\nPress Enter to continue...")
    
    def view_my_tasks(self):
        """View tasks assigned to current user"""
        self.clear_screen()
        self.print_header("MY TASKS")
        
        tasks = self.task_manager.view_my_tasks()
        
        if not tasks:
            print("No tasks assigned to you.")
        else:
            print(f"Your tasks: {len(tasks)}\n")
            for task in tasks:
                status_icon = "✅" if task['status'] == 'Completed' else "🔄" if task['status'] == 'In Progress' else "⏳"
                print(f"{status_icon} [ID: {task['id']}] [{task['status']}] {task['title']}")
                print(f"   Description: {task['description']}")
                print(f"   Created: {task['created_at']}")
                print(f"   Updated: {task['updated_at']}")
                print("-" * 50)
        
        input("\nPress Enter to continue...")
    
    def update_my_task_status(self):
        """Update status of user's task"""
        self.clear_screen()
        self.print_header("UPDATE TASK STATUS")
        
        tasks = self.task_manager.view_my_tasks()
        
        if not tasks:
            print("No tasks assigned to you.")
            input("Press Enter to continue...")
            return
        
        print("Your tasks:")
        for i, task in enumerate(tasks, 1):
            status_icon = "✅" if task['status'] == 'Completed' else "🔄" if task['status'] == 'In Progress' else "⏳"
            print(f"{i}. {status_icon} [{task['status']}] {task['title']} (ID: {task['id']})")
        
        try:
            task_choice = int(input("\nSelect task to update (number): ")) - 1
            if task_choice < 0 or task_choice >= len(tasks):
                print("❌ Invalid task selection!")
                input("Press Enter to continue...")
                return
        except ValueError:
            print("❌ Please enter a valid number!")
            input("Press Enter to continue...")
            return
        
        selected_task = tasks[task_choice]
        
        print(f"\nUpdating task: {selected_task['title']}")
        print(f"Current status: {selected_task['status']}")
        print("\nSelect new status:")
        print("1. Pending")
        print("2. In Progress")
        print("3. Completed")
        
        try:
            status_choice = int(input("Enter choice (1-3): "))
            statuses = ["Pending", "In Progress", "Completed"]
            if status_choice < 1 or status_choice > 3:
                print("❌ Invalid status selection!")
                input("Press Enter to continue...")
                return
            new_status = statuses[status_choice - 1]
        except ValueError:
            print("❌ Please enter a valid number!")
            input("Press Enter to continue...")
            return
        
        if self.task_manager.update_task_status(selected_task['id'], new_status):
            print(f"✅ Task status updated to '{new_status}'!")
        else:
            print("❌ Failed to update task status!")
        
        input("Press Enter to continue...")
    
    def run(self):
        """Main application loop"""
        while True:
            if not self.task_manager.is_logged_in():
                if not self.login_screen():
                    continue
            
            user = self.task_manager.get_current_user()
            
            if user['role'] == 'Admin':
                self.admin_menu()
            else:
                self.manager_employee_menu()
            
            self.task_manager.logout()
            
            self.clear_screen()
            print("👋 Goodbye!")
            if input("Do you want to login again? (y/n): ").lower() != 'y':
                break
