from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from db import get_connection

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('auth.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('username')

        if not all([email, password, name]):
            return jsonify({"status": "error", "message": "Missing fields"}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if email already exists
        cursor.execute("SELECT * FROM User WHERE Email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Email already exists"}), 409

        # Create new user
        cursor.execute(
            "INSERT INTO User (Name, Email, Password) VALUES (%s, %s, %s)",
            (name, email, password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "User registered successfully"}), 200
    except Exception as e:
        print("Signup error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM User WHERE Email = %s AND Password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            # Remove password before sending to client
            user.pop('Password', None)
            return jsonify({"status": "success", "user": user})
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    except Exception as e:
        print("Login error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT User_Id, Name, Email FROM User")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "users": users})
    except Exception as e:
        print("Error fetching users:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/create_group', methods=['POST'])
def create_group():
    try:
        data = request.json
        group_name = data.get('group_name')
        admin_email = data.get('admin_email')
        members = data.get('members', [])  # List of user IDs to add to group

        if not group_name or not admin_email:
            return jsonify({"status": "error", "message": "Missing group_name or admin_email"}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Get admin user ID
        cursor.execute("SELECT User_Id FROM User WHERE Email = %s", (admin_email,))
        admin = cursor.fetchone()
        if not admin:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Admin user not found"}), 404

        # Create group
        cursor.execute(
            "INSERT INTO group_Table (group_name, admin_email) VALUES (%s, %s)",
            (group_name, admin_email)
        )
        group_id = cursor.lastrowid

        # Add admin to group
        cursor.execute(
            "INSERT INTO user_group (user_id, group_id) VALUES (%s, %s)",
            (admin['User_Id'], group_id)
        )

        # Add other members to group
        for member_id in members:
            if member_id != admin['User_Id']:  # Don't add admin twice
                cursor.execute(
                    "INSERT INTO user_group (user_id, group_id) VALUES (%s, %s)",
                    (member_id, group_id)
                )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Group created", "group_id": group_id}), 201
    except Exception as e:
        print("Error creating group:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/groups/<int:user_id>', methods=['GET'])
def get_user_groups(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT g.group_id, g.group_name, g.admin_email
            FROM group_Table g
            JOIN user_group ug ON g.group_id = ug.group_id
            WHERE ug.user_id = %s
        """, (user_id,))
        groups = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "groups": groups})
    except Exception as e:
        print("Error fetching user groups:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        sender_user_id = data.get('sender_user_id')
        content = data.get('content')
        receiver_user_id = data.get('receiver_user_id')
        receiver_group_id = data.get('receiver_group_id')

        if not sender_user_id or not content:
            return jsonify({"status": "error", "message": "Missing sender_user_id or content"}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Insert message
        cursor.execute("""
            INSERT INTO Message (sender_user_id, receiver_user_id, receiver_group_id, content)
            VALUES (%s, %s, %s, %s)
        """, (sender_user_id, receiver_user_id, receiver_group_id, content))
        
        message_id = cursor.lastrowid
        conn.commit()

        # Get the inserted message with sender name
        cursor.execute("""
            SELECT m.*, u.Name as sender_name
            FROM Message m
            JOIN User u ON m.sender_user_id = u.User_Id
            WHERE m.message_id = %s
        """, (message_id,))
        message = cursor.fetchone()
        
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Message sent", "data": message})
    except Exception as e:
        print("Error sending message:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/chat_history', methods=['GET'])
def chat_history():
    try:
        sender_user_id = request.args.get('sender_user_id', type=int)
        receiver_user_id = request.args.get('receiver_user_id', type=int)
        receiver_group_id = request.args.get('receiver_group_id', type=int)

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        if receiver_group_id:
            # Get group messages
            cursor.execute("""
                SELECT m.*, u.Name as sender_name
                FROM Message m
                JOIN User u ON m.sender_user_id = u.User_Id
                WHERE m.receiver_group_id = %s
                ORDER BY m.sent_at
            """, (receiver_group_id,))
        elif sender_user_id and receiver_user_id:
            # Get direct messages between two users
            cursor.execute("""
                SELECT m.*, u.Name as sender_name
                FROM Message m
                JOIN User u ON m.sender_user_id = u.User_Id
                WHERE (m.sender_user_id = %s AND m.receiver_user_id = %s)
                   OR (m.sender_user_id = %s AND m.receiver_user_id = %s)
                ORDER BY m.sent_at
            """, (sender_user_id, receiver_user_id, receiver_user_id, sender_user_id))
        else:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Invalid parameters"}), 400

        messages = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(messages)
    except Exception as e:
        print("Error fetching chat history:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
