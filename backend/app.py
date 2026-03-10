from flask import Flask, request, jsonify, send_from_directory, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import jwt
import datetime
import os
import json
from functools import wraps

app = Flask(__name__, static_folder='../frontend/static', template_folder='../frontend')

SECRET_KEY = "pupalu_secret_2024_secure_key"

# ─── CORS ──────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.route('/api/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return jsonify({}), 200


DB_PATH = os.path.join(os.path.dirname(__file__), 'pupalu.db')

# ─── DATABASE SETUP ────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        category TEXT,
        image TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        customer_phone TEXT,
        customer_email TEXT,
        customer_address TEXT,
        items TEXT NOT NULL,
        total REAL NOT NULL,
        status TEXT DEFAULT 'pendiente',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price REAL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )''')

    # Default admin
    admin_exists = c.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not admin_exists:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', generate_password_hash('pupalu2024'), 'admin'))

    # Sample products
    prod_count = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if prod_count == 0:
        sample_products = [
            ('Blusa Floral Rosa', 'Delicada blusa con estampado floral, perfecta para el verano', 35000, 15, 'Blusas', '🌸'),
            ('Falda Midi Lavanda', 'Elegante falda midi en tono lavanda, tela fluida premium', 42000, 10, 'Faldas', '💜'),
            ('Vestido Boho Coral', 'Vestido estilo bohemio en color coral con bordados', 68000, 8, 'Vestidos', '🌺'),
            ('Top Encaje Nude', 'Top con encaje delicado en tono nude, muy versátil', 28000, 20, 'Tops', '🤍'),
            ('Pantalón Rosa Pastel', 'Pantalón palazzo en rosa pastel, comodidad y estilo', 45000, 12, 'Pantalones', '🌷'),
            ('Chaqueta Dusty Rose', 'Chaqueta corta en dusty rose, ideal para looks casuales', 78000, 6, 'Chaquetas', '🌸'),
            ('Vestido Mini Lila', 'Vestido mini en lila con volantes, perfecto para salidas', 52000, 9, 'Vestidos', '💜'),
            ('Blusa Off-Shoulder Blanca', 'Romántica blusa off-shoulder con detalles en encaje', 32000, 18, 'Blusas', '🤍'),
        ]
        for p in sample_products:
            c.execute("INSERT INTO products (name, description, price, stock, category, image) VALUES (?,?,?,?,?,?)", p)

    conn.commit()
    conn.close()

# ─── AUTH DECORATOR ────────────────────────────────────────────────────────────

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token requerido'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = data['user']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except Exception:
            return jsonify({'error': 'Token inválido'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# ─── AUTH ROUTES ───────────────────────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        token = jwt.encode({
            'user': username,
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }, SECRET_KEY, algorithm='HS256')
        return jsonify({'token': token, 'username': username, 'role': user['role']})

    return jsonify({'error': 'Credenciales incorrectas'}), 401

# ─── PRODUCT ROUTES ────────────────────────────────────────────────────────────

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db()
    products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/admin/products', methods=['GET'])
@token_required
def admin_get_products(current_user):
    conn = get_db()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/admin/products', methods=['POST'])
@token_required
def create_product(current_user):
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "INSERT INTO products (name, description, price, stock, category, image) VALUES (?,?,?,?,?,?)",
        (data['name'], data.get('description',''), float(data['price']),
         int(data.get('stock',0)), data.get('category',''), data.get('image','🛍️'))
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto creado'}), 201

@app.route('/api/admin/products/<int:pid>', methods=['PUT'])
@token_required
def update_product(current_user, pid):
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "UPDATE products SET name=?, description=?, price=?, stock=?, category=?, image=?, active=? WHERE id=?",
        (data['name'], data.get('description',''), float(data['price']),
         int(data['stock']), data.get('category',''), data.get('image','🛍️'),
         int(data.get('active', 1)), pid)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto actualizado'})

@app.route('/api/admin/products/<int:pid>', methods=['DELETE'])
@token_required
def delete_product(current_user, pid):
    conn = get_db()
    conn.execute("UPDATE products SET active=0 WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto eliminado'})

# ─── ORDER ROUTES ──────────────────────────────────────────────────────────────

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    items = data.get('items', [])
    total = sum(item['price'] * item['quantity'] for item in items)

    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO orders (customer_name, customer_phone, customer_email, customer_address, items, total, notes) VALUES (?,?,?,?,?,?,?)",
        (data['customer_name'], data.get('customer_phone',''), data.get('customer_email',''),
         data.get('customer_address',''), json.dumps(items), total, data.get('notes',''))
    )
    order_id = cursor.lastrowid

    for item in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?,?,?,?)",
            (order_id, item['id'], item['quantity'], item['price'])
        )
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id=? AND stock >= ?",
            (item['quantity'], item['id'], item['quantity'])
        )

    conn.commit()
    conn.close()
    return jsonify({'message': 'Pedido creado', 'order_id': order_id}), 201

@app.route('/api/admin/orders', methods=['GET'])
@token_required
def get_orders(current_user):
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])

@app.route('/api/admin/orders/<int:oid>', methods=['PUT'])
@token_required
def update_order(current_user, oid):
    data = request.get_json()
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (data['status'], oid))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Pedido actualizado'})

# ─── DASHBOARD STATS ───────────────────────────────────────────────────────────

@app.route('/api/admin/stats', methods=['GET'])
@token_required
def get_stats(current_user):
    conn = get_db()

    total_sales = conn.execute(
        "SELECT COALESCE(SUM(total),0) as total FROM orders WHERE status != 'cancelado'"
    ).fetchone()['total']

    total_orders = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()['c']
    pending_orders = conn.execute("SELECT COUNT(*) as c FROM orders WHERE status='pendiente'").fetchone()['c']
    total_products = conn.execute("SELECT COUNT(*) as c FROM products WHERE active=1").fetchone()['c']
    low_stock = conn.execute("SELECT COUNT(*) as c FROM products WHERE stock <= 3 AND active=1").fetchone()['c']

    # Sales last 7 days
    daily_sales = conn.execute("""
        SELECT DATE(created_at) as day, SUM(total) as total, COUNT(*) as orders
        FROM orders
        WHERE created_at >= DATE('now', '-7 days') AND status != 'cancelado'
        GROUP BY DATE(created_at)
        ORDER BY day
    """).fetchall()

    # Top products
    top_products = conn.execute("""
        SELECT p.name, SUM(oi.quantity) as sold, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        GROUP BY oi.product_id
        ORDER BY sold DESC
        LIMIT 5
    """).fetchall()

    # Orders by status
    status_counts = conn.execute("""
        SELECT status, COUNT(*) as count FROM orders GROUP BY status
    """).fetchall()

    conn.close()

    return jsonify({
        'total_sales': total_sales,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_products': total_products,
        'low_stock': low_stock,
        'daily_sales': [dict(d) for d in daily_sales],
        'top_products': [dict(t) for t in top_products],
        'status_counts': [dict(s) for s in status_counts]
    })

# ─── SERVE FRONTEND ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('../frontend', 'admin.html')

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('../frontend/static', path)

if __name__ == '__main__':
    init_db()
    print("🌸 Pupalu Store iniciando...")
    print("🛍️  Tienda: http://localhost:5000")
    print("🔐 Admin:  http://localhost:5000/admin")
    print("👤 Usuario: admin | Contraseña: pupalu2024")
    app.run(debug=True, port=5000)
