from django.http import HttpResponse
from django.shortcuts import render
import mysql.connector


def getDbConnection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='chat_app'

    )

def home(request):
    context = {
        'projectName':'Chat App',
    }
    return render(request,'home.html',context)

from django.shortcuts import render, redirect

def login(request):
    context = {}
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get('password')

        conn = getDbConnection()
        cursor = conn.cursor()
        query = 'SELECT * FROM User WHERE Email = %s AND Password = %s'
        cursor.execute(query, (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            request.session['userEmail'] = email
            # Redirect to 'next' if present, else to chat
            next_url = request.GET.get('next') or request.POST.get('next') or '/chat/'
            return redirect(next_url)
        else:
            context = {'flag': '0', 'status': 'Wrong Credentials'}
    # Pass along 'next' if present
    context['next'] = request.GET.get('next', '')
    return render(request, 'login.html', context)

            

def signup(request):
    context = {}
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        conn = getDbConnection()

        cursor = conn.cursor()

        query="INSERT INTO USER (name,email,password) values(%s,%s,%s)"

        try:
            cursor.execute(query,(name,email,password))
            conn.commit()
            context = {'status':'Signup Sucessful','flag':'1'}
        except mysql.connector.IntegrityError:
            context={'status':'Email already exist','flag':'0'}
        finally:
            cursor.close()
            conn.close()
    return render(request,'signup.html',context)

def createGroup(request):
    context = {}
    if request.method == 'POST':
        groupName = request.POST.get('groupName')
        adminEmail = request.session.get('userEmail')

        conn = getDbConnection()
        cursor = conn.cursor()

        try:
            # Insert new group
            cursor.execute("INSERT INTO group_table (group_name, admin_email) VALUES (%s, %s)", (groupName, adminEmail))
            group_id = cursor.lastrowid

            # Get user_id of the admin by email
            cursor.execute("SELECT User_Id FROM User WHERE Email = %s", (adminEmail,))
            user_row = cursor.fetchone()
            if user_row:
                user_id = user_row[0]
                # Insert admin as group member
                cursor.execute("INSERT INTO user_group (user_id, group_id) VALUES (%s, %s)", (user_id, group_id))
                conn.commit()
                context = {'status': 'Successfully created new group', 'flag': '1'}
            else:
                context = {'status': 'Admin user not found', 'flag': '0'}

        except mysql.connector.IntegrityError:
            context = {'status': 'Group Already Exists', 'flag': '0'}
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    return render(request, 'group_create.html', context)



from django.http import JsonResponse
from django.shortcuts import redirect

# Helper functions
def get_current_user(request):
    """Get logged-in user details from session"""
    if 'userEmail' not in request.session:
        return None
    conn = getDbConnection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM User WHERE email = %s',
        (request.session['userEmail'],)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# Chat Views
def chat_home(request):
    user = get_current_user(request)
    if not user:
        return redirect('login')

    context = {
        'user': user,
        'status': '',
        'flag': '',
    }

    conn = getDbConnection()
    cursor = conn.cursor(dictionary=True)

    # Handle group creation if POST
    if request.method == 'POST' and 'groupName' in request.POST:
        groupName = request.POST.get('groupName')
        try:
            # Create group
            cursor.execute("INSERT INTO group_table (group_name, admin_email) VALUES (%s, %s)", (groupName, user['Email']))
            group_id = cursor.lastrowid
            # Get user_id
            cursor.execute("SELECT User_Id FROM User WHERE Email = %s", (user['Email'],))
            user_row = cursor.fetchone()
            if user_row:
                user_id = user_row['User_Id']
                cursor.execute("INSERT INTO user_group (user_id, group_id) VALUES (%s, %s)", (user_id, group_id))
                conn.commit()
                context['status'] = 'Successfully created new group'
                context['flag'] = '1'
            else:
                context['status'] = 'Admin user not found'
                context['flag'] = '0'
        except mysql.connector.IntegrityError:
            context['status'] = 'Group already exists'
            context['flag'] = '0'
            conn.rollback()

    # Fetch groups
    cursor.execute('''
        SELECT g.group_id, g.group_name 
        FROM user_group ug
        JOIN group_table g ON ug.group_id = g.group_id
        WHERE ug.user_id = %s
    ''', (user['User_Id'],))
    groups = cursor.fetchall()
    context['groups'] = groups

    # Fetch ALL users except current user
    cursor.execute('''
        SELECT User_Id, Name 
        FROM User 
        WHERE User_Id != %s
        ORDER BY Name
    ''', (user['User_Id'],))
    chats = cursor.fetchall()
    context['chats'] = chats

    cursor.close()
    conn.close()
    return render(request, 'chat_home.html', context)

def send_message(request):
    """Handle message sending (both individual and group)"""
    user = get_current_user(request)
    if not user or request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
    
    data = {
        'content': request.POST.get('content'),
        'receiver_type': request.POST.get('receiver_type'),
        'receiver_id': request.POST.get('receiver_id')
    }
    
    conn = getDbConnection()
    cursor = conn.cursor()
    
    try:
        if data['receiver_type'] == 'user':
            query = '''
                INSERT INTO Message 
                (sender_user_id, receiver_user_id, content)
                VALUES (%s, %s, %s)
            '''
            cursor.execute(query, (
                user['User_Id'], 
                int(data['receiver_id']), 
                data['content']
            ))
        elif data['receiver_type'] == 'group':
            # Verify user is group member
            cursor.execute('''
                SELECT 1 FROM user_group 
                WHERE user_id = %s AND group_id = %s
            ''', (user['User_Id'], int(data['receiver_id'])))
            if not cursor.fetchone():
                raise ValueError("Not a group member")
            
            query = '''
                INSERT INTO Message 
                (sender_user_id, receiver_group_id, content)
                VALUES (%s, %s, %s)
            '''
            cursor.execute(query, (
                user['User_Id'], 
                int(data['receiver_id']), 
                data['content']
            ))
        
        conn.commit()
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        conn.rollback()
        return JsonResponse({'status': 'error', 'message': str(e)})
        
    finally:
        cursor.close()
        conn.close()

def get_messages(request):
    """Retrieve messages for current user"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
    
    conn = getDbConnection()
    cursor = conn.cursor(dictionary=True)
    
    # Get both individual and group messages
    cursor.execute('''
        (SELECT m.content, m.sent_at, u.Name as sender_name, 
                'user' as type, m.receiver_user_id
         FROM Message m
         JOIN User u ON m.sender_user_id = u.User_Id
         WHERE m.receiver_user_id = %s)
         
        UNION ALL
         
        (SELECT m.content, m.sent_at, u.Name as sender_name,
                'group' as type, m.receiver_group_id
         FROM Message m
         JOIN User u ON m.sender_user_id = u.User_Id
         WHERE m.receiver_group_id IN (
             SELECT group_id FROM user_group WHERE user_id = %s
         ))
         
        ORDER BY sent_at DESC
        LIMIT 50
    ''', (user['User_Id'], user['User_Id']))
    
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return JsonResponse({'messages': messages})

def add_to_group(request):
    """Add user to existing group (admin only)"""
    user = get_current_user(request)
    if not user or request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
    
    target_email = request.POST.get('email')
    group_id = request.POST.get('group_id')
    
    conn = getDbConnection()
    cursor = conn.cursor()
    
    try:
        # Verify admin privileges
        cursor.execute('''
            SELECT 1 FROM group_table 
            WHERE group_id = %s AND admin_email = %s
        ''', (group_id, user['Email']))
        if not cursor.fetchone():
            raise PermissionError("Not group admin")
        
        # Get target user
        cursor.execute('''
            SELECT User_Id FROM User WHERE email = %s
        ''', (target_email,))
        target_user = cursor.fetchone()
        if not target_user:
            raise ValueError("User not found")
        
        # Add to group
        cursor.execute('''
            INSERT INTO user_group (user_id, group_id)
            VALUES (%s, %s)
        ''', (target_user[0], group_id))
        
        conn.commit()
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        conn.rollback()
        return JsonResponse({'status': 'error', 'message': str(e)})
        
    finally:
        cursor.close()
        conn.close()

