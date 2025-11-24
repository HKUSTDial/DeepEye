#!/usr/bin/env python3
"""Initialize MySQL example database with sample data.

This script creates an example e-commerce database with sample tables and data
for testing database connection and knowledge management features.

Usage:
    python scripts/init_example_mysql.py
    # or
    uv run python scripts/init_example_mysql.py

Database Connection Info:
    Host: localhost
    Port: 3307 (default, can be changed via MYSQL_EXAMPLE_PORT)
    Database: ecommerce_example
    Username: example_user
    Password: example_pass
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pymysql
import os
from datetime import datetime, timedelta
import random


def get_connection_params():
    """Get database connection parameters from environment variables."""
    return {
        "host": os.getenv("MYSQL_EXAMPLE_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_EXAMPLE_PORT", "3307")),
        "database": os.getenv("MYSQL_EXAMPLE_DB", "ecommerce_example"),
        "user": os.getenv("MYSQL_EXAMPLE_USER", "example_user"),
        "password": os.getenv("MYSQL_EXAMPLE_PASSWORD", "example_pass"),
    }


def create_tables(conn):
    """Create example database tables."""
    cursor = conn.cursor()
    
    print("📦 Creating tables...")
    
    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            category_id INT,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            stock_quantity INT DEFAULT 0,
            sku VARCHAR(50) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_category (category_id),
            INDEX idx_sku (sku),
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            full_name VARCHAR(100),
            phone VARCHAR(20),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_username (username),
            INDEX idx_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            order_number VARCHAR(50) UNIQUE NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            shipping_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_order_number (order_number),
            INDEX idx_status (status),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # Order items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT,
            product_id INT,
            quantity INT NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            subtotal DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_order (order_id),
            INDEX idx_product (product_id),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # Add table comments (for knowledge management)
    cursor.execute("ALTER TABLE categories COMMENT = 'Product categories for organizing products'")
    cursor.execute("ALTER TABLE products COMMENT = 'Product catalog with pricing and inventory information'")
    cursor.execute("ALTER TABLE users COMMENT = 'Customer user accounts'")
    cursor.execute("ALTER TABLE orders COMMENT = 'Customer orders with status tracking'")
    cursor.execute("ALTER TABLE order_items COMMENT = 'Individual items within each order'")
    
    # Add column comments
    cursor.execute("ALTER TABLE categories MODIFY COLUMN name VARCHAR(100) COMMENT 'Category name (e.g., Electronics, Clothing)'")
    cursor.execute("ALTER TABLE products MODIFY COLUMN price DECIMAL(10, 2) COMMENT 'Product price in USD'")
    cursor.execute("ALTER TABLE products MODIFY COLUMN stock_quantity INT COMMENT 'Available inventory count'")
    cursor.execute("ALTER TABLE orders MODIFY COLUMN status VARCHAR(20) COMMENT 'Order status: pending, processing, shipped, delivered, cancelled'")
    cursor.execute("ALTER TABLE order_items MODIFY COLUMN subtotal DECIMAL(10, 2) COMMENT 'Calculated as quantity * unit_price'")
    
    conn.commit()
    print("✅ Tables created successfully!")


def insert_sample_data(conn):
    """Insert sample data into tables."""
    cursor = conn.cursor()
    
    print("📊 Inserting sample data...")
    
    # Insert categories
    categories_data = [
        ("Electronics", "Electronic devices and accessories"),
        ("Clothing", "Apparel and fashion items"),
        ("Books", "Books and reading materials"),
        ("Home & Garden", "Home improvement and garden supplies"),
        ("Sports", "Sports equipment and accessories"),
    ]
    cursor.executemany(
        "INSERT INTO categories (name, description) VALUES (%s, %s)",
        categories_data
    )
    category_ids = []
    for cat_data in categories_data:
        cursor.execute("SELECT id FROM categories WHERE name = %s", (cat_data[0],))
        category_ids.append(cursor.fetchone()[0])
    print(f"   ✓ Inserted {len(category_ids)} categories")
    
    # Insert products
    products_data = [
        (category_ids[0], "Laptop Pro 15", "High-performance laptop with 16GB RAM", 1299.99, 50, "LAP-001"),
        (category_ids[0], "Wireless Mouse", "Ergonomic wireless mouse", 29.99, 200, "MOU-001"),
        (category_ids[0], "USB-C Cable", "Fast charging USB-C cable", 19.99, 300, "CAB-001"),
        (category_ids[1], "Cotton T-Shirt", "Comfortable cotton t-shirt", 24.99, 150, "TSH-001"),
        (category_ids[1], "Jeans Classic", "Classic fit denim jeans", 59.99, 80, "JEA-001"),
        (category_ids[1], "Running Shoes", "Lightweight running shoes", 89.99, 60, "SHO-001"),
        (category_ids[2], "Python Programming", "Learn Python programming", 49.99, 100, "BOK-001"),
        (category_ids[2], "Data Science Guide", "Complete guide to data science", 59.99, 75, "BOK-002"),
        (category_ids[3], "Garden Tool Set", "Complete garden tool set", 79.99, 40, "GAR-001"),
        (category_ids[3], "Plant Pot Set", "Decorative ceramic plant pots", 34.99, 90, "GAR-002"),
        (category_ids[4], "Yoga Mat", "Premium yoga mat", 39.99, 120, "SPO-001"),
        (category_ids[4], "Dumbbell Set", "Adjustable dumbbell set", 149.99, 30, "SPO-002"),
    ]
    cursor.executemany(
        """INSERT INTO products (category_id, name, description, price, stock_quantity, sku)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        products_data
    )
    product_ids = []
    for prod_data in products_data:
        cursor.execute("SELECT id FROM products WHERE sku = %s", (prod_data[5],))
        product_ids.append(cursor.fetchone()[0])
    print(f"   ✓ Inserted {len(product_ids)} products")
    
    # Insert users
    users_data = [
        ("alice", "alice@example.com", "Alice Johnson", "555-0101", "123 Main St, City, State 12345"),
        ("bob", "bob@example.com", "Bob Smith", "555-0102", "456 Oak Ave, City, State 12345"),
        ("charlie", "charlie@example.com", "Charlie Brown", "555-0103", "789 Pine Rd, City, State 12345"),
        ("diana", "diana@example.com", "Diana Prince", "555-0104", "321 Elm St, City, State 12345"),
        ("eve", "eve@example.com", "Eve Williams", "555-0105", "654 Maple Dr, City, State 12345"),
    ]
    cursor.executemany(
        """INSERT INTO users (username, email, full_name, phone, address)
           VALUES (%s, %s, %s, %s, %s)""",
        users_data
    )
    user_ids = []
    for user_data in users_data:
        cursor.execute("SELECT id FROM users WHERE username = %s", (user_data[0],))
        user_ids.append(cursor.fetchone()[0])
    print(f"   ✓ Inserted {len(user_ids)} users")
    
    # Insert orders
    orders_data = []
    order_numbers = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(15):
        user_id = random.choice(user_ids)
        order_date = base_date + timedelta(days=random.randint(0, 30))
        order_number = f"ORD-{order_date.strftime('%Y%m%d')}-{i+1:04d}"
        order_numbers.append(order_number)
        status = random.choice(["pending", "processing", "shipped", "delivered", "cancelled"])
        orders_data.append((
            user_id,
            order_number,
            round(random.uniform(50, 500), 2),
            status,
            f"Shipping address for order {order_number}",
            order_date,
            order_date,
        ))
    
    cursor.executemany(
        """INSERT INTO orders (user_id, order_number, total_amount, status, shipping_address, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        orders_data
    )
    order_ids = []
    for order_num in order_numbers:
        cursor.execute("SELECT id FROM orders WHERE order_number = %s", (order_num,))
        order_ids.append(cursor.fetchone()[0])
    print(f"   ✓ Inserted {len(order_ids)} orders")
    
    # Insert order items
    order_items_data = []
    for order_id, order_num in zip(order_ids, order_numbers):
        num_items = random.randint(1, 5)
        selected_products = random.sample(list(zip(product_ids, products_data)), num_items)
        
        for product_id, product_info in selected_products:
            quantity = random.randint(1, 3)
            unit_price = product_info[3]  # price
            subtotal = round(quantity * unit_price, 2)
            order_items_data.append((
                order_id,
                product_id,
                quantity,
                unit_price,
                subtotal,
            ))
    
    cursor.executemany(
        """INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
           VALUES (%s, %s, %s, %s, %s)""",
        order_items_data
    )
    print(f"   ✓ Inserted {len(order_items_data)} order items")
    
    conn.commit()
    print("✅ Sample data inserted successfully!")


def main():
    """Main function to initialize example database."""
    print("🚀 DeepEye - MySQL Example Database Initialization")
    print("=" * 60)
    print()
    
    params = get_connection_params()
    
    print(f"🔗 Connecting to MySQL example database...")
    print(f"   Host: {params['host']}")
    print(f"   Port: {params['port']}")
    print(f"   Database: {params['database']}")
    print(f"   User: {params['user']}")
    print()
    
    try:
        # Connect to MySQL
        conn = pymysql.connect(**params)
        
        print("✅ Connected successfully!")
        print()
        
        # Create tables
        create_tables(conn)
        print()
        
        # Insert sample data
        insert_sample_data(conn)
        print()
        
        # Display summary
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM categories")
        cat_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM products")
        prod_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM order_items")
        item_count = cursor.fetchone()[0]
        
        print("📊 Database Summary:")
        print(f"   Categories: {cat_count}")
        print(f"   Products: {prod_count}")
        print(f"   Users: {user_count}")
        print(f"   Orders: {order_count}")
        print(f"   Order Items: {item_count}")
        print()
        
        print("💡 Connection Information for DeepEye:")
        print(f"   Type: mysql")
        print(f"   Host: {params['host']}")
        print(f"   Port: {params['port']}")
        print(f"   Database: {params['database']}")
        print(f"   Username: {params['user']}")
        print(f"   Password: {params['password']}")
        print()
        
        print("✨ Example database initialized successfully!")
        
        cursor.close()
        conn.close()
        
    except pymysql.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("💡 Make sure the MySQL example container is running:")
        print("   docker-compose up -d mysql-example")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

