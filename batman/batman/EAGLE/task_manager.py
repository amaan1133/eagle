
from database import Database
from typing import Optional, Dict

class TaskManager:
    def __init__(self):
        self.db = Database()
        self.current_user: Optional[Dict] = None
    
    def login(self, identifier: str, password: str) -> bool:
        """Login user with username or mobile number"""
        user = self.db.authenticate_user(identifier, password)
        if user:
            self.current_user = user
            return True
        return False
    
    def logout(self):
        """Logout current user"""
        self.current_user = None
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return self.current_user is not None
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current logged in user"""
        return self.current_user
    
    # Admin functions
    def register_company(self, name: str) -> bool:
        """Register a new company (Admin only)"""
        if not self.current_user or self.current_user['role'] != 'Admin':
            return False
        return self.db.create_company(name)
    
    def create_user(self, username: str, password: str, role: str, company_id: int) -> bool:
        """Create a new user (Admin only)"""
        if not self.current_user or self.current_user['role'] != 'Admin':
            return False
        return self.db.create_user(username, password, role, company_id)
    
    def assign_task(self, title: str, description: str, assigned_to: int, 
                   start_date: str = None, deadline: str = None, priority: str = 'Medium') -> bool:
        """Assign task to user (Admin only)"""
        if not self.current_user or self.current_user['role'] != 'Admin':
            return False
        return self.db.create_task(title, description, assigned_to, self.current_user['company_id'], 
                                 start_date, deadline, priority)
    
    def view_all_tasks(self):
        """View all tasks in company (Admin only)"""
        if not self.current_user or self.current_user['role'] != 'Admin':
            return []
        return self.db.get_tasks_by_company(self.current_user['company_id'])
    
    # Manager/Employee functions
    def view_my_tasks(self):
        """View tasks assigned to current user"""
        if not self.current_user:
            return []
        return self.db.get_user_tasks(self.current_user['id'], self.current_user['company_id'])
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """Update task status (Manager/Employee only)"""
        if not self.current_user or self.current_user['role'] == 'Admin':
            return False
        return self.db.update_task_status(task_id, status, self.current_user['id'])

    def admin_update_task(self, task_id: int, title: str = None, description: str = None, 
                         assigned_to: int = None, start_date: str = None, deadline: str = None, 
                         priority: str = None, status: str = None) -> bool:
        """Update task (Admin only)"""
        if not self.current_user or self.current_user['role'] != 'Admin':
            return False
        return self.db.admin_update_task(task_id, title, description, assigned_to, 
                                       start_date, deadline, priority, status, 
                                       self.current_user['company_id'])

    def admin_delete_task(self, task_id: int) -> bool:
        """Delete task (Admin only)"""
        if not self.current_user or self.current_user['role'] != 'Admin':
            return False
        return self.db.admin_delete_task(task_id, self.current_user['company_id'])
    
    # Utility functions
    def get_companies(self):
        """Get all companies"""
        return self.db.get_companies()
    
    def get_company_users(self, company_id: int):
        """Get users in a company"""
        return self.db.get_users_by_company(company_id)
