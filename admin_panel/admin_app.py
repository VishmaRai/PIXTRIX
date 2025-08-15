from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from werkzeug.security import check_password_hash

# Configuration
DB_PATH = "../db/dataset.db"  # Adjust path as needed

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin Login Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("Please enter both username and password")
            return render_template('admin/login.html')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
            admin = cursor.fetchone()
            conn.close()
            
            if admin and check_password_hash(admin['password'], password):
                session['admin_logged_in'] = True
                session['admin_username'] = username
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid username or password", "error")
        except Exception as e:
            print(f"Database error: {e}")
            flash("An error occurred. Please try again.", "error")
    
    return render_template('admin/login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Dashboard Route
@app.route('/dashboard')
@admin_required
def dashboard():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total registered users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Active subscriptions
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        active_subscriptions = cursor.fetchone()[0]
        
        # Total credits sold (from all transactions with amounts)
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE amount > 0")
        total_credits_sold = cursor.fetchone()[0] or 0
        
        # Revenue this month - use ALL transactions with amounts (not just 'completed')
        cursor.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE amount > 0 
            AND created_at >= date('now', 'start of month')
        """)
        revenue_this_month = cursor.fetchone()[0] or 0
        
        # Alternative approach if the above doesn't work
        if revenue_this_month == 0:
            cursor.execute("""
                SELECT SUM(amount) FROM transactions 
                WHERE amount > 0 
                AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            """)
            revenue_this_month = cursor.fetchone()[0] or 0
        
        # Images generated today
        cursor.execute("""
            SELECT COUNT(*) FROM generations 
            WHERE DATE(created_at) = DATE('now')
        """)
        images_today = cursor.fetchone()[0]
        
        # Images generated this month
        cursor.execute("""
            SELECT COUNT(*) FROM generations 
            WHERE created_at >= date('now', 'start of month')
        """)
        images_this_month = cursor.fetchone()[0]
        
        conn.close()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             active_subscriptions=active_subscriptions,
                             total_credits_sold=total_credits_sold,
                             revenue_this_month=revenue_this_month,
                             images_today=images_today,
                             images_this_month=images_this_month)
    except Exception as e:
        print(f"Dashboard error: {e}")
        flash("Error loading dashboard data", "error")
        return render_template('admin/dashboard.html')

# Users Management with Search
@app.route('/users')
@admin_required
def users():
    try:
        # Get search parameters
        search = request.args.get('search', '').strip()
        subscription_status = request.args.get('subscription_status', '').strip()
        page = request.args.get('page', 1, type=int)
        
        per_page = 20
        offset = (page - 1) * per_page
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build the query with search conditions
        base_query = """
            SELECT u.id, u.username, u.email, u.credits, u.created_at, u.verified,
                   s.plan_name, s.start_date, s.end_date, s.status as subscription_status
            FROM users u
            LEFT JOIN (
                SELECT user_id, plan_name, start_date, end_date, status,
                       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
                FROM subscriptions
            ) s ON u.id = s.user_id AND s.rn = 1
        """
        
        count_query = """
            SELECT COUNT(*) 
            FROM users u
            LEFT JOIN (
                SELECT user_id, plan_name, start_date, end_date, status,
                       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
                FROM subscriptions
            ) s ON u.id = s.user_id AND s.rn = 1
        """
        
        conditions = []
        params = []
        count_params = []
        
        # Add search condition
        if search:
            conditions.append("(u.username LIKE ? OR u.email LIKE ? OR s.plan_name LIKE ?)")
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])
            count_params.extend([search_param, search_param, search_param])
        
        # Add subscription status condition
        if subscription_status:
            if subscription_status == 'no_subscription':
                conditions.append("s.user_id IS NULL")
            else:
                conditions.append("s.status = ?")
                params.append(subscription_status)
                count_params.append(subscription_status)
        
        # Apply conditions to queries
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            base_query += where_clause
            count_query += where_clause
        
        # Add ordering and pagination
        base_query += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        # Execute the main query
        cursor.execute(base_query, params)
        users_data = cursor.fetchall()
        
        # Execute count query for pagination
        cursor.execute(count_query, count_params)
        total_users = cursor.fetchone()[0]
        
        conn.close()
        
        total_pages = (total_users + per_page - 1) // per_page
        
        return render_template('admin/users.html', 
                             users=users_data,
                             search=search,
                             subscription_status=subscription_status,
                             page=page,
                             total_pages=total_pages,
                             total_users=total_users)
    except Exception as e:
        print(f"Users error: {e}")
        flash("Error loading users data", "error")
        return render_template('admin/users.html', users=[], search='', subscription_status='')


# Payments & Subscriptions
@app.route('/payments')
@admin_required
def payments():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.id, t.user_id, u.email, t.plan_name, t.amount, t.status, 
                   t.payment_method, t.created_at, t.pid
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
        """)
        payments_data = cursor.fetchall()
        conn.close()
        
        return render_template('admin/payments.html', payments=payments_data)
    except Exception as e:
        print(f"Payments error: {e}")
        flash("Error loading payments data", "error")
        return render_template('admin/payments.html', payments=[])

# Image Generation Logs
@app.route('/logs')
@admin_required
def logs():
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        per_page = 20
        offset = (page - 1) * per_page
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT g.id, g.user_id, u.email, g.prompt, g.aspect_ratio, g.created_at
            FROM generations g
            LEFT JOIN users u ON g.user_id = u.id
        """
        
        conditions = []
        params = []
        
        if search:
            conditions.append("(u.email LIKE ? OR g.prompt LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%'])
        
        if date_from:
            conditions.append("DATE(g.created_at) >= ?")
            params.append(date_from)
        
        if date_to:
            conditions.append("DATE(g.created_at) <= ?")
            params.append(date_to)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY g.created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        logs_data = cursor.fetchall()
        
        count_query = "SELECT COUNT(*) FROM generations g LEFT JOIN users u ON g.user_id = u.id"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        
        count_params = params[:-2]
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        conn.close()
        
        total_pages = (total + per_page - 1) // per_page
        
        return render_template('admin/logs.html', 
                             logs=logs_data, 
                             page=page, 
                             total_pages=total_pages,
                             search=search,
                             date_from=date_from,
                             date_to=date_to)
    except Exception as e:
        print(f"Logs error: {e}")
        flash("Error loading logs data", "error")
        return render_template('admin/logs.html', logs=[], page=1, total_pages=1)
    
# Add this route to your existing routes
@app.route('/settings')
@admin_required
def settings():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all plans
        cursor.execute("SELECT * FROM plans ORDER BY id")
        plans = cursor.fetchall()
        conn.close()
        
        return render_template('admin/settings.html', plans=plans)
    except Exception as e:
        print(f"Settings error: {e}")
        flash("Error loading plans data", "error")
        return render_template('admin/settings.html', plans=[])

@app.route('/settings/update_plan', methods=['POST'])
@admin_required
def update_plan():
    try:
        plan_id = request.form.get('plan_id')
        name = request.form.get('name', '').strip()
        credits = request.form.get('credits')
        amount = request.form.get('amount')
        active = request.form.get('active') == 'on'
        
        # Validation
        if not plan_id:
            flash("Invalid plan ID", "error")
            return redirect(url_for('settings'))
        
        if not name or len(name) < 2:
            flash("Plan name must be at least 2 characters long", "error")
            return redirect(url_for('settings'))
        
        try:
            credits_int = int(credits)
            if credits_int <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            flash("Credits must be a positive number", "error")
            return redirect(url_for('settings'))
        
        try:
            amount_float = float(amount)
            if amount_float < 0:
                raise ValueError()
        except (ValueError, TypeError):
            flash("Price must be a valid positive number", "error")
            return redirect(url_for('settings'))
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if plan exists
        cursor.execute("SELECT id FROM plans WHERE id = ?", (plan_id,))
        if not cursor.fetchone():
            flash("Plan not found", "error")
            conn.close()
            return redirect(url_for('settings'))
        
        cursor.execute("""
            UPDATE plans 
            SET name = ?, credits = ?, amount = ?, active = ?
            WHERE id = ?
        """, (name, credits_int, amount_float, active, plan_id))
        
        conn.commit()
        conn.close()
        
        flash(f"Plan '{name}' updated successfully!", "success")
    except Exception as e:
        print(f"Update plan error: {e}")
        flash("Error updating plan. Please try again.", "error")
    
    return redirect(url_for('settings'))
    
    
    
    

if __name__ == '__main__':
    app.run(debug=True, port=5001)