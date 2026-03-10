from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import jwt
import datetime
import os
import json
from functools import wraps

# ── Sirve los HTML desde la misma carpeta que app.py ──────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, template_folder=BASE_DIR)

SECRET_KEY = "pupalu_secret_2024_secure_key"
DB_PATH = os.path.join(BASE_DIR, 'pupalu.db')

# ─── DATABASE SETUP ────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

BIOGREEN_PRODUCTS = [
    ('Aceite Esencial Puro Calidez 10ml', 'Aceite esencial puro, ideal para difusores y aromaterapia', 6990, 20, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/03/ACEITE-CALIDEZ-801X801-300x300.webp'),
    ('Aceite Esencial Puro de Enebro 10ml', 'Aceite esencial de enebro 100% puro para aromaterapia y bienestar', 29990, 15, 'Aromaterapia', 'https://biogreenchile.com/wp-content/uploads/2025/03/ACEITE-ENEBRO-801X801-300x300.webp'),
    ('Difusor de Aromas Organza 250ml', 'Difusor de ambiente con fragancia Organza, elegante y duradero', 20990, 12, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/03/DIFUSOR-ORGANZA-801X801-300x300.webp'),
    ('Aromatizante Textil Organza 250ml', 'Aromatizante para telas y ambientes con suave fragancia Organza', 10990, 25, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/03/AROMATIZANTE-ORGANZA-801X801-300x300.webp'),
    ('Aromatizante Textil Suenos Pack Regalable x4', 'Pack regalable con 4 brumas aromaticas textiles', 29990, 8, 'Regalables', 'https://biogreenchile.com/wp-content/uploads/2023/11/10308-300x300.jpg'),
    ('Aceite Arbol de Higo + Difusor Ultrasonico + Bolsa', 'Kit completo: aceite 10ml + difusor ultrasonico + bolsa de regalo', 36980, 6, 'Regalables', 'https://biogreenchile.com/wp-content/uploads/2025/03/PROMO-DIA-DE-LA-MADRE-801X801-300x300.webp'),
    ('Caja Perfumeros Inspira x4 En Estuche', '4 perfumeros 12ml en estuche de regalo, coleccion Inspira', 24990, 10, 'Regalables', 'https://biogreenchile.com/wp-content/uploads/2025/03/SET-PERFUMEROS-801X801-300x300.webp'),
    ('Regalable Armonia Textil', 'Pack regalable con aromatizante textil y fragancia Lino', 29590, 10, 'Regalables', 'https://biogreenchile.com/wp-content/uploads/2025/02/REGALABLE-LINO-300X300-2-300x300.webp'),
    ('Regalable Nardos y Magnolias', 'Pack regalable con fragancia floral de nardos y magnolias', 19990, 14, 'Regalables', 'https://biogreenchile.com/wp-content/uploads/2025/02/REGALABLE-MAGNOLIA-300X300-300x300.webp'),
    ('Difusor Alma Botanica Canela de Ceylan 250ml', 'Difusor de aromas con extracto natural de Canela de Ceylan', 21990, 11, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-05-300x300.webp'),
    ('Aromatizante Alma Botanica Canela de Ceylan 330ml', 'Aromatizante ambiental con fragancia natural de canela', 12990, 18, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-01-300x300.webp'),
    ('Aromatizante Alma Botanica Haba Tonka Repuesto 330ml', 'Repuesto de aromatizante con fragancia Haba Tonka, exotica y calida', 12990, 16, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-04-300x300.webp'),
    ('Difusor de Aromas Capullo de Lino 100ml', 'Difusor de ambiente con delicada fragancia Capullo de Lino', 18990, 13, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-02-300x300.webp'),
    ('Aromatizante Textil y Ambiental Bebe 190ml', 'Suave aromatizante para textiles y ambientes, ideal para bebes', 9990, 20, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-06-300x300.webp'),
    ('Crema de Manos y Unas Lavanda 75ml', 'Crema hidratante con aceite esencial de lavanda para manos y unas', 19990, 17, 'Aromaterapia', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-07-300x300.webp'),
    ('Emulsion Corporal Lavanda 200ml', 'Emulsion corporal hidratante con lavanda natural, textura ligera', 24990, 12, 'Aromaterapia', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-08-300x300.webp'),
]

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

    # Admin por defecto
    admin_exists = c.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not admin_exists:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', generate_password_hash('pupalu2026'), 'admin'))

    # ── Forzar carga de productos BioGreen ──────────────────────────────────
    # Si no hay productos BioGreen, los inserta (borra los de muestra si los hay)
    biogreen_exists = c.execute(
        "SELECT COUNT(*) FROM products WHERE name LIKE '%Aceite Esencial%' OR name LIKE '%Difusor%' OR name LIKE '%Aromatizante%'"
    ).fetchone()[0]

    if biogreen_exists == 0:
        # Eliminar productos de muestra (blusas, vestidos, etc.) si existen
        c.execute("DELETE FROM products WHERE name LIKE '%Blusa%' OR name LIKE '%Falda%' OR name LIKE '%Vestido%' OR name LIKE '%Top %' OR name LIKE '%Pantalon%' OR name LIKE '%Chaqueta%'")
        for p in BIOGREEN_PRODUCTS:
            c.execute("INSERT INTO products (name, description, price, stock, category, image) VALUES (?,?,?,?,?,?)", p)
        print(f"✅ {len(BIOGREEN_PRODUCTS)} productos BioGreen cargados.")
    else:
        print(f"✅ Productos BioGreen ya existen en la base de datos.")

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
            return jsonify({'error': 'Token invalido'}), 401
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
         int(data.get('stock',0)), data.get('category',''), data.get('image','🌿'))
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
         int(data['stock']), data.get('category',''), data.get('image','🌿'),
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
    daily_sales = conn.execute("""
        SELECT DATE(created_at) as day, SUM(total) as total, COUNT(*) as orders
        FROM orders
        WHERE created_at >= DATE('now', '-7 days') AND status != 'cancelado'
        GROUP BY DATE(created_at) ORDER BY day
    """).fetchall()
    top_products = conn.execute("""
        SELECT p.name, SUM(oi.quantity) as sold, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi JOIN products p ON p.id = oi.product_id
        GROUP BY oi.product_id ORDER BY sold DESC LIMIT 5
    """).fetchall()
    status_counts = conn.execute(
        "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
    ).fetchall()
    conn.close()
    return jsonify({
        'total_sales': total_sales, 'total_orders': total_orders,
        'pending_orders': pending_orders, 'total_products': total_products,
        'low_stock': low_stock,
        'daily_sales': [dict(d) for d in daily_sales],
        'top_products': [dict(t) for t in top_products],
        'status_counts': [dict(s) for s in status_counts]
    })

# ─── SERVE FRONTEND (desde la misma carpeta que app.py) ───────────────────────

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory(BASE_DIR, 'admin.html')

# ─── ENDPOINT PARA RECARGAR PRODUCTOS BIOGREEN (útil si ya existía la DB) ─────
@app.route('/api/admin/reload-products', methods=['POST'])
@token_required
def reload_products(current_user):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE active=1")
    for p in BIOGREEN_PRODUCTS:
        c.execute("INSERT INTO products (name, description, price, stock, category, image) VALUES (?,?,?,?,?,?)", p)
    conn.commit()
    conn.close()
    return jsonify({'message': f'{len(BIOGREEN_PRODUCTS)} productos BioGreen recargados'}), 200

if __name__ == '__main__':
    init_db()
    print("\n🌿 ========================")
    print("   Pupalu Store iniciando")
    print("   ========================")
    print(f"🛍️  Tienda: http://localhost:5000")
    print(f"🔐 Admin:  http://localhost:5000/admin")
    print(f"👤 Usuario: admin")
    print(f"🔑 Contraseña: pupalu2026")
    print("========================\n")
    app.run(debug=True, port=5000, host='0.0.0.0')
