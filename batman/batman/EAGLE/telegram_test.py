
#!/usr/bin/env python3
"""
Telegram notification testing script
"""

import os
from database import Database
from web_app import send_telegram_notification

def setup_test_chat_ids():
    """Setup test chat IDs for users"""
    db = Database()
    
    # Set your chat ID for testing (replace with actual chat ID)
    test_chat_id = "5776427389"  # Your provided chat ID
    
    # Update simran user with chat ID
    success = db.set_user_telegram_chat_id_by_username("simran", test_chat_id)
    
    if success:
        print("✅ Test chat ID set for simran")
    else:
        print("❌ Failed to set chat ID")

def test_telegram_notification():
    """Test Telegram notification with real user"""
    print("🧪 Testing Telegram notification with registered user...")
    
    # Get user with mobile number (samreen)
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, mobile_number FROM users WHERE mobile_number IS NOT NULL LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        user_id, username, mobile_number = result
        message = f"📋 *Test Task Assignment*\n\n*Title:* Sample Task\n*Description:* This is a test notification to verify Telegram integration\n*Priority:* High"
        print(f"📱 Testing notification for user: {username} (Mobile: {mobile_number})")
        success = send_telegram_notification(user_id, message)
        
        if success:
            print("✅ Test notification sent successfully!")
        else:
            print("❌ Test notification failed!")
    else:
        print("❌ No user found with mobile number. Please register a user with mobile number first!")ran' not found")

def test_direct_notification():
    """Test direct notification without database"""
    print("🧪 Testing direct Telegram notification...")
    
    import requests
    
    bot_token = "7653297508:AAE_sfu893LJ-D5Z5xtr_sjy-XEJvvf7haQ"
    chat_id = "5776427389"
    
    message = "🦅 *Eagle Task Manager*\n\n🧪 *Direct Test Notification*\n\nYour bot is working perfectly!"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("✅ Direct notification sent successfully!")
            return True
        else:
            print(f"❌ Direct notification failed: {response.text}")
            return False
    except Exception as e:
        print(f"💥 Error in direct notification: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Telegram Testing Script")
    print("=" * 40)
    
    # Test direct notification first (doesn't need database)
    print("\n📱 Testing direct notification...")
    test_direct_notification()
    
    print("\n👤 Testing user-based notification...")
    # Setup test data
    setup_test_chat_ids()
    
    # Test notification
    test_telegram_notification()
    
    print("\n🎯 Summary:")
    print("- Direct notifications should work immediately")
    print("- User notifications will use fallback chat_id if mobile number fails")
    print("- All notifications will go to your chat_id: 5776427389")
