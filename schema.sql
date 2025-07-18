-- Drop existing tables to ensure a clean slate
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS admins;
DROP TABLE IF EXISTS menu_items;

-- Table for student users with login credentials
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password TEXT NOT NULL
);

-- Table for admin users
CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- Table for menu items with daily stock
CREATE TABLE menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    price REAL NOT NULL,
    is_available INTEGER NOT NULL DEFAULT 1, -- 1 for true (available), 0 for false
    daily_quantity INTEGER NOT NULL DEFAULT 0 -- The available quantity for the day
);

-- Table for orders placed by students with payment status
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    item_name TEXT NOT NULL, -- This was likely 'item' before
    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,
    payment_status TEXT NOT NULL,
    order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users (student_id)
);