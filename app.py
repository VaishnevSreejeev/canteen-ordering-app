from flask import Flask, render_template, request, redirect, url_for, g, session, flash
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_very_secret_key_for_canteen_app_stage3_auth')

# --- Database Configuration ---
DATABASE = 'canteen.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
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
        init_admin_user()
        init_default_users()
        init_default_menu_items()

def init_admin_user():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM admins WHERE username = 'chandrettan'")
    if cursor.fetchone() is None:
        hashed_password = generate_password_hash('adminpass', method='pbkdf2:sha256')
        db.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ('chandrettan', hashed_password))
        db.commit()

def init_default_users():
    db = get_db()
    students = [
        ('S001', 'Hari', 'pass123'),
        ('S002', 'Meera', 'pass123'),
        ('S003', 'John', 'pass123')
    ]
    for student_id, name, password in students:
        if db.execute("SELECT id FROM users WHERE student_id = ?", (student_id,)).fetchone() is None:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            db.execute("INSERT INTO users (student_id, name, password) VALUES (?, ?, ?)", (student_id, name, hashed_password))
    db.commit()

def init_default_menu_items():
    db = get_db()
    default_items = [
        ('Meals', 40.0, 200),
        ('Chai', 10.0, 150),
        ('Snacks', 20.0, 100)
    ]
    for name, price, quantity in default_items:
        if db.execute("SELECT id FROM menu_items WHERE name = ?", (name,)).fetchone() is None:
            db.execute("INSERT INTO menu_items (name, price, daily_quantity) VALUES (?, ?, ?)", (name, price, quantity))
    db.commit()

# --- Main Landing Page ---
@app.route('/')
def landing():
    return render_template('landing.html')

# --- Student Routes ---
@app.route('/order')
def index():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    db = get_db()
    menu_items = db.execute(
        "SELECT * FROM menu_items WHERE is_available = 1 AND daily_quantity > 0 ORDER BY name"
    ).fetchall()
    return render_template('index.html', menu_items=menu_items)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id'].strip().upper()
        name = request.form['name'].strip()
        password = request.form['password']
        if not all([student_id, name, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        db = get_db()
        try:
            db.execute("INSERT INTO users (student_id, name, password) VALUES (?, ?, ?)", (student_id, name, hashed_password))
            db.commit()
            flash('Registration successful! Please log in.', 'message')
            return redirect(url_for('student_login'))
        except sqlite3.IntegrityError:
            flash('Student ID already exists.', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if 'student_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        student_id = request.form['student_id'].strip().upper()
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE student_id = ?", (student_id,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['student_id'] = user['student_id']
            session['name'] = user['name']
            flash(f"Welcome back, {user['name']}!", 'message')
            return redirect(url_for('index'))
        else:
            flash('Invalid Student ID or password.', 'error')
    return render_template('student_login.html')

@app.route('/logout')
def logout():
    session.pop('student_id', None)
    session.pop('name', None)
    flash('You have been logged out.', 'message')
    return redirect(url_for('landing'))

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'student_id' not in session:
        flash('Please log in to place an order.', 'error')
        return redirect(url_for('student_login'))
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])
    student_id = session['student_id']
    db = get_db()
    item = db.execute("SELECT * FROM menu_items WHERE name = ? AND is_available = 1", (item_name,)).fetchone()
    if not item:
        flash('This item is not available.', 'error')
        return redirect(url_for('index'))
    if item['daily_quantity'] < quantity:
        flash(f"Sorry, only {item['daily_quantity']} of {item_name} left.", 'error')
        return redirect(url_for('index'))
    total_price = item['price'] * quantity
    try:
        db.execute("BEGIN TRANSACTION")
        db.execute(
            "INSERT INTO orders (student_id, item_name, quantity, total_price, payment_status) VALUES (?, ?, ?, ?, ?)",
            (student_id, item_name, quantity, total_price, 'Unpaid')
        )
        db.execute(
            "UPDATE menu_items SET daily_quantity = daily_quantity - ? WHERE name = ?",
            (quantity, item_name)
        )
        db.commit()
        flash(f'Order for {quantity} x {item_name} placed successfully!', 'message')
    except sqlite3.Error as e:
        db.rollback()
        flash(f'An error occurred: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/order_history')
def order_history():
    if 'student_id' not in session:
        flash('Please log in to view your order history.', 'error')
        return redirect(url_for('student_login'))

    student_id = session['student_id']
    db = get_db()
    orders = db.execute(
        "SELECT id, item_name, quantity, total_price, payment_status, order_date "
        "FROM orders WHERE student_id = ? ORDER BY order_date DESC",
        (student_id,)
    ).fetchall()

    return render_template('order_history.html', orders=orders)

# --- Admin Routes ---
@app.before_request
def admin_auth_check():
    if request.path.startswith('/admin') and request.endpoint not in ['admin_login_page', 'static']:
        if 'admin_logged_in' not in session:
            flash('Please log in to access the admin panel.', 'error')
            return redirect(url_for('admin_login_page'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        admin = db.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        if admin and check_password_hash(admin['password'], password):
            session['admin_logged_in'] = True
            flash('Admin login successful!', 'message')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin username or password.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out from the admin panel.', 'message')
    return redirect(url_for('landing'))

@app.route('/admin')
def admin_dashboard():
    db = get_db()
    today = datetime.date.today().strftime('%Y-%m-%d')
    
    # Fetch individual orders for today
    orders = db.execute(
        "SELECT id, student_id, item_name, quantity, order_date FROM orders WHERE DATE(order_date) = ? ORDER BY order_date DESC",
        (today,)
    ).fetchall()

    # Calculate aggregated demand for today
    aggregated_demand = db.execute(
        "SELECT item_name, SUM(quantity) as total_quantity "
        "FROM orders "
        "WHERE DATE(order_date) = ? "
        "GROUP BY item_name",
        (today,)
    ).fetchall()

    return render_template('admin.html', orders=orders, aggregated_demand=aggregated_demand)

@app.route('/admin/menu')
def admin_menu():
    db = get_db()
    menu_items = db.execute("SELECT * FROM menu_items ORDER BY name").fetchall()
    return render_template('admin_menu.html', menu_items=menu_items)

@app.route('/admin/menu/add', methods=['POST'])
def add_menu_item():
    item_name = request.form['name'].strip()
    price = float(request.form['price'])
    quantity = int(request.form['daily_quantity'])
    db = get_db()
    db.execute("INSERT INTO menu_items (name, price, daily_quantity) VALUES (?, ?, ?)", (item_name, price, quantity))
    db.commit()
    flash(f"'{item_name}' has been added to the menu.", 'message')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_menu_item(item_id):
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        daily_quantity = int(request.form['daily_quantity'])
        is_available = 1 if 'is_available' in request.form else 0
        db.execute(
            "UPDATE menu_items SET name = ?, price = ?, daily_quantity = ?, is_available = ? WHERE id = ?",
            (name, price, daily_quantity, is_available, item_id)
        )
        db.commit()
        flash('Item updated successfully.', 'message')
        return redirect(url_for('admin_menu'))
    item = db.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,)).fetchone()
    return render_template('admin_edit_menu.html', item=item)

@app.route('/admin/menu/toggle_availability/<int:item_id>', methods=['POST'])
def toggle_menu_item_availability(item_id):
    db = get_db()
    item = db.execute("SELECT is_available, name FROM menu_items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        flash('Menu item not found.', 'error')
        return redirect(url_for('admin_menu'))

    new_status = 0 if item['is_available'] == 1 else 1
    status_text = "unavailable" if new_status == 0 else "available"
    try:
        db.execute("UPDATE menu_items SET is_available = ? WHERE id = ?", (new_status, item_id))
        db.commit()
        flash(f"'{item['name']}' is now {status_text}.", 'message')
    except sqlite3.Error as e:
        flash(f"Error toggling availability: {e}", 'error')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/delete/<int:item_id>', methods=['POST'])
def delete_menu_item(item_id):
    db = get_db()
    db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    db.commit()
    flash('Item deleted successfully.', 'message')
    return redirect(url_for('admin_menu'))

if __name__ == '__main__':
    with app.app_context():
        print("Initializing database...")
        init_db()
        print("Database initialization complete.")
    app.run(debug=True)
