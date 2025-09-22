
# Task Management System

A comprehensive CLI-based Task Management System built with Python and SQLite3, featuring multi-company support and role-based access control.

## Features

### 🏢 Multi-Company Support
- Supports up to 7 companies with complete data isolation
- Each company manages its own users and tasks independently

### 👥 Role-Based Access Control
- **Admin**: Can register companies, create users, assign tasks, and view all tasks
- **Manager**: Can view and update status of assigned tasks
- **Employee**: Can view and update status of assigned tasks

### 📋 Task Management
- Create tasks with title, description, and assignment
- Track task status: Pending, In Progress, Completed
- Automatic timestamp tracking (created_at, updated_at)
- Task statistics and reporting

### 🔐 Security
- Password hashing using SHA256
- User authentication and session management
- Role-based permission enforcement

## Quick Start

### 1. Run the Application
```bash
python main.py
```

### 2. Initial Login
- Username: `admin`
- Password: `admin123`

### 3. Setup Sample Data (Optional)
```bash
python setup_sample_data.py
```

## File Structure

```
├── main.py                 # Application entry point
├── database.py            # Database schema and operations
├── task_manager.py        # Core business logic
├── cli_interface.py       # Command-line interface
├── setup_sample_data.py   # Sample data setup script
├── README.md              # This file
└── task_management.db     # SQLite database (created automatically)
```

## Database Schema

### Companies Table
- `id` (Primary Key)
- `name` (Unique)
- `created_at`

### Users Table
- `id` (Primary Key)
- `username` (Unique)
- `password_hash`
- `role` (Admin/Manager/Employee)
- `company_id` (Foreign Key)
- `created_at`

### Tasks Table
- `id` (Primary Key)
- `title`
- `description`
- `assigned_to` (Foreign Key to Users)
- `company_id` (Foreign Key to Companies)
- `status` (Pending/In Progress/Completed)
- `created_at`
- `updated_at`

## Usage Guide

### Admin Operations
1. **Register Company**: Add new companies (max 7)
2. **Create User**: Add users with specific roles to companies
3. **Assign Task**: Create and assign tasks to users
4. **View All Tasks**: Monitor all tasks and their status
5. **View Statistics**: See completion rates and task distribution

### Manager/Employee Operations
1. **View My Tasks**: See all assigned tasks
2. **Update Task Status**: Change task status (Pending → In Progress → Completed)

## Sample Data

After running `setup_sample_data.py`, you can login with:

- **Admin**: `admin` / `admin123`
- **Manager**: `john_manager_techcorp` / `pass123`
- **Employee**: `alice_emp_techcorp` / `pass123`
- **Employee**: `bob_emp_techcorp` / `pass123`

## Technical Requirements

- Python 3.6+
- SQLite3 (included with Python)
- No external dependencies required

## Design Principles

- **Clean Code**: Well-structured, readable Python code
- **Data Isolation**: Complete separation between company data
- **Role-Based Security**: Proper permission enforcement
- **User-Friendly**: Intuitive CLI interface with clear navigation
- **Robust**: Error handling and input validation throughout

## Future Enhancements

- Web interface using Flask/FastAPI
- Task priorities and due dates
- Email notifications
- Task comments and file attachments
- Advanced reporting and analytics
