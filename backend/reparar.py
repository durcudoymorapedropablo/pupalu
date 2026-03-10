"""
╔══════════════════════════════════════════╗
║   SCRIPT DE REPARACIÓN — PUPALU STORE   ║
║   Ejecutar: python reparar.py           ║
╚══════════════════════════════════════════╝

Qué hace este script:
  1. Diagnostica el problema actual
  2. Resetea la base de datos con productos BioGreen
  3. Resetea la contraseña del admin
  4. Verifica que todo funcione

Cómo usarlo:
  Copia este archivo a la misma carpeta donde está app.py y pupalu.db
  Luego ejecuta:  python reparar.py
"""

import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'pupalu.db')

# ── Intentar importar werkzeug ──────────────────────────────────────────────
try:
    from werkzeug.security import generate_password_hash, check_password_hash
    WERKZEUG_OK = True
except ImportError:
    WERKZEUG_OK = False

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
    ('Aromatizante Alma Botanica Haba Tonka Repuesto 330ml', 'Repuesto de aromatizante con fragancia Haba Tonka', 12990, 16, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-04-300x300.webp'),
    ('Difusor de Aromas Capullo de Lino 100ml', 'Difusor de ambiente con delicada fragancia Capullo de Lino', 18990, 13, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-02-300x300.webp'),
    ('Aromatizante Textil y Ambiental Bebe 190ml', 'Suave aromatizante para textiles y ambientes, ideal para bebes', 9990, 20, 'Aromatizantes', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-06-300x300.webp'),
    ('Crema de Manos y Unas Lavanda 75ml', 'Crema hidratante con aceite esencial de lavanda', 19990, 17, 'Aromaterapia', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-07-300x300.webp'),
    ('Emulsion Corporal Lavanda 200ml', 'Emulsion corporal hidratante con lavanda natural', 24990, 12, 'Aromaterapia', 'https://biogreenchile.com/wp-content/uploads/2025/02/26107-08-300x300.webp'),
]

def sep(char='─', n=50):
    print(char * n)

def ok(msg):   print(f"  ✅  {msg}")
def err(msg):  print(f"  ❌  {msg}")
def info(msg): print(f"  ℹ️   {msg}")
def warn(msg): print(f"  ⚠️   {msg}")

print()
sep('═')
print("  PUPALU — DIAGNÓSTICO Y REPARACIÓN")
sep('═')
print()

# ── 1. Verificar entorno ────────────────────────────────────────────────────
print("1. VERIFICANDO ENTORNO")
sep()

info(f"Directorio: {BASE_DIR}")
info(f"Python: {sys.version.split()[0]}")

if WERKZEUG_OK:
    ok("werkzeug instalado")
else:
    err("werkzeug NO está instalado")
    print("\n  Instala con:  pip install werkzeug")
    sys.exit(1)

app_exists = os.path.exists(os.path.join(BASE_DIR, 'app.py'))
index_exists = os.path.exists(os.path.join(BASE_DIR, 'index.html'))
admin_exists_f = os.path.exists(os.path.join(BASE_DIR, 'admin.html'))
db_exists = os.path.exists(DB_PATH)

ok("app.py encontrado") if app_exists else err("app.py NO encontrado en esta carpeta")
ok("index.html encontrado") if index_exists else warn("index.html no encontrado (asegúrate que esté aquí)")
ok("admin.html encontrado") if admin_exists_f else warn("admin.html no encontrado (asegúrate que esté aquí)")
ok(f"pupalu.db encontrada en {DB_PATH}") if db_exists else info("pupalu.db no existe — se creará nueva")

print()

# ── 2. Diagnóstico de la DB ──────────────────────────────────────────────────
print("2. DIAGNÓSTICO DE BASE DE DATOS")
sep()

if db_exists:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        users = c.execute("SELECT username, role FROM users").fetchall()
        info(f"Usuarios en DB: {len(users)}")
        for u in users:
            print(f"      → {u['username']} ({u['role']})")
    except Exception as e:
        err(f"Error leyendo usuarios: {e}")

    try:
        total = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        active = c.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
        info(f"Productos: {total} total, {active} activos")
        sample = c.execute("SELECT name FROM products WHERE active=1 LIMIT 5").fetchall()
        for p in sample:
            print(f"      → {p['name']}")
        if total > 5:
            print(f"      ... y {total - 5} más")
    except Exception as e:
        err(f"Error leyendo productos: {e}")

    conn.close()
else:
    info("Base de datos nueva — se inicializará")

print()

# ── 3. Reparación ────────────────────────────────────────────────────────────
print("3. REPARACIÓN AUTOMÁTICA")
sep()

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Crear tablas si no existen
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

# Reset contraseña admin
NEW_PASSWORD = 'pupalu2026'
c.execute("DELETE FROM users WHERE username='admin'")
c.execute(
    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
    ('admin', generate_password_hash(NEW_PASSWORD), 'admin')
)
ok(f"Usuario admin restablecido con contraseña: {NEW_PASSWORD}")

# Reset productos BioGreen
c.execute("DELETE FROM products")
for p in BIOGREEN_PRODUCTS:
    c.execute(
        "INSERT INTO products (name, description, price, stock, category, image) VALUES (?,?,?,?,?,?)", p
    )
ok(f"{len(BIOGREEN_PRODUCTS)} productos BioGreen cargados")

conn.commit()
conn.close()

print()

# ── 4. Verificación final ────────────────────────────────────────────────────
print("4. VERIFICACIÓN FINAL")
sep()

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

admin_user = c.execute("SELECT * FROM users WHERE username='admin'").fetchone()
prod_count = c.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]

if admin_user and check_password_hash(admin_user['password'], NEW_PASSWORD):
    ok("Login admin verificado correctamente")
else:
    err("Problema con el login admin")

if prod_count == len(BIOGREEN_PRODUCTS):
    ok(f"{prod_count} productos BioGreen verificados en DB")
else:
    err(f"Productos esperados: {len(BIOGREEN_PRODUCTS)}, encontrados: {prod_count}")

conn.close()

print()
sep('═')
print("  ✅  REPARACIÓN COMPLETADA")
sep('═')
print()
print("  Próximos pasos:")
print("  1. Asegúrate que index.html y admin.html están en esta misma carpeta")
print("  2. Reinicia tu servidor (gunicorn / systemctl restart / etc.)")
print()
print("  Credenciales admin:")
print(f"  👤 Usuario:    admin")
print(f"  🔑 Contraseña: {NEW_PASSWORD}")
print()
sep('═')
print()
