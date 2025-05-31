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

    try:
        # Handle group creation if POST
        if request.method == 'POST' and 'groupName' in request.POST:
            groupName = request.POST.get('groupName')
            try:
                # First check if group name already exists
                cursor.execute("SELECT 1 FROM group_table WHERE group_name = %s", (groupName,))
                exists = cursor.fetchone()
                cursor.fetchall()  # Clear any remaining results
                
                if exists:
                    context['status'] = 'Group name already exists'
                    context['flag'] = '0'
                else:
                    # Create group only if name doesn't exist
                    cursor.execute("INSERT INTO group_table (group_name, admin_email) VALUES (%s, %s)", (groupName, user['Email']))
                    group_id = cursor.lastrowid
                    
                    # Get user_id
                    cursor.execute("SELECT User_Id FROM User WHERE Email = %s", (user['Email'],))
                    user_row = cursor.fetchone()
                    cursor.fetchall()  # Clear any remaining results
                    
                    if user_row:
                        user_id = user_row['User_Id']
                        cursor.execute("INSERT INTO user_group (user_id, group_id) VALUES (%s, %s)", (user_id, group_id))
                        conn.commit()
                        context['status'] = 'Successfully created new group'
                        context['flag'] = '1'
                    else:
                        context['status'] = 'Admin user not found'
                        context['flag'] = '0'
                        conn.rollback()
            except mysql.connector.IntegrityError:
                context['status'] = 'Error creating group'
                context['flag'] = '0'
                conn.rollback()
            except Exception as e:
                context['status'] = f'Error: {str(e)}'
                context['flag'] = '0'
                conn.rollback()

        # Fetch groups - Modified to prevent duplicates
        cursor.execute('''
            SELECT DISTINCT g.group_id, g.group_name 
            FROM group_table g
            INNER JOIN user_group ug ON g.group_id = ug.group_id
            WHERE ug.user_id = %s
            ORDER BY g.group_name
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

    except Exception as e:
        context['status'] = f'Error: {str(e)}'
        context['flag'] = '0'
        if conn.in_transaction:
            conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return render(request, 'chat_home.html', context)

def get_messages(request):
    """Retrieve messages for current user"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
    
    receiver_type = request.GET.get('type')
    receiver_id = request.GET.get('id')
    
    if not receiver_type or not receiver_id:
        return JsonResponse({'status': 'error', 'message': 'Missing receiver information'})
    
    conn = getDbConnection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        if receiver_type == 'user':
            # Get direct messages between two users
            cursor.execute('''
                SELECT m.content, m.sent_at, u.Name as sender_name, 
                       m.sender_user_id, m.receiver_user_id
                FROM Message m
                JOIN User u ON m.sender_user_id = u.User_Id
                WHERE ((m.sender_user_id = %s AND m.receiver_user_id = %s)
                    OR (m.sender_user_id = %s AND m.receiver_user_id = %s))
                    AND m.receiver_group_id IS NULL
                ORDER BY m.sent_at ASC
            ''', (user['User_Id'], int(receiver_id), int(receiver_id), user['User_Id']))
            
        elif receiver_type == 'group':
            # Verify user is group member
            cursor.execute('''
                SELECT 1 FROM user_group 
                WHERE user_id = %s AND group_id = %s
            ''', (user['User_Id'], int(receiver_id)))
            if not cursor.fetchone():
                return JsonResponse({'status': 'error', 'message': 'Not a group member'})
            
            # Get group messages
            cursor.execute('''
                SELECT m.content, m.sent_at, u.Name as sender_name,
                       m.sender_user_id, m.receiver_group_id
                FROM Message m
                JOIN User u ON m.sender_user_id = u.User_Id
                WHERE m.receiver_group_id = %s
                ORDER BY m.sent_at ASC
            ''', (int(receiver_id),))
        
        messages = cursor.fetchall()
        # Convert datetime objects to strings for JSON serialization
        for message in messages:
            message['sent_at'] = message['sent_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return JsonResponse({'status': 'success', 'messages': messages})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
        
    finally:
        cursor.close()
        conn.close()

def send_message(request):
    """Handle message sending (both individual and group)"""
    user = get_current_user(request)
    if not user or request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
    
    content = request.POST.get('content')
    receiver_type = request.POST.get('receiver_type')
    receiver_id = request.POST.get('receiver_id')
    
    if not all([content, receiver_type, receiver_id]):
        return JsonResponse({'status': 'error', 'message': 'Missing required fields'})
    
    conn = getDbConnection()
    cursor = conn.cursor()
    
    try:
        if receiver_type == 'user':
            # Verify receiver exists
            cursor.execute('SELECT 1 FROM User WHERE User_Id = %s', (int(receiver_id),))
            if not cursor.fetchone():
                raise ValueError("Receiver user not found")
            
            query = '''
                INSERT INTO Message 
                (sender_user_id, receiver_user_id, content)
                VALUES (%s, %s, %s)
            '''
            cursor.execute(query, (
                user['User_Id'], 
                int(receiver_id), 
                content
            ))
            
        elif receiver_type == 'group':
            # Verify user is group member
            cursor.execute('''
                SELECT 1 FROM user_group 
                WHERE user_id = %s AND group_id = %s
            ''', (user['User_Id'], int(receiver_id)))
            if not cursor.fetchone():
                raise ValueError("Not a group member")
            
            # Verify group exists
            cursor.execute('SELECT 1 FROM group_table WHERE group_id = %s', (int(receiver_id),))
            if not cursor.fetchone():
                raise ValueError("Group not found")
            
            query = '''
                INSERT INTO Message 
                (sender_user_id, receiver_group_id, content)
                VALUES (%s, %s, %s)
            '''
            cursor.execute(query, (
                user['User_Id'], 
                int(receiver_id), 
                content
            ))
        
        conn.commit()
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        conn.rollback()
        return JsonResponse({'status': 'error', 'message': str(e)})
        
    finally:
        cursor.close()
        conn.close()

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

def get_all_groups(request):
    """Get all available groups for the current user"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
    
    conn = getDbConnection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all groups where user is not a member
        cursor.execute('''
            SELECT g.group_id, g.group_name, u.Name as admin_name
            FROM group_table g
            JOIN User u ON g.admin_email = u.Email
            WHERE g.group_id NOT IN (
                SELECT group_id FROM user_group WHERE user_id = %s
            )
            ORDER BY g.group_name
        ''', (user['User_Id'],))
        available_groups = cursor.fetchall()
        
        # Get groups where user is admin
        cursor.execute('''
            SELECT g.group_id, g.group_name
            FROM group_table g
            WHERE g.admin_email = %s
            ORDER BY g.group_name
        ''', (user['Email'],))
        admin_groups = cursor.fetchall()
        
        return JsonResponse({
            'status': 'success',
            'available_groups': available_groups,
            'admin_groups': admin_groups
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def join_group(request):
    """Request to join a group"""
    user = get_current_user(request)
    if not user or request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'})
    
    group_id = request.POST.get('group_id')
    if not group_id:
        return JsonResponse({'status': 'error', 'message': 'Missing group ID'})
    
    conn = getDbConnection()
    cursor = conn.cursor()
    
    try:
        # Check if user is already in group
        cursor.execute('''
            SELECT 1 FROM user_group 
            WHERE user_id = %s AND group_id = %s
        ''', (user['User_Id'], group_id))
        if cursor.fetchone():
            return JsonResponse({'status': 'error', 'message': 'Already a member of this group'})
        
        # Add user to group
        cursor.execute('''
            INSERT INTO user_group (user_id, group_id)
            VALUES (%s, %s)
        ''', (user['User_Id'], group_id))
        
        conn.commit()
        return JsonResponse({'status': 'success', 'message': 'Successfully joined group'})
        
    except Exception as e:
        conn.rollback()
        return JsonResponse({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

