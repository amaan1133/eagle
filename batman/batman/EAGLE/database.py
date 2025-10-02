
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
import threading
import time

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "task_management.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = "task_management.db"):
        if hasattr(self, 'initialized'):
            return
        
        self.db_path = db_path
        self.local_lock = threading.RLock()
        self.initialized = True
        self.init_database()

    def get_connection(self):
        """Get a database connection with proper error handling"""
        max_retries = 5
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(
                    self.db_path, 
                    timeout=30.0,
                    check_same_thread=False,
                    isolation_level=None
                )
                conn.execute('PRAGMA journal_mode=DELETE;')  # Changed from WAL to DELETE
                conn.execute('PRAGMA synchronous=NORMAL;')
                conn.execute('PRAGMA temp_store=MEMORY;')
                conn.execute('PRAGMA mmap_size=268435456;')  # 256MB
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                raise e

    def init_database(self):
        """Initialize database with required tables"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Check if tasks table exists and has the new columns
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'start_date' not in columns or 'deadline' not in columns or 'priority' not in columns:
                # Drop and recreate tables with new schema
                cursor.execute("DROP TABLE IF EXISTS task_comments")
                cursor.execute("DROP TABLE IF EXISTS messages")
                cursor.execute("DROP TABLE IF EXISTS tasks")
                cursor.execute("DROP TABLE IF EXISTS users")
                cursor.execute("DROP TABLE IF EXISTS companies")

            # Companies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('Admin', 'Manager', 'Employee')),
                    company_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            ''')

            # Add is_active column to existing users table if it doesn't exist
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'is_active' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")

            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    assigned_to INTEGER NOT NULL,
                    company_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'In Progress', 'Completed')),
                    start_date DATE,
                    deadline DATE,
                    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (assigned_to) REFERENCES users (id),
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            ''')

            # Task Comments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    comment TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    company_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    receiver_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    FOREIGN KEY (receiver_id) REFERENCES users (id)
                )
            ''')

            # Private Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS private_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender_id) REFERENCES users (id),
                    FOREIGN KEY (receiver_id) REFERENCES users (id)
                )
            ''')

            # Reminders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    reminder_date DATE NOT NULL,
                    alert_days_before INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    company_id INTEGER NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')

            # File attachments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    file_type TEXT,
                    uploaded_by INTEGER NOT NULL,
                    upload_type TEXT NOT NULL CHECK (upload_type IN ('task_assignment', 'task_progress')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id),
                    FOREIGN KEY (uploaded_by) REFERENCES users (id)
                )
            ''')

            # Update task_comments table to support unread status
            cursor.execute("PRAGMA table_info(task_comments)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'is_read' not in columns:
                cursor.execute("ALTER TABLE task_comments ADD COLUMN is_read BOOLEAN DEFAULT 0")

            # Push subscriptions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS push_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    endpoint TEXT NOT NULL,
                    p256dh TEXT,
                    auth TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Notifications table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Add telegram_chat_id column to users table if it doesn't exist
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'telegram_chat_id' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN telegram_chat_id TEXT")
            
            # Add mobile_number column to users table if it doesn't exist
            if 'mobile_number' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN mobile_number TEXT")

            conn.commit()
            conn.close()

    def hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password) == password_hash

    # Company methods
    def create_company(self, name: str) -> bool:
        """Create a new company"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO companies (name) VALUES (?)", (name,))
                conn.commit()
                conn.close()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_companies(self) -> List[Dict]:
        """Get all companies"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM companies")
            companies = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
            conn.close()
            return companies

    # User methods
    def create_user(self, username: str, password: str, role: str, company_id: int) -> bool:
        """Create a new user"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                password_hash = self.hash_password(password)
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, company_id) VALUES (?, ?, ?, ?)",
                    (username, password_hash, role, company_id)
                )
                conn.commit()
                conn.close()
                return True
            except sqlite3.IntegrityError:
                return False

    def update_user_telegram_chat_id(self, user_id: int, telegram_chat_id: str) -> bool:
        """Update user's Telegram chat ID"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET telegram_chat_id = ? WHERE id = ?",
                    (telegram_chat_id, user_id)
                )
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                return success
            except sqlite3.Error:
                return False
    
    def set_user_telegram_chat_id_by_username(self, username: str, telegram_chat_id: str) -> bool:
        """Set Telegram chat ID for user by username"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET telegram_chat_id = ? WHERE username = ?",
                    (telegram_chat_id, username)
                )
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                print(f"✅ Updated Telegram chat ID for {username}: {telegram_chat_id}")
                return success
            except sqlite3.Error as e:
                print(f"❌ Error updating chat ID: {e}")
                return False

    def authenticate_user(self, identifier: str, password: str) -> Optional[Dict]:
        """Authenticate user with username or mobile number and return user info"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, role, company_id, password_hash, is_active, mobile_number FROM users WHERE username = ? OR mobile_number = ?",
                (identifier, identifier)
            )
            user = cursor.fetchone()
            conn.close()

            if user and self.verify_password(password, user[4]):
                # Check if user is active
                is_active = user[5] if len(user) > 5 else True
                if not is_active:
                    return None  # Don't allow login for deactivated users
                
                return {
                    "id": user[0],
                    "username": user[1],
                    "role": user[2],
                    "company_id": user[3],
                    "mobile_number": user[6]
                }
            return None

    def get_users_by_company(self, company_id: int) -> List[Dict]:
        """Get all users in a company"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, role FROM users WHERE company_id = ?",
                (company_id,)
            )
            users = [{"id": row[0], "username": row[1], "role": row[2]} for row in cursor.fetchall()]
            conn.close()
            return users

    # Task methods
    def create_task(self, title: str, description: str, assigned_to: int, company_id: int, 
                   start_date: str = None, deadline: str = None, priority: str = 'Medium') -> bool:
        """Create a new task"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO tasks (title, description, assigned_to, company_id, start_date, deadline, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (title, description, assigned_to, company_id, start_date, deadline, priority)
                )
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                return False

    def get_tasks_by_company(self, company_id: int) -> List[Dict]:
        """Get all tasks for a company, sorted by deadline (closest first)"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.title, t.description, t.status, t.created_at, t.updated_at,
                       u.username, t.start_date, t.deadline, t.priority, t.assigned_to
                FROM tasks t
                LEFT JOIN users u ON t.assigned_to = u.id
                WHERE t.company_id = ?
                ORDER BY 
                    CASE 
                        WHEN t.deadline IS NULL THEN 1 
                        ELSE 0 
                    END,
                    t.deadline ASC,
                    t.created_at DESC
            ''', (company_id,))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                    "assigned_to_name": row[6],
                    "start_date": row[7],
                    "deadline": row[8],
                    "priority": row[9],
                    "assigned_to": row[10]
                })
            conn.close()
            return tasks

    def get_user_tasks(self, user_id: int, company_id: int) -> List[Dict]:
        """Get tasks assigned to a specific user"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.title, t.description, t.status, t.created_at, t.updated_at,
                       u.username, t.start_date, t.deadline, t.priority
                FROM tasks t
                LEFT JOIN users u ON t.assigned_to = u.id
                WHERE t.assigned_to = ? AND t.company_id = ?
                ORDER BY t.created_at DESC
            ''', (user_id, company_id))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                    "assigned_to": row[6],
                    "start_date": row[7],
                    "deadline": row[8],
                    "priority": row[9]
                })
            conn.close()
            return tasks

    def update_task_status(self, task_id: int, status: str, user_id: int) -> bool:
        """Update task status (only if task belongs to user and not already completed)"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # First check if task is already completed - prevent further changes
                cursor.execute('''
                    SELECT status FROM tasks 
                    WHERE id = ? AND assigned_to = ?
                ''', (task_id, user_id))
                result = cursor.fetchone()
                
                if not result:
                    conn.close()
                    return False
                
                current_status = result[0]
                if current_status == 'Completed':
                    # Task is already completed, no further changes allowed
                    conn.close()
                    return False
                
                # Update status only if task is not completed
                cursor.execute('''
                    UPDATE tasks 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ? AND assigned_to = ? AND status != 'Completed'
                ''', (status, task_id, user_id))

                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
            except sqlite3.Error:
                return False

    def admin_update_task(self, task_id: int, title: str, description: str, assigned_to: int, 
                         start_date: str = None, deadline: str = None, priority: str = 'Medium', 
                         status: str = None, company_id: int = None) -> bool:
        """Update task (Admin only)"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Build update query dynamically based on provided fields
                update_fields = []
                values = []
                
                if title:
                    update_fields.append("title = ?")
                    values.append(title)
                if description is not None:
                    update_fields.append("description = ?")
                    values.append(description)
                if assigned_to:
                    update_fields.append("assigned_to = ?")
                    values.append(assigned_to)
                if start_date is not None:
                    update_fields.append("start_date = ?")
                    values.append(start_date)
                if deadline is not None:
                    update_fields.append("deadline = ?")
                    values.append(deadline)
                if priority:
                    update_fields.append("priority = ?")
                    values.append(priority)
                if status:
                    update_fields.append("status = ?")
                    values.append(status)
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
                if company_id:
                    query += " AND company_id = ?"
                    values.extend([task_id, company_id])
                else:
                    values.append(task_id)
                
                cursor.execute(query, values)
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
            except sqlite3.Error as e:
                print(f"Error updating task: {e}")
                return False

    def admin_delete_task(self, task_id: int, company_id: int) -> bool:
        """Delete task (Admin only)"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Delete task comments first
                cursor.execute("DELETE FROM task_comments WHERE task_id = ?", (task_id,))
                
                # Delete file attachments
                cursor.execute("DELETE FROM file_attachments WHERE task_id = ?", (task_id,))
                
                # Delete the task
                cursor.execute("DELETE FROM tasks WHERE id = ? AND company_id = ?", (task_id, company_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
            except sqlite3.Error as e:
                print(f"Error deleting task: {e}")
                return False

    # Message methods
    def create_message(self, user_id, company_id, message, receiver_id=None):
        """Create a new message"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO messages (user_id, company_id, message, receiver_id)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, company_id, message, receiver_id))
                conn.commit()
                message_id = cursor.lastrowid
                conn.close()
                return message_id
            except sqlite3.Error as e:
                print(f"Error creating message: {e}")
                conn.close()
                return None

    def create_private_message(self, sender_id, receiver_id, message):
        """Create a private message between users"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO private_messages (sender_id, receiver_id, message)
                    VALUES (?, ?, ?)
                ''', (sender_id, receiver_id, message))
                conn.commit()
                message_id = cursor.lastrowid
                conn.close()
                return message_id
            except sqlite3.Error as e:
                print(f"Error creating private message: {e}")
                conn.close()
                return None

    def get_company_messages(self, company_id, limit=50):
        """Get messages for a company"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.id, m.message, m.timestamp, u.username, u.id as user_id, m.receiver_id
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.company_id = ? AND m.receiver_id IS NULL
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', (company_id, limit))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'message': row[1],
                    'timestamp': row[2],
                    'username': row[3],
                    'user_id': row[4],
                    'receiver_id': row[5]
                })
            
            conn.close()
            return messages[::-1]  # Reverse to show oldest first

    def get_all_company_messages(self, company_id=None, limit=50):
        """Get all messages for admin view"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            if company_id:
                cursor.execute('''
                    SELECT m.id, m.message, m.timestamp, u.username, u.id as user_id, 
                           c.name as company_name, r.username as receiver_username
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    JOIN companies c ON m.company_id = c.id
                    LEFT JOIN users r ON m.receiver_id = r.id
                    WHERE m.company_id = ?
                    ORDER BY m.timestamp DESC
                    LIMIT ?
                ''', (company_id, limit))
            else:
                cursor.execute('''
                    SELECT m.id, m.message, m.timestamp, u.username, u.id as user_id, 
                           c.name as company_name, r.username as receiver_username
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    JOIN companies c ON m.company_id = c.id
                    LEFT JOIN users r ON m.receiver_id = r.id
                    ORDER BY m.timestamp DESC
                    LIMIT ?
                ''', (limit,))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'message': row[1],
                    'timestamp': row[2],
                    'username': row[3],
                    'user_id': row[4],
                    'company_name': row[5],
                    'receiver_username': row[6]
                })
            
            conn.close()
            return messages[::-1]

    def get_private_messages(self, user1_id, user2_id, limit=50):
        """Get private messages between two users"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pm.id, pm.message, pm.timestamp, 
                       s.username as sender_name, s.id as sender_id,
                       r.username as receiver_name, r.id as receiver_id
                FROM private_messages pm
                JOIN users s ON pm.sender_id = s.id
                JOIN users r ON pm.receiver_id = r.id
                WHERE (pm.sender_id = ? AND pm.receiver_id = ?) 
                   OR (pm.sender_id = ? AND pm.receiver_id = ?)
                ORDER BY pm.timestamp DESC
                LIMIT ?
            ''', (user1_id, user2_id, user2_id, user1_id, limit))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'message': row[1],
                    'timestamp': row[2],
                    'sender_name': row[3],
                    'sender_id': row[4],
                    'receiver_name': row[5],
                    'receiver_id': row[6]
                })

            conn.close()
            return messages[::-1]

    def get_all_private_messages_for_admin(self, limit=100):
        """Get all private messages across all users for admin monitoring"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pm.id, pm.message, pm.timestamp, 
                       s.username as sender_name, s.id as sender_id,
                       r.username as receiver_name, r.id as receiver_id,
                       sc.name as sender_company, rc.name as receiver_company
                FROM private_messages pm
                JOIN users s ON pm.sender_id = s.id
                JOIN users r ON pm.receiver_id = r.id
                JOIN companies sc ON s.company_id = sc.id
                JOIN companies rc ON r.company_id = rc.id
                ORDER BY pm.timestamp DESC
                LIMIT ?
            ''', (limit,))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'message': row[1],
                    'timestamp': row[2],
                    'sender_name': row[3],
                    'sender_id': row[4],
                    'receiver_name': row[5],
                    'receiver_id': row[6],
                    'sender_company': row[7],
                    'receiver_company': row[8]
                })
            
            conn.close()
            return messages[::-1]

    def get_private_messages_with_admin_filter(self, user_id, is_admin=False, limit=50):
        """Get private messages based on user role - admin sees all admin chats, users only see their own admin chats"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if is_admin:
                # Admin sees all private messages
                cursor.execute('''
                    SELECT pm.id, pm.message, pm.timestamp, 
                           s.username as sender_name, s.id as sender_id,
                           r.username as receiver_name, r.id as receiver_id
                    FROM private_messages pm
                    JOIN users s ON pm.sender_id = s.id
                    JOIN users r ON pm.receiver_id = r.id
                    ORDER BY pm.timestamp DESC
                    LIMIT ?
                ''', (limit,))
            else:
                # Regular users only see admin chats they were involved in
                cursor.execute('''
                    SELECT pm.id, pm.message, pm.timestamp, 
                           s.username as sender_name, s.id as sender_id,
                           r.username as receiver_name, r.id as receiver_id
                    FROM private_messages pm
                    JOIN users s ON pm.sender_id = s.id
                    JOIN users r ON pm.receiver_id = r.id
                    WHERE ((pm.sender_id = ? AND r.role = 'Admin') OR 
                           (pm.receiver_id = ? AND s.role = 'Admin'))
                    ORDER BY pm.timestamp DESC
                    LIMIT ?
                ''', (user_id, user_id, limit,))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'message': row[1],
                    'timestamp': row[2],
                    'sender_name': row[3],
                    'sender_id': row[4],
                    'receiver_name': row[5],
                    'receiver_id': row[6]
                })
            
            conn.close()
            return messages[::-1]

    def get_all_users(self):
        """Get all users across all companies (Admin only)"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.username, u.role, c.name as company_name, u.company_id, u.is_active, u.mobile_number
                FROM users u
                JOIN companies c ON u.company_id = c.id
                ORDER BY c.name, u.username
            ''')
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    "id": row[0],
                    "username": row[1],
                    "role": row[2],
                    "company_name": row[3],
                    "company_id": row[4],
                    "is_active": row[5] if len(row) > 5 else True,
                    "mobile_number": row[6] if len(row) > 6 else None
                })
            conn.close()
            return users

    def deactivate_user(self, user_id: int, admin_company_id: int = None) -> bool:
        """Deactivate a user (Admin only)"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Admin can deactivate users from any company, but let's add a check
                if admin_company_id:
                    cursor.execute("UPDATE users SET is_active = 0 WHERE id = ? AND company_id = ?", 
                                 (user_id, admin_company_id))
                else:
                    cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
                
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
            except sqlite3.Error:
                return False

    def reactivate_user(self, user_id: int, admin_company_id: int = None) -> bool:
        """Reactivate a user (Admin only)"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                if admin_company_id:
                    cursor.execute("UPDATE users SET is_active = 1 WHERE id = ? AND company_id = ?", 
                                 (user_id, admin_company_id))
                else:
                    cursor.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
                
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
            except sqlite3.Error:
                return False

    def delete_user(self, user_id: int, admin_company_id: int = None) -> bool:
        """Delete a user permanently (Admin only) - Use with caution"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # First, get user info to check if they have tasks
                cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
                user = cursor.fetchone()
                if not user:
                    conn.close()
                    return False
                
                # Check if user has tasks assigned
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = ?", (user_id,))
                task_count = cursor.fetchone()[0]
                
                if task_count > 0:
                    # Don't delete if user has tasks - suggest deactivation instead
                    conn.close()
                    return False
                
             
                cursor.execute("DELETE FROM task_comments WHERE user_id = ?", (user_id,))
                
               
                cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM private_messages WHERE sender_id = ? OR receiver_id = ?", 
                             (user_id, user_id))
                
                
                cursor.execute("DELETE FROM push_subscriptions WHERE user_id = ?", (user_id,))
                
                # Delete user's notifications
                cursor.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
                
                # Finally delete the user
                if admin_company_id:
                    cursor.execute("DELETE FROM users WHERE id = ? AND company_id = ?", 
                                 (user_id, admin_company_id))
                else:
                    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
            except sqlite3.Error as e:
                print(f"Error deleting user: {e}")
                return False

    # Task Comments methods
    def add_task_comment(self, task_id: int, user_id: int, comment: str) -> bool:
        """Add a comment to a task"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO task_comments (task_id, user_id, comment) VALUES (?, ?, ?)",
                    (task_id, user_id, comment)
                )
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                return False

    def get_task_comments(self, task_id: int, user_id: int = None) -> List[Dict]:
        """Get all comments for a task"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tc.id, tc.comment, tc.created_at, u.username, tc.user_id, tc.is_read
                FROM task_comments tc
                JOIN users u ON tc.user_id = u.id
                WHERE tc.task_id = ?
                ORDER BY tc.created_at DESC
            ''', (task_id,))

            comments = []
            for row in cursor.fetchall():
                comments.append({
                    "id": row[0],
                    "comment": row[1],
                    "created_at": row[2],
                    "username": row[3],
                    "user_id": row[4],
                    "is_read": row[5]
                })
            conn.close()
            
            # Mark comments as read for the viewing user
            if user_id:
                self.mark_comments_as_read(task_id, user_id)
            
            return comments

    def mark_comments_as_read(self, task_id: int, user_id: int) -> bool:
        """Mark comments as read for a user"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_comments SET is_read = 1 
                    WHERE task_id = ? AND user_id != ?
                ''', (task_id, user_id))
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                return False

    def get_unread_comments_count(self, user_id: int, company_id: int) -> int:
        """Get count of unread comments for user's tasks"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM task_comments tc
                JOIN tasks t ON tc.task_id = t.id
                WHERE (t.assigned_to = ? OR EXISTS (
                    SELECT 1 FROM users u WHERE u.id = ? AND u.role = 'Admin' AND u.company_id = ?
                ))
                AND tc.user_id != ? 
                AND tc.is_read = 0
                AND t.company_id = ?
            ''', (user_id, user_id, company_id, user_id, company_id))
            
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0

    # File attachment methods
    def save_file_attachment(self, task_id: int, filename: str, original_filename: str, 
                           file_path: str, file_size: int, file_type: str, 
                           uploaded_by: int, upload_type: str) -> bool:
        """Save file attachment info to database"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO file_attachments 
                    (task_id, filename, original_filename, file_path, file_size, file_type, uploaded_by, upload_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (task_id, filename, original_filename, file_path, file_size, file_type, uploaded_by, upload_type))
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error as e:
                print(f"Error saving file attachment: {e}")
                return False

    def get_task_attachments(self, task_id: int) -> List[Dict]:
        """Get all file attachments for a task"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT fa.id, fa.filename, fa.original_filename, fa.file_path, fa.file_size, 
                       fa.file_type, fa.upload_type, fa.created_at, u.username
                FROM file_attachments fa
                JOIN users u ON fa.uploaded_by = u.id
                WHERE fa.task_id = ?
                ORDER BY fa.created_at DESC
            ''', (task_id,))

            attachments = []
            for row in cursor.fetchall():
                attachments.append({
                    "id": row[0],
                    "filename": row[1],
                    "original_filename": row[2],
                    "file_path": row[3],
                    "file_size": row[4],
                    "file_type": row[5],
                    "upload_type": row[6],
                    "created_at": row[7],
                    "uploaded_by": row[8]
                })
            conn.close()
            return attachments

    def delete_file_attachment(self, attachment_id: int, user_id: int) -> bool:
        """Delete a file attachment"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Get file path first
                cursor.execute("SELECT file_path FROM file_attachments WHERE id = ? AND uploaded_by = ?", 
                             (attachment_id, user_id))
                result = cursor.fetchone()
                
                if result:
                    import os
                    file_path = result[0]
                    
                    # Delete from database
                    cursor.execute("DELETE FROM file_attachments WHERE id = ? AND uploaded_by = ?", 
                                 (attachment_id, user_id))
                    
                    # Delete physical file
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    conn.commit()
                    conn.close()
                    return True
                
                conn.close()
                return False
            except sqlite3.Error as e:
                print(f"Error deleting file attachment: {e}")
                return False

    # Reminders methods
    def create_reminder(self, title: str, description: str, reminder_date: str, 
                       alert_days_before: int, company_id: int, created_by: int) -> bool:
        """Create a new reminder"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO reminders (title, description, reminder_date, alert_days_before, company_id, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (title, description, reminder_date, alert_days_before, company_id, created_by))
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error as e:
                print(f"Error creating reminder: {e}")
                return False

    def get_reminders(self, company_id: int) -> List[Dict]:
        """Get all active reminders for a company"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.title, r.description, r.reminder_date, r.alert_days_before, 
                       r.created_at, u.username
                FROM reminders r
                JOIN users u ON r.created_by = u.id
                WHERE r.company_id = ? AND r.is_active = 1
                ORDER BY r.reminder_date ASC
            ''', (company_id,))
            
            reminders = []
            for row in cursor.fetchall():
                reminders.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'reminder_date': row[3],
                    'alert_days_before': row[4],
                    'created_at': row[5],
                    'created_by': row[6]
                })
            conn.close()
            return reminders

    def get_upcoming_reminders(self, company_id: int) -> List[Dict]:
        """Get reminders that need alerts (within alert days)"""
        with self.local_lock:
            from datetime import date, timedelta
            
            conn = self.get_connection()
            cursor = conn.cursor()
            today = date.today()
            
            cursor.execute('''
                SELECT r.id, r.title, r.description, r.reminder_date, r.alert_days_before
                FROM reminders r
                WHERE r.company_id = ? AND r.is_active = 1
                AND DATE(r.reminder_date) <= DATE(?, '+' || r.alert_days_before || ' days')
                AND DATE(r.reminder_date) >= DATE(?)
            ''', (company_id, today.isoformat(), today.isoformat()))
            
            reminders = []
            for row in cursor.fetchall():
                reminders.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'reminder_date': row[3],
                    'alert_days_before': row[4]
                })
            conn.close()
            return reminders

    def delete_reminder(self, reminder_id: int, company_id: int) -> bool:
        """Delete a reminder (soft delete by setting is_active to false)"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE reminders SET is_active = 0
                    WHERE id = ? AND company_id = ?
                ''', (reminder_id, company_id))
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
            except sqlite3.Error:
                return False

    def save_push_subscription(self, user_id: int, subscription: dict) -> bool:
        """Save push notification subscription"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Remove existing subscription for this user
                cursor.execute("DELETE FROM push_subscriptions WHERE user_id = ?", (user_id,))
                
                # Add new subscription
                cursor.execute('''
                    INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, subscription.get('endpoint'), 
                      subscription.get('keys', {}).get('p256dh'),
                      subscription.get('keys', {}).get('auth')))
                
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error as e:
                print(f"Error saving push subscription: {e}")
                return False

    def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        """Get push subscriptions for user"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?
            ''', (user_id,))
            
            subscriptions = []
            for row in cursor.fetchall():
                subscriptions.append({
                    'endpoint': row[0],
                    'keys': {
                        'p256dh': row[1],
                        'auth': row[2]
                    }
                })
            conn.close()
            return subscriptions

    def store_notification(self, user_id: int, message: str) -> bool:
        """Store notification in database"""
        with self.local_lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notifications (user_id, message)
                    VALUES (?, ?)
                ''', (user_id, message))
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                return False

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Get task by ID"""
        with self.local_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, description, assigned_to, status
                FROM tasks WHERE id = ?
            ''', (task_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'title': result[1],
                    'description': result[2],
                    'assigned_to': result[3],
                    'status': result[4]
                }
            return None

    def __del__(self):
        pass  
