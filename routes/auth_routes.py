from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from db import get_db, serialize_doc

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.user_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin') or 'admin_id' not in session:
            flash('Admin authentication required.', 'danger')
            return redirect(url_for('auth.admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ================= CUSTOMER / USER AUTH =================

@auth_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    if 'user_id' in session:
        return redirect(url_for('user.menu_view'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        db = get_db()
        user = db.users.find_one({'email': email})

        if user and check_password_hash(user.get('password_hash', ''), password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user.get('name', 'Customer')
            session['user_email'] = user.get('email')
            session['user_phone'] = user.get('phone', '')
            session['is_admin'] = False
            
            flash(f"Welcome back, {user.get('name', 'Guest')}! Ready for delicious breakfast?", 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('user.menu_view'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/user_login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def user_register():
    if 'user_id' in session:
        return redirect(url_for('user.menu_view'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/user_register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/user_register.html')

        db = get_db()
        if db.users.find_one({'email': email}):
            flash('An account with this email already exists. Please log in.', 'warning')
            return redirect(url_for('auth.user_login'))

        new_user = {
            'name': name,
            'email': email,
            'phone': phone,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow()
        }
        result = db.users.insert_one(new_user)
        
        # Log in automatically
        session['user_id'] = str(result.inserted_id)
        session['user_name'] = name
        session['user_email'] = email
        session['user_phone'] = phone
        session['is_admin'] = False

        flash('Registration successful! Welcome to Smart Breakfast Hotel.', 'success')
        return redirect(url_for('user.menu_view'))

    return render_template('auth/user_register.html')

@auth_bp.route('/logout')
def user_logout():
    # Keep table_number if seated
    table_num = session.get('table_number')
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)
    session.pop('user_phone', None)
    if table_num:
        session['table_number'] = table_num
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('user.menu_view'))


# ================= ADMIN AUTH =================

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin') and 'admin_id' in session:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()
        admin = db.admins.find_one({'email': email})

        if admin and check_password_hash(admin.get('password_hash', ''), password):
            session['admin_id'] = str(admin['_id'])
            session['admin_name'] = admin.get('name', 'Admin')
            session['admin_email'] = admin.get('email')
            session['admin_role'] = admin.get('role', 'admin')
            session['is_admin'] = True

            flash(f"Welcome to Hotel Control Center, {admin.get('name', 'Admin')}!", 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials. Access denied.', 'danger')

    return render_template('auth/admin_login.html')

@auth_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)
    session.pop('admin_role', None)
    session.pop('is_admin', None)
    flash('Admin session logged out successfully.', 'info')
    return redirect(url_for('auth.admin_login'))
