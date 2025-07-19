from flask import Flask, render_template, request, redirect, url_for, g, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
import datetime
import threading
import logging
import time

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_very_secret_key_for_canteen_app_stage3_auth')

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Database Configuration ---
DATABASE = '/tmp/canteen.db'
db_init_lock = threading.Lock()

# --- Database Functions (Revised for Concurrency) ---

def init_db(db):
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    init_admin_user(db)
    init_default_users(db)
    init_default_menu_items(db)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        with db_init_lock:
            cursor = g.db.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                init_db(g.db)
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Data Initialization Functions ---
def init_admin_user(db):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM admins WHERE username = 'chandrettan'")
    if cursor.fetchone() is None:
        hashed_password = generate_password_hash('adminpass', method='pbkdf2:sha256')
        db.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ('chandrettan', hashed_password))
    db.commit()

def init_default_users(db):
    students = [('S001', 'Hari', 'pass123'), ('S002', 'Meera', 'pass123'), ('S003', 'John', 'pass123')]
    for student_id, name, password in students:
        if db.execute("SELECT id FROM users WHERE student_id = ?", (student_id,)).fetchone() is None:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            db.execute("INSERT INTO users (student_id, name, password) VALUES (?, ?, ?)", (student_id, name, hashed_password))
    db.commit()

def init_default_menu_items(db):
    default_items = [('Meals', 40.0, 200), ('Chai', 10.0, 150), ('Snacks', 20.0, 100)]
    for name, price, quantity in default_items:
        if db.execute("SELECT id FROM menu_items WHERE name = ?", (name,)).fetchone() is None:
            db.execute("INSERT INTO menu_items (name, price, daily_quantity) VALUES (?, ?, ?)", (name, price, quantity))
    db.commit()

# --- Main & Auth Routes ---
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if 'student_id' in session: return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            student_id = request.form['student_id'].strip().upper()
            password = request.form['password']
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE student_id = ?", (student_id,)).fetchone()
            if user and check_password_hash(user['password'], password):
                session['student_id'] = user['student_id']
                session['name'] = user['name']
                session['cart'] = {}
                flash(f"Welcome back, {user['name']}!", 'message')
                return redirect(url_for('index'))
            else:
                flash('Invalid Student ID or password.', 'error')
        except Exception as e:
            app.logger.error(f"Error during login: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
    return render_template('student_login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'message')
    return redirect(url_for('landing'))

# --- Student Ordering & Cart Routes ---
@app.route('/order')
def index():
    if 'student_id' not in session: return redirect(url_for('student_login'))
    try:
        db = get_db()
        menu_items = db.execute("SELECT * FROM menu_items WHERE is_available = 1 AND daily_quantity > 0 ORDER BY name").fetchall()
        return render_template('index.html', menu_items=menu_items)
    except Exception as e:
        app.logger.error(f"Database error on menu page: {e}")
        flash("Could not load menu due to a database error. Please try again.", "error")
        return render_template('index.html', menu_items=[])

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if 'student_id' not in session: return redirect(url_for('student_login'))
    try:
        item_id = request.form.get('item_id', type=int)
        quantity_to_add = request.form.get('quantity', type=int)
        if not all([item_id, quantity_to_add]) or quantity_to_add < 1:
            flash('Invalid item or quantity.', 'error')
            return redirect(url_for('index'))
        
        db = get_db()
        item = db.execute("SELECT name, daily_quantity FROM menu_items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            flash('Item not found.', 'error')
            return redirect(url_for('index'))

        cart = session.get('cart', {})
        current_cart_quantity = cart.get(str(item_id), {'quantity': 0})['quantity']
        new_total_quantity = current_cart_quantity + quantity_to_add

        if new_total_quantity > item['daily_quantity']:
            flash(f"Not enough stock for {item['name']}. Only {item['daily_quantity']} available, you have {current_cart_quantity} in cart.", 'error')
            return redirect(url_for('index'))

        cart[str(item_id)] = {'name': item['name'], 'quantity': new_total_quantity}
        session['cart'] = cart
        flash(f"Updated cart: {new_total_quantity} x {item['name']}.", "message")
    except Exception as e:
        app.logger.error(f"Database error adding to cart: {e}")
        flash("Could not add item to cart due to a database error.", "error")
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    if 'student_id' not in session: return redirect(url_for('student_login'))
    cart = session.get('cart', {})
    if not cart:
        return render_template('cart.html', cart_items=[], total_price=0)
    try:
        db = get_db()
        cart_items = []
        total_price = 0
        for item_id_str, details in cart.items():
            item = db.execute("SELECT price FROM menu_items WHERE id = ?", (int(item_id_str),)).fetchone()
            if item:
                price = item['price'] * details['quantity']
                total_price += price
                cart_items.append({'id': item_id_str, 'name': details['name'], 'quantity': details['quantity'], 'price': price})
        return render_template('cart.html', cart_items=cart_items, total_price=total_price)
    except Exception as e:
        app.logger.error(f"Database error viewing cart: {e}")
        flash("Could not display cart due to a database error.", "error")
        return render_template('cart.html', cart_items=[], total_price=0)

@app.route('/cart/remove/<item_id>')
def remove_from_cart(item_id):
    if 'student_id' not in session: return redirect(url_for('student_login'))
    cart = session.get('cart', {})
    if item_id in cart:
        del cart[item_id]
        session['cart'] = cart
        flash("Item removed from cart.", "message")
    return redirect(url_for('view_cart'))

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'student_id' not in session: return redirect(url_for('student_login'))
    cart = session.get('cart', {})
    if not cart:
        flash("Cannot place an empty order.", "error")
        return redirect(url_for('view_cart'))

    db = get_db()
    try:
        with db:
            items_to_process = []
            total_price = 0
            for item_id_str, details in cart.items():
                item_id = int(item_id_str)
                item = db.execute("SELECT name, price FROM menu_items WHERE id = ?", (item_id,)).fetchone()
                if not item:
                    raise ValueError(f"Item {details.get('name', '')} is no longer on the menu.")
                total_price += item['price'] * details['quantity']
                items_to_process.append({
                    'id': item_id, 'name': item['name'],
                    'price': item['price'], 'quantity': details['quantity']
                })

            cursor = db.execute("INSERT INTO orders (student_id, total_price) VALUES (?, ?)", (session['student_id'], total_price))
            order_id = cursor.lastrowid

            for item_data in items_to_process:
                update_cursor = db.execute(
                    "UPDATE menu_items SET daily_quantity = daily_quantity - ? WHERE id = ? AND daily_quantity >= ?",
                    (item_data['quantity'], item_data['id'], item_data['quantity'])
                )
                if update_cursor.rowcount == 0:
                    raise ValueError(f"Not enough stock for {item_data['name']}. Order cancelled.")
                db.execute("INSERT INTO order_items (order_id, item_name, quantity, price_at_order) VALUES (?, ?, ?, ?)",
                           (order_id, item_data['name'], item_data['quantity'], item_data['price']))

        session['cart'] = {}
        flash("Order placed successfully!", "message")
        # FIX: Redirect to the main menu to avoid the race condition with order_history.
        return redirect(url_for('index'))

    except (sqlite3.Error, ValueError) as e:
        app.logger.error(f"Error during place_order: {e}")
        flash(f"Order failed: {e}", "error")
        return redirect(url_for('view_cart'))

@app.route('/order_history')
def order_history():
    if 'student_id' not in session: return redirect(url_for('student_login'))
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db = get_db()
            orders_list = db.execute("SELECT * FROM orders WHERE student_id = ? ORDER BY order_date DESC", (session['student_id'],)).fetchall()
            
            if not orders_list:
                return render_template('order_history.html', orders_with_items=[])

            orders_dict = {order['id']: {'order': dict(order), 'items': []} for order in orders_list}
            order_ids = tuple(orders_dict.keys())

            if not order_ids:
                return render_template('order_history.html', orders_with_items=[])

            placeholders = ','.join('?' for _ in order_ids)
            items_list = db.execute(f"SELECT * FROM order_items WHERE order_id IN ({placeholders})", order_ids).fetchall()

            for item in items_list:
                if item['order_id'] in orders_dict:
                    orders_dict[item['order_id']]['items'].append(dict(item))

            orders_with_items = list(orders_dict.values())
            
            # Success, return the rendered template
            return render_template('order_history.html', orders_with_items=orders_with_items)

        except sqlite3.OperationalError as e:
            app.logger.warning(f"Attempt {attempt + 1} failed for order_history: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1)  # Wait 100ms before retrying
            else:
                app.logger.error(f"All {max_retries} retries failed for order_history: {e}")
                return render_template('order_history.html', 
                                       orders_with_items=[], 
                                       error="Could not load order history due to a persistent database issue. Please try again later.")
        except Exception as e:
            app.logger.error(f"Unexpected error in order_history: {e}")
            return render_template('order_history.html', 
                                   orders_with_items=[], 
                                   error="An unexpected error occurred while loading order history.")
    # Fallback in case loop finishes unexpectedly
    return render_template('order_history.html', 
                           orders_with_items=[], 
                           error="Could not load order history. Please try again.")

# --- Admin Routes ---
@app.before_request
def admin_auth_check():
    if request.path.startswith('/admin') and request.endpoint not in ['admin_login_page', 'static']:
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login_page'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login_page():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            db = get_db()
            admin = db.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
            if admin and check_password_hash(admin['password'], password):
                session['admin_logged_in'] = True
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin username or password.', 'error')
        except Exception as e:
            app.logger.error(f"Database error during admin login: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('landing'))

@app.route('/admin')
def admin_dashboard():
    try:
        db = get_db()
        orders = db.execute("SELECT o.*, u.name as student_name FROM orders o JOIN users u ON o.student_id = u.student_id ORDER BY o.order_date DESC").fetchall()
        return render_template('admin.html', orders=orders)
    except Exception as e:
        app.logger.error(f"Database error on admin dashboard: {e}")
        flash("Could not load orders due to a database error.", "error")
        return render_template('admin.html', orders=[])

@app.route('/admin/order/<int:order_id>')
def admin_order_details(order_id):
    try:
        db = get_db()
        order = db.execute("SELECT o.*, u.name as student_name FROM orders o JOIN users u ON o.student_id = u.student_id WHERE o.id = ?", (order_id,)).fetchone()
        if not order:
            flash("Order not found", "error")
            return redirect(url_for('admin_dashboard'))
        items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        return render_template('admin_order_details.html', order=order, items=items)
    except Exception as e:
        app.logger.error(f"Database error fetching order details: {e}")
        flash("Could not load order details due to a database error.", "error")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/order/update_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    new_status = request.form.get('status')
    if new_status not in ['Pending', 'Completed', 'Cancelled']:
        flash("Invalid status.", "error")
        return redirect(url_for('admin_order_details', order_id=order_id))
    
    db = get_db()
    try:
        with db:
            db.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        flash(f"Order #{order_id} status updated to {new_status}.", "message")
    except sqlite3.Error as e:
        app.logger.error(f"Error updating order status: {e}")
        flash(f"Database error: {e}", "error")
    return redirect(url_for('admin_order_details', order_id=order_id))

@app.route('/admin/menu')
def admin_menu():
    try:
        db = get_db()
        menu_items = db.execute("SELECT * FROM menu_items ORDER BY name").fetchall()
        return render_template('admin_menu.html', menu_items=menu_items)
    except Exception as e:
        app.logger.error(f"Database error on admin menu: {e}")
        flash("Could not load menu items due to a database error.", "error")
        return render_template('admin_menu.html', menu_items=[])

@app.route('/admin/menu/add', methods=['POST'])
def add_menu_item():
    db = get_db()
    try:
        with db:
            item_name = request.form['name'].strip()
            price = float(request.form['price'])
            quantity = int(request.form['daily_quantity'])
            db.execute("INSERT INTO menu_items (name, price, daily_quantity) VALUES (?, ?, ?)", (item_name, price, quantity))
        flash(f"'{item_name}' has been added to the menu.", 'message')
    except (sqlite3.Error, ValueError) as e:
        app.logger.error(f"Error adding menu item: {e}")
        flash(f"Error adding item: {e}", 'error')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_menu_item(item_id):
    db = get_db()
    if request.method == 'POST':
        try:
            with db:
                name = request.form['name']
                price = float(request.form['price'])
                daily_quantity = int(request.form['daily_quantity'])
                is_available = 1 if 'is_available' in request.form else 0
                db.execute(
                    "UPDATE menu_items SET name = ?, price = ?, daily_quantity = ?, is_available = ? WHERE id = ?",
                    (name, price, daily_quantity, is_available, item_id)
                )
            flash('Item updated successfully.', 'message')
            return redirect(url_for('admin_menu'))
        except (sqlite3.Error, ValueError) as e:
            app.logger.error(f"Error editing menu item: {e}")
            flash(f"Error updating item: {e}", 'error')
    
    try:
        item = db.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            flash('Item not found.', 'error')
            return redirect(url_for('admin_menu'))
        return render_template('admin_edit_menu.html', item=item)
    except Exception as e:
        app.logger.error(f"Error fetching item for edit: {e}")
        flash("Could not load item details due to a database error.", "error")
        return redirect(url_for('admin_menu'))

@app.route('/admin/menu/delete/<int:item_id>', methods=['POST'])
def delete_menu_item(item_id):
    db = get_db()
    try:
        with db:
            db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        flash('Item deleted successfully.', 'message')
    except sqlite3.Error as e:
        app.logger.error(f"Error deleting menu item: {e}")
        flash(f"Database error: {e}", 'error')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/toggle_availability/<int:item_id>', methods=['POST'])
def toggle_menu_item_availability(item_id):
    db = get_db()
    try:
        with db:
            item = db.execute("SELECT is_available, name FROM menu_items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                raise ValueError('Menu item not found.')
            new_status = 0 if item['is_available'] == 1 else 1
            db.execute("UPDATE menu_items SET is_available = ? WHERE id = ?", (new_status, item_id))
            status_text = "unavailable" if new_status == 0 else "available"
            flash(f"'{item['name']}' is now {status_text}.", 'message')
    except (sqlite3.Error, ValueError) as e:
        app.logger.error(f"Error toggling availability: {e}")
        flash(f"Error toggling availability: {e}", 'error')
    return redirect(url_for('admin_menu'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
