import os
from flask import Flask, abort, render_template, request, jsonify, session, redirect, url_for, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from db.database import get_connection, init_db, get_user_by_id, get_generations_by_user_id, get_all_plans
import sqlite3
import secrets
import re
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from authlib.integrations.flask_client import OAuth
import time
from urllib.parse import unquote
import json, base64, hmac, hashlib
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a-very-secret-key')

# Flask-Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'bhismabhisma809@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

# ======= eSewa Configuration =======
ESW_PRODUCT_CODE = os.environ.get('ESW_PRODUCT_CODE', 'EPAYTEST')
ESW_SECRET_KEY = os.environ.get('ESW_SECRET_KEY', '8gBm/:&EnhH.1/q').encode('utf-8')
ESW_CHECKOUT_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"

# ======= Subscription Helpers =======
def get_active_subscription(user_id):
    """Get user's active subscription if exists and not expired"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = ? 
            AND status = 'active' 
            AND end_date > datetime('now')
            AND credits_remaining > 0
            ORDER BY end_date DESC
            LIMIT 1
        """, (user_id,))
        return cursor.fetchone()
    finally:
        conn.close()

def deduct_credit(user_id):
    """Deduct 1 credit, prioritizing subscription credits first"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Try to deduct from subscription first
        subscription = get_active_subscription(user_id)
        if subscription:
            cursor.execute("""
                UPDATE subscriptions 
                SET credits_remaining = credits_remaining - 1 
                WHERE id = ? AND credits_remaining > 0
            """, (subscription['id'],))
            if cursor.rowcount == 1:
                conn.commit()
                return True
        
        # Fall back to user credits
        cursor.execute("""
            UPDATE users 
            SET credits = credits - 1 
            WHERE id = ? AND credits > 0
        """, (user_id,))
        if cursor.rowcount == 1:
            conn.commit()
            return True
        
        return False
    finally:
        conn.close()

def sign_esewa_payload(total_amount: str, txn_uuid: str) -> str:
    message = (
        f"total_amount={total_amount},"
        f"transaction_uuid={txn_uuid},"
        f"product_code={ESW_PRODUCT_CODE}"
    )
    return base64.b64encode(
        hmac.new(ESW_SECRET_KEY, message.encode(), hashlib.sha256).digest()
    ).decode()

def verify_esewa_response(b64_resp: str) -> dict:
    """Returns decoded JSON if signature is valid, else aborts"""
    decoded = base64.b64decode(unquote(b64_resp)).decode()
    data = json.loads(decoded)

    # Re-build the exact string eSewa signed based on 'signed_field_names'
    signed_fields = data.get("signed_field_names", "").split(",")
    
    message_parts = []
    for key in signed_fields:
        if key in data:
            message_parts.append(f"{key}={data[key]}")

    message = ",".join(message_parts)

    expected_sig = base64.b64encode(
        hmac.new(ESW_SECRET_KEY, message.encode(), hashlib.sha256).digest()
    ).decode()

    if not hmac.compare_digest(expected_sig, data.get("signature", "")):
        abort(400, "Invalid eSewa signature")

    return data

mail = Mail(app)
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"}
)

init_db()
# fetch plans data from database
def get_plans():
    try:
        return get_all_plans()
    except Exception as e:
        print(f"Error fetching plans: {e}")
        # Fallback to hardcoded values
        return {
            "basic": {"credits": 10, "amount": 100, "name": "Basic"},
            "pro": {"credits": 150, "amount": 1000, "name": "Pro"}
        }
COLAB_API = os.environ.get('COLAB_API_URL', 'https://7b6e2384fcbf.ngrok-free.app/generate')
is_generating = False


# ----------- Helper Functions for getting First letters of User Name -----------
def get_initials(full_name, max_initials=2):
    """Extract initials from full name"""
    if not full_name or not str(full_name).strip():
        return "?"
    cleaned_name = re.sub(r'[^a-zA-Z\s]', ' ', str(full_name).strip())
    words = [word for word in cleaned_name.split() if word and len(word) > 0]
    if not words:
        return "?"
    initials = ''.join([word[0].upper() for word in words[:max_initials]])
    return initials if initials else "?"

def nocache(view):
    """Helper to Disable Cache (Prevents Back Button Access)"""
    def no_cache_wrapper(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    no_cache_wrapper.__name__ = view.__name__
    return no_cache_wrapper


# ----------- Routes -----------
@app.route("/", methods=["GET", "POST"])
@nocache
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))

    global is_generating
    images = []

    if request.method == "POST":
        # --- Guest Credit Check ---
        if 'guest_credits' not in session:
            session['guest_credits'] = 2

        if session['guest_credits'] <= 0:
            return jsonify(error="You have used all your free credits. Please log in to continue."), 403
        
        session['guest_credits'] -= 1
        # --- End Credit Check ---

        if is_generating:
            return jsonify(error="Generation already in progress"), 429

        is_generating = True
        prompt = request.form["prompt"]
        aspect = request.form["aspect"]
        headers = {"ngrok-skip-browser-warning": "true"}

        try:
            r = requests.post(COLAB_API, json={
                "prompt": prompt,
                "negative_prompt": "blury",
                "guidance_scale": 7.5,
                "aspect": aspect
            }, headers=headers, timeout=120)
            r.raise_for_status()
            data = r.json()
            base64_strings = data.get("images", [])
            images = ["data:image/png;base64," + s for s in base64_strings]

        except Exception as e:
            print(f"Error generating images: {e}")
            # Rollback credit deduction for guests
            session['guest_credits'] += 1
            images = []
        finally:
            is_generating = False

        # build the JSON response
        resp = jsonify(images=images)

        # mark browser as used for guests
        if not session.get('user_id'):
            resp.set_cookie('guest_used', '1', max_age=60*60*24)  # 1 day, (each day you get 2 credits)

        return resp

    # --- guest credit handling with persistent cookie ---
    credits_key = 'guest_credits'
    used_key = 'guest_used'          # cookie name that survives logout

    if 'user_id' not in session:
        # credits live in the session while the tab is open
        if credits_key not in session:
            # read the "already-used" flag from a long-lived cookie
            already_used = request.cookies.get(used_key, '0') == '1'
            session[credits_key] = 0 if already_used else 2
        credits = session[credits_key]
    else:
        credits = 0

    return render_template("index.html", credits=credits)


@app.route("/login", methods=["GET", "POST"])
@nocache
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['initials'] = get_initials(user['username'])
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password", 'error')
            return render_template("login_page.html")

    return render_template("login_page.html")


## login with Google OAuth
@app.route("/auth/google")
def login_google():
    redirect_uri = url_for("authorize_google", _external=True)
    return google.authorize_redirect(redirect_uri, access_type="offline", prompt="consent")


@app.route("/login/callback")
def authorize_google():
    token = google.authorize_access_token()
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        flash("Google login failed or no email provided.", "error")
        return redirect(url_for("login"))

    email = user_info["email"]
    google_sub = user_info["sub"]
    name = user_info.get("name")

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Check if a user is already associated with this Google account
    cur.execute(
        "SELECT u.* FROM users u JOIN oauth_users o ON u.id = o.user_id WHERE o.provider = 'google' AND o.provider_user_id = ?",
        (google_sub,)
    )
    user = cur.fetchone()

    if not user:
        # 2. If not, check if a user with this email already exists
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()

        if user:
            # 2a. Email exists, link this Google account to the existing user
            try:
                cur.execute(
                    "INSERT INTO oauth_users (user_id, provider, provider_user_id) VALUES (?, ?, ?)",
                    (user['id'], "google", google_sub)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                flash("This Google account is already linked to another user.", "error")
                conn.close()
                return redirect(url_for("login"))
        else:
            # 2b. No user with this email, create a new one
            try:
                cur.execute(
                    "INSERT INTO users (username, email, password, verified) VALUES (?, ?, ?, ?)",
                    (name, email, "GOOGLE_OAUTH", True)
                )
                user_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO oauth_users (user_id, provider, provider_user_id) VALUES (?, ?, ?)",
                    (user_id, "google", google_sub)
                )
                conn.commit()
                cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                user = cur.fetchone()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "UNIQUE constraint failed: users.email" in str(e):
                    flash("This email is already registered.", "error")
                else:
                    flash("An unexpected error occurred during signup.", "error")
                conn.close()
                return redirect(url_for("login"))

    conn.close()

    if not user:
        flash("Unable to log you in with Google. Please try again.", "error")
        return redirect(url_for("login"))

    session.clear()
    session["user_id"] = user['id']
    session["username"] = user['username']
    session["email"] = user['email']
    session["initials"] = get_initials(user['username'])

    return redirect(url_for("home"))


@app.route("/signup", methods=["GET", "POST"])
@nocache
def signup():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        code = request.form.get("code")

        conn = get_connection()
        cursor = conn.cursor()
        current_time = datetime.utcnow()
        cursor.execute('''
            SELECT * FROM verification_codes 
            WHERE email = ? AND code = ? AND expires_at > ?
        ''', (email, code, current_time))

        valid_code = cursor.fetchone()
        if not valid_code:
            return jsonify(success=False, message="Verification code is invalid")

        hashed_password = generate_password_hash(password)
        try:
            cursor.execute('''
                INSERT INTO users (username, email, password, verified)
                VALUES (?, ?, ?, ?)
            ''', (username, email, hashed_password, True))
            cursor.execute('DELETE FROM verification_codes WHERE id = ?', (valid_code[0],))
            conn.commit()
            return jsonify(success=True, message="Account created successfully!")
        except sqlite3.IntegrityError as e:
            conn.rollback()
            if "UNIQUE constraint failed: users.username" in str(e):
                return jsonify(success=False, message="Username already exists")
            elif "UNIQUE constraint failed: users.email" in str(e):
                return jsonify(success=False, message="Email already registered")
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return jsonify(success=False, message="An error occurred during signup")
        finally:
            conn.close()

    return render_template("SignUp_page.html")


@app.route("/send_verification_code", methods=["POST"])
def send_verification_code():
    email = request.json.get("email")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        return jsonify(success=False, message="Email already registered")

    cursor.execute('SELECT created_at FROM verification_codes WHERE email = ? ORDER BY created_at DESC LIMIT 1', (email,))
    last_code_time = cursor.fetchone()
    if last_code_time:
        last_created_at = datetime.strptime(last_code_time[0], '%Y-%m-%d %H:%M:%S')
        if datetime.utcnow() - last_created_at < timedelta(seconds=60):
            return jsonify(success=False, message="Please wait 60 seconds before requesting a new code.")

    code = ''.join(secrets.choice('0123456789') for _ in range(6))
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    cursor.execute('DELETE FROM verification_codes WHERE email = ?', (email,))
    cursor.execute('''
        INSERT INTO verification_codes (email, code, expires_at)
        VALUES (?, ?, ?)
    ''', (email, code, expires_at))
    conn.commit()

    try:
        msg = Message("Your Verification Code", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.html = f"<p>Your verification code is: <h1><strong>{code}</strong></h1></p><p>This code will expire in 10 minutes.</p>"
        mail.send(msg)
        return jsonify(success=True, message="Verification code sent!")
    except Exception as e:
        print(f"Failed to send email: {e}")
        return jsonify(success=False, message="Failed to send verification code")


@app.route("/add_credits", methods=["GET"])
@nocache
def add_credits():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_id(session['user_id'])
    active_sub = get_active_subscription(session['user_id'])
    
    return render_template(
        "Add_Credits.html", 
        user=user,
        active_sub=active_sub,
        plans=get_plans()
    )


@app.route("/gallery_all", methods=["GET"])
@nocache
def gallery_all():
    return render_template("gallery_all.html")


### Home Page ###
@app.route("/home", methods=["GET", "POST"])
@nocache
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = get_user_by_id(user_id)
    active_sub = get_active_subscription(user_id)

    if request.method == "POST":
        # --- Credit Check ---
        if not deduct_credit(user_id):
            return jsonify(error="You don't have enough credits to generate images."), 403

        global is_generating
        if is_generating:
            return jsonify(error="Generation already in progress"), 429

        is_generating = True
        prompt = request.form["prompt"]
        aspect = request.form["aspect"]
        headers = {"ngrok-skip-browser-warning": "true"}
        images = []

        try:
            r = requests.post(COLAB_API, json={
                "prompt": prompt,
                "negative_prompt": "blury",
                "guidance_scale": 7.5,
                "aspect": aspect
            }, headers=headers, timeout=120)
            r.raise_for_status()
            data = r.json()
            base64_strings = data.get("images", [])
            images = ["data:image/png;base64," + s for s in base64_strings]

            # Save to DB
            if base64_strings:
                import base64, os
                from datetime import datetime

                folder = os.path.join("static", "generated")
                os.makedirs(folder, exist_ok=True)

                for i, base64_str in enumerate(base64_strings):
                    image_data = base64.b64decode(base64_str)
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}.png"
                    filepath = os.path.join(folder, filename)
                    with open(filepath, "wb") as f:
                        f.write(image_data)

                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO generations (user_id, prompt, image_path, aspect_ratio)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, prompt, f"generated/{filename}", aspect))
                    conn.commit()
                    conn.close()

        except Exception as e:
            print(f"Error generating images: {e}")
            # Rollback credit deduction on failure
            conn = get_connection()
            cursor = conn.cursor()
            
            # Try to restore subscription credit first
            if active_sub:
                cursor.execute("""
                    UPDATE subscriptions 
                    SET credits_remaining = credits_remaining + 1 
                    WHERE id = ?
                """, (active_sub['id'],))
            
            # Otherwise restore user credit
            else:
                cursor.execute("""
                    UPDATE users 
                    SET credits = credits + 1 
                    WHERE id = ?
                """, (user_id,))
            
            conn.commit()
            conn.close()
            return jsonify(error="An error occurred while generating images."), 500
        finally:
            is_generating = False

        return jsonify(images=images)

    return render_template("home_page.html", user=user, active_sub=active_sub)


# New routes for profile functionality
@app.route("/library", methods=["GET"])
@nocache
def library():
    if 'user_id' not in session:
        flash("Please log in to access this page", "warning")
        return redirect(url_for('login'))

    images = get_generations_by_user_id(session['user_id'])
    return render_template("library.html", images=images)


# ── Account management API ------------------------------------
@app.route('/api/account/username', methods=['PUT'])
def change_username():
    if 'user_id' not in session:
        return jsonify(success=False, message='Not logged in'), 401
    new = request.json.get('username', '').strip()
    if not new:
        return jsonify(success=False, message='Empty username')

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('UPDATE users SET username = ? WHERE id = ?', (new, session['user_id']))
        conn.commit()
        session['username'] = new
        session['initials'] = get_initials(new)
        return jsonify(success=True)
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify(success=False, message='Username already taken')
    finally:
        conn.close()


@app.route('/api/account', methods=['DELETE'])
def delete_account():
    if 'user_id' not in session:
        return jsonify(success=False, message='Not logged in'), 401

    user_id = session['user_id']
    conn = get_connection()
    cur = conn.cursor()

    # 1. Remove generated images (files + DB records)
    cur.execute('SELECT image_path FROM generations WHERE user_id = ?', (user_id,))
    rows = cur.fetchall()
    for row in rows:
        try:
            os.remove(os.path.join('static', row[0]))
        except FileNotFoundError:
            pass
    cur.execute('DELETE FROM generations WHERE user_id = ?', (user_id,))
    cur.execute('DELETE FROM credit_transactions WHERE user_id = ?', (user_id,))
    cur.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
    cur.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
    cur.execute('DELETE FROM oauth_users WHERE user_id = ?', (user_id,))
    cur.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    return jsonify(success=True)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('index'))


@app.route('/session-debug')
def session_debug():
    return dict(session)


@app.route('/delete_image/<int:image_id>', methods=['DELETE'])
@nocache
def delete_image(image_id):
    if 'user_id' not in session:
        return jsonify(success=False, message="User not logged in"), 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT image_path FROM generations WHERE id = ? AND user_id = ?", (image_id, session['user_id']))
    image = cursor.fetchone()

    if image:
        try:
            import os
            image_path = os.path.join("static", image[0])
            if os.path.exists(image_path):
                os.remove(image_path)

            cursor.execute("DELETE FROM generations WHERE id = ?", (image_id,))
            conn.commit()
            return jsonify(success=True)
        except Exception as e:
            conn.rollback()
            print(f"Error deleting image: {e}")
            return jsonify(success=False, message="An error occurred while deleting the image."), 500
        finally:
            conn.close()
    else:
        conn.close()
        return jsonify(success=False, message="Image not found or you don't have permission to delete it."), 404
    
    
# ======= Payment Routes =======
@app.route("/initiate_payment/<plan>")
@nocache
def initiate_payment(plan):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    plans = get_plans()

    if plan not in plans:
        abort(404, "Invalid plan selected")
    
    user_id = session['user_id']
    plan_data = plans[plan]
    
    # Check if user has less than 5 credits before allowing purchase
    user = get_user_by_id(user_id)
    active_sub = get_active_subscription(user_id)
    
    total_credits = 0
    if user and user['credits']:
        total_credits += user['credits']
    if active_sub and active_sub['credits_remaining']:
        total_credits += active_sub['credits_remaining']

    if total_credits >= 4:
        flash("You can only purchase a new plan when you have less than 4 credits remaining. <br> <center><h3>Warning:</h3> old plan will be replaced by new plan</center>", "error")
        return redirect(url_for('add_credits'))

    
    txn_uuid = f"{user_id}-{int(time.time())}"
    
    # Store in session temporarily
    session['payment_info'] = {
        "plan": plan,
        "name": plan_data["name"],
        "credits": plan_data["credits"],
        "amount": plan_data["amount"],
        "txn_uuid": txn_uuid
    }
    
    form_data = {
        "amount": str(plan_data["amount"]),
        "tax_amount": "0",
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "product_code": ESW_PRODUCT_CODE,
        "total_amount": str(plan_data["amount"]),
        "transaction_uuid": txn_uuid,
        "success_url": url_for("esewa_success", _external=True),
        "failure_url": url_for("esewa_failure", _external=True),
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": sign_esewa_payload(str(plan_data["amount"]), txn_uuid),
    }

    # Build auto-submit form
    html = f"""<!DOCTYPE html>
    <html>
    <body>
        <form id="esewa_form" action="{ESW_CHECKOUT_URL}" method="POST">
            {' '.join(f'<input type="hidden" name="{k}" value="{v}">' for k, v in form_data.items())}
        </form>
        <script>document.getElementById('esewa_form').submit();</script>
    </body>
    </html>"""
    return html

@app.route("/esewa/success")
@nocache
def esewa_success():
    b64_data = request.args.get("data", "")
    if not b64_data:
        flash("Missing payment data", "error")
        return redirect(url_for('add_credits'))
    
    try:
        data = verify_esewa_response(b64_data)
    except Exception as e:
        flash(f"Payment verification failed: {str(e)}", "error")
        return redirect(url_for('add_credits'))
    
    payment_info = session.get('payment_info')
    if not payment_info:
        flash("Payment session expired", "error")
        return redirect(url_for('add_credits'))
    
    # Verify transaction matches
    if data['transaction_uuid'] != payment_info['txn_uuid']:
        flash("Transaction mismatch", "error")
        return redirect(url_for('add_credits'))
    
    user_id = session['user_id']
    
    # Get plan details from session instead of global PLANS
    plan_id = payment_info['plan']
    plan_name = payment_info.get('name', plan_id)  # Use name if available, fallback to ID
    credits = payment_info['credits']
    amount = payment_info['amount']
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get current active subscription
        cursor.execute("""
            SELECT id FROM subscriptions 
            WHERE user_id = ? 
            AND status = 'active' 
            AND end_date > datetime('now')
        """, (user_id,))
        current_sub = cursor.fetchone()
        
        # Mark current subscription as replaced if exists
        if current_sub:
            cursor.execute("""
                UPDATE subscriptions 
                SET status = 'replaced' 
                WHERE id = ?
            """, (current_sub[0],))
        
        # Record transaction
        cursor.execute("""
            INSERT INTO transactions 
            (user_id, plan_name, amount, status, pid, ref_id, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            plan_name,
            amount,
            "success",
            payment_info["txn_uuid"],
            data.get("transaction_code"),
            "eSewa"
        ))
        transaction_id = cursor.lastrowid
        
        # Create new subscription
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30)
        
        cursor.execute("""
            INSERT INTO subscriptions 
            (user_id, plan_name, credits_remaining, max_credits, 
             start_date, end_date, transaction_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            plan_name,
            credits,
            credits,
            start_date,
            end_date,
            transaction_id
        ))
        
        conn.commit()
        
        # Clear payment session
        session.pop('payment_info', None)
        
        flash(f"Payment successful! {credits} credits added to your subscription.", "success")
        return redirect(url_for('home'))
    
    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
        flash("An error occurred while processing your payment", "error")
        return redirect(url_for('add_credits'))
    
    finally:
        conn.close()

@app.route("/esewa/failure")
@nocache
def esewa_failure():
    session.pop('payment_info', None)
    flash("Payment failed or was cancelled", "error")
    return redirect(url_for('add_credits'))


if __name__ == "__main__":
    app.run(debug=True)