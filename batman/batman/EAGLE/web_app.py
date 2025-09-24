from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from task_manager import TaskManager
from database import Database
import json
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
CORS(app, supports_credentials=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'doc', 'docx', 'txt', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users and their rooms
active_users = {}

def send_telegram_notification(user_id, message):
    """Send Telegram notification to user using their telegram_chat_id"""
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        # Get user's telegram_chat_id and username
        cursor.execute("SELECT telegram_chat_id, username FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            print(f"⚠️ User not found for user_id: {user_id}")
            return False

        telegram_chat_id, username = result
        
        if not telegram_chat_id:
            print(f"⚠️ No Chat ID configured for user: {username}. User needs to set up Chat ID in settings.")
            return False
        
        # Get bot credentials from environment variables
        import os
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', "7653297508:AAE_sfu893LJ-D5Z5xtr_sjy-XEJvvf7haQ")
        bot_username = os.getenv('TELEGRAM_BOT_USERNAME', "taskmanager_eagle_bot")

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Create a clean notification message
        notification_text = f"🦅 *Eagle Task Manager*\n\n*Task Notification for:* {username}\n\n*Message:* {message}"
        
        data = {
            'chat_id': telegram_chat_id,
            'text': notification_text,
            'parse_mode': 'Markdown'
        }

        print(f"📤 Sending Telegram notification to {username} (chat_id: {telegram_chat_id})")
        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 200:
            print(f"✅ Telegram notification sent successfully to {username}")
            return True
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            print(f"❌ Failed to send Telegram notification to {username}")
            print(f"Error: {error_data}")
            return False

    except Exception as e:
        print(f"💥 Error sending Telegram notification: {e}")
        return False

def send_bot_setup_message(mobile_number, username, bot_token, bot_username):
    """Send a setup message to user's mobile number to help them start the bot"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        bot_start_link = f"https://t.me/{bot_username}?start=user_{mobile_number}"
        
        setup_message = f"🤖 *Eagle Task Manager Bot Setup*\n\nHi {username}!\n\n📲 To receive task notifications directly on your phone:\n\n1️⃣ Click this link: {bot_start_link}\n2️⃣ Or search @{bot_username} on Telegram\n3️⃣ Type /start to activate notifications\n\n✅ Once activated, you'll receive all task notifications directly!"
        
        data = {
            'chat_id': mobile_number,
            'text': setup_message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print(f"📱 Setup message sent to {username} at {mobile_number}")
        else:
            print(f"⚠️ Could not send setup message to {mobile_number}")
            
    except Exception as e:
        print(f"💥 Error sending setup message: {e}")

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('mobile_number') or data.get('username')  # Accept both for compatibility
        password = data.get('password')
        company_id = data.get('company_id')

        # Universal admin login
        if username == 'admin' and password == 'admin@277213':
            session['user_id'] = 1
            session['username'] = 'admin'
            session['role'] = 'Admin'
            session['company_id'] = int(company_id)

            # AI Greeting for universal admin
            tm = TaskManager()
            tm.current_user = {
                'id': 1,
                'username': 'admin',
                'role': 'Admin',
                'company_id': int(company_id)
            }
            tasks = tm.view_all_tasks()
            pending = len([t for t in tasks if t['status'] == 'Pending'])
            in_progress = len([t for t in tasks if t['status'] == 'In Progress'])
            completed = len([t for t in tasks if t['status'] == 'Completed'])

            ai_message = f"Namaste Nigam Ji! I am your AI Eagle 🦅. Current status: {pending} pending, {in_progress} in progress, {completed} completed tasks."

            user = {
                'id': 1,
                'username': 'admin',
                'role': 'Admin',
                'company_id': int(company_id)
            }
            return jsonify({'success': True, 'user': user, 'ai_message': ai_message})

        tm = TaskManager()
        if tm.login(username, password):
            user = tm.get_current_user()
            # Verify user belongs to selected company
            if user['company_id'] == int(company_id):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['company_id'] = user['company_id']

                # AI Greeting for admin
                ai_message = ""
                if user['role'] == 'Admin':
                    tasks = tm.view_all_tasks()
                    pending = len([t for t in tasks if t['status'] == 'Pending'])
                    in_progress = len([t for t in tasks if t['status'] == 'In Progress'])
                    completed = len([t for t in tasks if t['status'] == 'Completed'])

                    ai_message = f"Namaste Nigam Ji! I am your AI Eagle 🦅. Current status: {pending} pending, {in_progress} in progress, {completed} completed tasks."

                return jsonify({'success': True, 'user': user, 'ai_message': ai_message})
            else:
                return jsonify({'success': False, 'message': 'Invalid company selection'})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'})

    # Get companies for login form
    db = Database()
    companies = db.get_companies()
    return render_template('login.html', companies=companies)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/companies')
def get_companies():
    db = Database()
    companies = db.get_companies()
    return jsonify(companies)

@app.route('/api/register_company', methods=['POST'])
def register_company():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    tm = TaskManager()
    tm.current_user = {
        'id': session['user_id'],
        'username': session['username'],
        'role': session['role'],
        'company_id': session['company_id']
    }

    success = tm.register_company(data['name'])

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Company name already exists or limit reached'})

@app.route('/api/create_user', methods=['POST'])
def create_user():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'})

        # Validate required fields
        required_fields = ['username', 'password', 'role', 'company_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'})

        tm = TaskManager()
        tm.current_user = {
            'id': session['user_id'],
            'username': session['username'],
            'role': session['role'],
            'company_id': session['company_id']
        }

        success = tm.create_user(
            data['username'],
            data['password'],
            data['role'],
            int(data['company_id'])
        )

        if success:
            return jsonify({'success': True, 'message': 'User created successfully'})
        else:
            return jsonify({'success': False, 'message': 'Username already exists or invalid data'})

    except Exception as e:
        print(f"Error creating user: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@app.route('/api/users')
def get_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    db = Database()
    company_id = session['company_id']
    users = db.get_users_by_company(company_id)
    return jsonify(users)

@app.route('/api/tasks')
def get_tasks():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    tm = TaskManager()
    tm.current_user = {
        'id': session['user_id'],
        'username': session['username'],
        'role': session['role'],
        'company_id': session['company_id']
    }

    if session['role'] == 'Admin':
        tasks = tm.view_all_tasks()
    else:
        tasks = tm.view_my_tasks()

    return jsonify(tasks)

@app.route('/api/create_task', methods=['POST'])
def create_task():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    tm = TaskManager()
    tm.current_user = {
        'id': session['user_id'],
        'username': session['username'],
        'role': session['role'],
        'company_id': session['company_id']
    }

    success = tm.assign_task(
        data['title'],
        data['description'],
        data['assigned_to'],
        data.get('start_date'),
        data.get('deadline'),
        data.get('priority', 'Medium')
    )

    if success:
        # Send notification to assigned user
        send_notification(data['assigned_to'], f"New task assigned: {data['title']}")
        # Send Telegram notification
        notification_message = f"📋 *New Task Assigned*\n\n*Title:* {data['title']}\n*Description:* {data['description']}\n*Priority:* {data.get('priority', 'Medium')}"
        if data.get('deadline'):
            notification_message += f"\n*Deadline:* {data['deadline']}"
        send_telegram_notification(data['assigned_to'], notification_message)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to create task'})

@app.route('/api/admin/update_task/<int:task_id>', methods=['PUT'])
def admin_update_task(task_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    db = Database()

    success = db.admin_update_task(
        task_id,
        data.get('title'),
        data.get('description'),
        data.get('assigned_to'),
        data.get('start_date'),
        data.get('deadline'),
        data.get('priority', 'Medium'),
        data.get('status'),
        session['company_id']
    )

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to update task'})

@app.route('/api/admin/delete_task/<int:task_id>', methods=['DELETE'])
def admin_delete_task(task_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    db = Database()
    success = db.admin_delete_task(task_id, session['company_id'])

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete task'})

@app.route('/api/update_task_status', methods=['POST'])
def update_task_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    tm = TaskManager()
    tm.current_user = {
        'id': session['user_id'],
        'username': session['username'],
        'role': session['role'],
        'company_id': session['company_id']
    }

    success = tm.update_task_status(data['task_id'], data['status'])

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to update task'})

@app.route('/api/task_comments/<int:task_id>')
def get_task_comments(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    db = Database()
    comments = db.get_task_comments(task_id, session['user_id'])
    return jsonify(comments)

@app.route('/api/add_task_comment', methods=['POST'])
def add_task_comment():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    db = Database()

    success = db.add_task_comment(
        data['task_id'],
        session['user_id'],
        data['comment']
    )

    if success:
        # Get task info to find who to notify
        db_conn = Database()
        task = db_conn.get_task_by_id(data['task_id'])
        if task:
            # Send notification to task assignee if not the commenter
            if task['assigned_to'] != session['user_id']:
                send_notification(task['assigned_to'], f"New comment on task: {task['title']}")

        # Emit notification to task assignee
        socketio.emit('new_comment_notification', {
            'task_id': data['task_id'],
            'message': f"New comment on task from {session['username']}"
        }, room=f"company_{session['company_id']}")

        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to add comment'})

@app.route('/api/unread_comments_count')
def get_unread_comments_count():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    db = Database()
    count = db.get_unread_comments_count(session['user_id'], session['company_id'])
    return jsonify({'count': count})

@app.route('/api/upload_task_file/<int:task_id>', methods=['POST'])
def upload_task_file(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'})

    file = request.files['file']
    upload_type = request.form.get('upload_type', 'task_progress')

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})

    if file and allowed_file(file.filename):
        try:
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            # Save file
            file.save(file_path)
            file_size = os.path.getsize(file_path)

            # Save to database
            db = Database()
            success = db.save_file_attachment(
                task_id,
                unique_filename,
                original_filename,
                file_path,
                file_size,
                file_extension,
                session['user_id'],
                upload_type
            )

            if success:
                return jsonify({'success': True, 'filename': original_filename})
            else:
                # Remove file if database save failed
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({'success': False, 'message': 'Failed to save file info'})

        except Exception as e:
            return jsonify({'success': False, 'message': f'Error uploading file: {str(e)}'})

    return jsonify({'success': False, 'message': 'Invalid file type. Only PDF, Excel, Word, and text files are allowed.'})

@app.route('/api/task_attachments/<int:task_id>')
def get_task_attachments(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    db = Database()
    attachments = db.get_task_attachments(task_id)
    return jsonify(attachments)

@app.route('/api/download_file/<int:attachment_id>')
def download_file(attachment_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT fa.file_path, fa.original_filename 
        FROM file_attachments fa
        JOIN tasks t ON fa.task_id = t.id
        WHERE fa.id = ? AND (t.assigned_to = ? OR t.company_id = ?)
    ''', (attachment_id, session['user_id'], session['company_id']))

    result = cursor.fetchone()
    conn.close()

    if result:
        file_path, original_filename = result
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename, as_attachment=True, download_name=original_filename)

    return jsonify({'error': 'File not found'}), 404

@app.route('/api/delete_attachment/<int:attachment_id>', methods=['DELETE'])
def delete_attachment(attachment_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    db = Database()
    success = db.delete_file_attachment(attachment_id, session['user_id'])

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete attachment'})

@app.route('/api/reminders')
def get_reminders():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    db = Database()
    reminders = db.get_reminders(session['company_id'])
    return jsonify(reminders)

@app.route('/api/create_reminder', methods=['POST'])
def create_reminder():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    db = Database()

    success = db.create_reminder(
        data['title'],
        data.get('description', ''),
        data['reminder_date'],
        data.get('alert_days_before', 1),
        session['company_id'],
        session['user_id']
    )

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to create reminder'})

@app.route('/api/delete_reminder/<int:reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    db = Database()
    success = db.delete_reminder(reminder_id, session['company_id'])

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete reminder'})

@app.route('/api/upcoming_reminders')
def get_upcoming_reminders():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    db = Database()
    reminders = db.get_upcoming_reminders(session['company_id'])
    return jsonify(reminders)

@app.route('/api/messages')
def get_messages():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    db = Database()

    if session['role'] == 'Admin':
        messages = db.get_all_company_messages(session['company_id'])
    else:
        messages = db.get_company_messages(session['company_id'])

    return jsonify(messages)

@app.route('/api/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    db = Database()

    receiver_id = data.get('receiver_id')

    if receiver_id:
        # Send private message
        message_id = db.create_private_message(
            session['user_id'],
            receiver_id,
            data['message']
        )

        if message_id:
            # Send notification to receiver
            send_notification(receiver_id, f"New message from {session['username']}")

            # Emit to specific user
            socketio.emit('new_private_message', {
                'id': message_id,
                'message': data['message'],
                'sender_name': session['username'],
                'sender_id': session['user_id'],
                'timestamp': datetime.now().isoformat()
            }, room=f"user_{receiver_id}")

            return jsonify({'success': True})
    else:
        # Send company message
        message_id = db.create_message(
            session['user_id'],
            session['company_id'],
            data['message']
        )

        if message_id:
            room = f"company_{session['company_id']}"
            socketio.emit('new_message', {
                'id': message_id,
                'message': data['message'],
                'username': session['username'],
                'timestamp': datetime.now().isoformat(),
                'user_id': session['user_id']
            }, room=room)

            return jsonify({'success': True})

    return jsonify({'success': False, 'message': 'Failed to send message'})

# Socket.IO events
@socketio.on('connect')
def on_connect():
    if 'user_id' in session:
        user_id = session['user_id']
        company_id = session['company_id']
        username = session['username']

        room = f"company_{company_id}"
        join_room(room)

        active_users[request.sid] = {
            'user_id': user_id,
            'username': username,
            'company_id': company_id
        }

        emit('user_joined', {
            'username': username,
            'message': f'{username} joined the chat'
        }, room=room, include_self=False)

@app.route('/api/all_users')
def get_all_users():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    db = Database()
    users = db.get_all_users()
    return jsonify(users)

@app.route('/api/admin/deactivate_user/<int:user_id>', methods=['POST'])
def deactivate_user(user_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    if user_id == session['user_id']:
        return jsonify({'success': False, 'message': 'Cannot deactivate your own account'})

    db = Database()
    success = db.deactivate_user(user_id)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to deactivate user'})

@app.route('/api/admin/reactivate_user/<int:user_id>', methods=['POST'])
def reactivate_user(user_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    db = Database()
    success = db.reactivate_user(user_id)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to reactivate user'})

@app.route('/api/admin/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    if user_id == session['user_id']:
        return jsonify({'success': False, 'message': 'Cannot delete your own account'})

    db = Database()
    success = db.delete_user(user_id)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Cannot delete user with assigned tasks. Please deactivate instead.'})

@app.route('/api/users_by_company/<int:company_id>')
def get_users_by_company(company_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.role, u.is_active, u.created_at
        FROM users u
        WHERE u.company_id = ?
        ORDER BY u.username
    ''', (company_id,))

    users = []
    for row in cursor.fetchall():
        users.append({
            "id": row[0],
            "username": row[1],
            "role": row[2],
            "is_active": row[3] if len(row) > 3 else True,
            "created_at": row[4]
        })
    conn.close()
    return jsonify(users)

@app.route('/api/private_messages/<int:user_id>')
def get_private_messages(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    db = Database()
    if session['role'] == 'Admin':
        # Admin can see all private messages
        messages = db.get_private_messages_with_admin_filter(session['user_id'], is_admin=True)
    else:
        # Regular users only see admin chats they were involved in
        messages = db.get_private_messages_with_admin_filter(session['user_id'], is_admin=False)
    return jsonify(messages)

@app.route('/api/admin/all_messages')
def get_admin_all_messages():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401

    db = Database()
    # Get all messages across all companies for admin
    messages = db.get_all_company_messages(limit=100)
    return jsonify(messages)

@app.route('/api/subscribe_notifications', methods=['POST'])
def subscribe_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    subscription = data.get('subscription')

    db = Database()
    success = db.save_push_subscription(session['user_id'], subscription)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Failed to save subscription'})

@app.route('/api/task_stats')
def get_task_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    tm = TaskManager()
    tm.current_user = {
        'id': session['user_id'],
        'username': session['username'],
        'role': session['role'],
        'company_id': session['company_id']
    }

    if session['role'] == 'Admin':
        tasks = tm.view_all_tasks()
    else:
        tasks = tm.view_my_tasks()

    stats = {
        'total': len(tasks),
        'pending': len([t for t in tasks if t['status'] == 'Pending']),
        'in_progress': len([t for t in tasks if t['status'] == 'In Progress']),
        'completed': len([t for t in tasks if t['status'] == 'Completed']),
        'by_priority': {
            'critical': len([t for t in tasks if t.get('priority') == 'Critical']),
            'high': len([t for t in tasks if t.get('priority') == 'High']),
            'medium': len([t for t in tasks if t.get('priority') == 'Medium']),
            'low': len([t for t in tasks if t.get('priority') == 'Low'])
        }
    }

    return jsonify(stats)

@app.route('/api/telegram_setup_info')
def get_telegram_setup_info():
    """Get Telegram bot setup information"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Get user's mobile number
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT mobile_number, telegram_chat_id FROM users WHERE id = ?", (session['user_id'],))
    result = cursor.fetchone()
    conn.close()
    
    mobile_number = result[0] if result else None
    telegram_chat_id = result[1] if result else None
    
    bot_username = "taskmanager_eagle_bot"
    bot_start_link = f"https://t.me/{bot_username}?start=user_{mobile_number}" if mobile_number else f"https://t.me/{bot_username}"
    
    setup_info = {
        'bot_username': bot_username,
        'bot_start_link': bot_start_link,
        'mobile_number': mobile_number,
        'telegram_chat_id': telegram_chat_id,
        'is_setup_complete': bool(telegram_chat_id),
        'instructions': [
            f"1. Click this link: {bot_start_link}",
            f"2. Or search @{bot_username} on Telegram",
            "3. Type /start to activate notifications",
            "4. You'll start receiving task notifications directly!"
        ]
    }
    
    return jsonify(setup_info)

@app.route('/api/send_telegram_setup', methods=['POST'])
def send_telegram_setup():
    """Send Telegram setup instructions to user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Get user info
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT mobile_number, username FROM users WHERE id = ?", (session['user_id'],))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return jsonify({'success': False, 'message': 'Mobile number not found'})
        
        mobile_number, username = result
        # Get bot credentials from environment variables
        import os
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', "7653297508:AAE_sfu893LJ-D5Z5xtr_sjy-XEJvvf7haQ")
        bot_username = os.getenv('TELEGRAM_BOT_USERNAME', "taskmanager_eagle_bot")
        
        # Send setup message
        send_bot_setup_message(mobile_number, username, bot_token, bot_username)
        
        return jsonify({'success': True, 'message': 'Setup instructions sent to your mobile number'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/chat_id', methods=['GET'])
def get_chat_id():
    """Get current user's Telegram chat ID"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_chat_id FROM users WHERE id = ?", (session['user_id'],))
        result = cursor.fetchone()
        conn.close()
        
        chat_id = result[0] if result and result[0] else None
        return jsonify({'success': True, 'chat_id': chat_id})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/chat_id', methods=['POST'])
def update_chat_id():
    """Update current user's Telegram chat ID"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        chat_id = data.get('chat_id', '').strip()
        
        if not chat_id:
            return jsonify({'success': False, 'message': 'Chat ID is required'})
        
        # Basic validation - should be a number
        if not chat_id.isdigit():
            return jsonify({'success': False, 'message': 'Chat ID should only contain numbers'})
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET telegram_chat_id = ? WHERE id = ?", (chat_id, session['user_id']))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Chat ID updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@socketio.on('join_user_room')
def on_join_user_room():
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")

@socketio.on('disconnect')
def on_disconnect():
    if request.sid in active_users:
        user_info = active_users[request.sid]
        room = f"company_{user_info['company_id']}"

        emit('user_left', {
            'username': user_info['username'],
            'message': f"{user_info['username']} left the chat"
        }, room=room)

        del active_users[request.sid]

def send_notification(user_id, message):
    """Send push notification to user"""
    try:
        db = Database()
        subscriptions = db.get_user_subscriptions(user_id)

        for subscription in subscriptions:
            # Send web push notification
            try:
                import requests
                import json

                payload = {
                    "title": "Eagle Task Manager",
                    "body": message,
                    "icon": "/static/icon-192x192.png",
                    "badge": "/static/badge-72x72.png"
                }

                headers = {
                    'Content-Type': 'application/json',
                    'TTL': '86400'
                }

                # This would require web push library in production
                # For now, we'll store the notification
                db.store_notification(user_id, message)

            except Exception as e:
                print(f"Error sending push notification: {e}")

    except Exception as e:
        print(f"Error in send_notification: {e}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)