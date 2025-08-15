import sqlite3
from pathlib import Path

DB_PATH = "db/dataset.db"  
def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

   
    # Create tables
    #Stores basic user info.
    cursor.execute('''
                    
            CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE,
        password TEXT NOT NULL,
        credits INTEGER DEFAULT 3,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        verified BOOLEAN NOT NULL DEFAULT 0
    );''')

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')

    
# Stores user-generated images and prompts.
    cursor.execute('''
       CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    prompt TEXT,
    image_path TEXT,
    aspect_ratio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

    ''')
    
# Logs credit usage or top-up history
  
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_name TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            pid TEXT NOT NULL,
            ref_id TEXT,
            payment_method TEXT DEFAULT 'eSewa',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_name TEXT NOT NULL,
            credits_remaining INTEGER NOT NULL,
            max_credits INTEGER NOT NULL,
            start_date DATETIME NOT NULL,
            end_date DATETIME NOT NULL,
            status TEXT DEFAULT 'active',
            transaction_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    ''')
# If you're using email/OTP/Google OAuth
    cursor.execute('''
       CREATE TABLE IF NOT EXISTS pending_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    otp TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


    ''')
    
# Stores OAuth user data for third-party logins (e.g., Google)    
    cursor.execute('''
      CREATE TABLE IF NOT EXISTS oauth_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,        -- e.g., "google"
    provider_user_id TEXT UNIQUE,  -- e.g., Google sub ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);


    ''')
    
    # Stores admin user data for admin panel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Stores subscription plans
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY, -- e.g., 'basic', 'pro'
            name TEXT NOT NULL,
            credits INTEGER NOT NULL,
            amount REAL NOT NULL,
            active BOOLEAN NOT NULL DEFAULT 1
        );
    ''')


    conn.commit()
    conn.close()
    
    
## function to get user data through user_id ### used in home page
def get_user_by_id(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
## function to get image promts, aspect ratio and image path through user_id ### used in library page
def get_generations_by_user_id(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM generations WHERE user_id = ?', (user_id,))
    generations = cursor.fetchall()
    conn.close()
    return generations

def get_all_plans():
    """Fetch all active plans from the database."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, credits, amount FROM plans WHERE active = 1")
    plans_list = cursor.fetchall()
    conn.close()
    
    plans_dict = {plan['id']: dict(plan) for plan in plans_list}
    return plans_dict
