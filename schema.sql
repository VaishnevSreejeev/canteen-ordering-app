-- Drop tables if they exist to start fresh on each initialization.
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS orders;

-- Users table to store student IDs
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL
);

-- Orders table to store simple orders
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    item TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users (student_id)
);