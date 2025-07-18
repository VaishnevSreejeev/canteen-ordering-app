from flask import Flask, render_template, request, redirect, url_for, g, session, flash
from dotenv import load_dotenv
import os
import sqlite3

load_dotenv()  # Loads variables from .env into environment

app = Flask(__name__)
# Use the secret key from .env for session security
app.secret_key = os.getenv('SECRET_KEY', 'default_fallback_key_for_dev_12345')

# --- Database Configuration ---
DATABASE = 'canteen.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # This makes rows behave like dictionaries
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# --- Routes ---

@app.route('/')
def index():
    student_id = session.get('student_id')
    # The render_template function will have access to flashed messages
    return render_template('index.html', student_id=student_id)

@app.route('/login', methods=['POST'])
def login():
    # Strip whitespace and convert to uppercase for consistency
    student_id = request.form['student_id'].strip().upper()
    if not student_id:
        flash('Student ID cannot be empty.', 'error')
        return redirect(url_for('index'))

    db = get_db()
    try:
        # Use INSERT OR IGNORE to create a new user only if they don't exist
        db.execute("INSERT OR IGNORE INTO users (student_id) VALUES (?)", (student_id,))
        db.commit()

        # Now that we know the user exists, set the session
        session['student_id'] = student_id
        flash(f'Welcome, {student_id}!', 'message')
    except sqlite3.Error as e:
        flash(f'Database error during login: {e}', 'error')

    return redirect(url_for('index'))


@app.route('/place_order', methods=['POST'])
def place_order():
    student_id = session.get('student_id')
    if not student_id:
        flash('Please enter your Student ID first.', 'error')
        return redirect(url_for('index'))

    item = request.form.get('item')
    quantity_str = request.form.get('quantity')

    if not item or not quantity_str or not quantity_str.isdigit() or int(quantity_str) <= 0:
        flash('Invalid item or quantity.', 'error')
        return redirect(url_for('index'))

    quantity = int(quantity_str)
    db = get_db()
    try:
        db.execute(
            "INSERT INTO orders (student_id, item, quantity) VALUES (?, ?, ?)",
            (student_id, item, quantity)
        )
        db.commit()
        flash(f'Order for {quantity} x {item} placed successfully!', 'message')
    except sqlite3.Error as e:
        flash(f'Error placing order: {e}', 'error')

    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('student_id', None)
    flash('You have been logged out.', 'message')
    return redirect(url_for('index'))


#chandrettan to display orders
@app.route('/admin')
def admin_dashboard():
    db = get_db()
    # Fetch all orders, ordered by newest first
    orders = db.execute("SELECT * FROM orders ORDER BY order_date DESC").fetchall()
    return render_template('admin.html', orders=orders)


if __name__ == '__main__':
    # Initialize the database if it doesn't exist
    with app.app_context():
        try:
            db = get_db()
            # Check if both tables exist
            db.execute("SELECT 1 FROM users LIMIT 1")
            db.execute("SELECT 1 FROM orders LIMIT 1")
            print("Database tables already exist. Skipping initialization.")
        except sqlite3.OperationalError:
            print("Initializing new database...")
            init_db()
            print("Database initialized.")
    app.run(debug=True)