from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, jwt, datetime, os, json
from functools import wraps

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR     = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(ROOT_DIR, 'frontend')
DB_PATH      = os.path.join(ROOT_DIR, 'pupalu.db')

app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=FRONTEND_DIR)
SECRET_KEY = "pupalu_turquesa_2025_secure"

BIOGREEN_PRODUCTS = [
    ('Aceite Esencial Puro Calidez 10ml','Aceite esencial 100% puro, calido y envolvente. Ideal para difusor.',6990,20,'Aceites','https://biogreenchile.com/wp-content/uploads/2025/03/ACEITE-CALIDEZ-801X801-300x300.webp'),
    ('Aceite Esencial Puro de Enebro 10ml','Aceite de enebro 100% puro, purificante y refrescante.',29990,15,'Aceites','https://biogreenchile.com/wp-content/uploads/2025/03/ACEITE-ENEBRO-801X801-300x300.webp'),
    ('Difusor de Aromas Organza 250ml','Difusor de varillas con fragancia Organza floral y sofisticada.',20990,12,'Difusores','https://biogreenchile.com/wp-content/uploads/2025/03/DIFUSOR-ORGANZA-801X801-300x300.webp'),
    ('Aromatizante Textil Organza 250ml','Bruma textil con suave fragancia Organza para ropa y ambientes.',10990,25,'Aromatizantes','https://biogreenchile.com/wp-content/uploads/2025/03/AROMATIZANTE-ORGANZA-801X801-300x300.webp'),
    ('Aromatizante Textil Suenos Pack x4','Pack regalable con 4 brumas aromaticas para textiles.',29990,8,'Regalables','https://biogreenchile.com/wp-content/uploads/2023/11/10308-300x300.jpg'),
    ('Kit Arbol de Higo + Difusor + Bolsa','Set: aceite 10ml + difusor ultrasonico + bolsa regalo.',36980,6,'Regalables','https://biogreenchile.com/wp-content/uploads/2025/03/PROMO-DIA-DE-LA-MADRE-801X801-300x300.webp'),
    ('Caja Perfumeros Inspira x4 Estuche','4 perfumeros 12ml en estuche de regalo coleccion Inspira.',24990,10,'Regalables','https://biogreenchile.com/wp-content/uploads/2025/03/SET-PERFUMEROS-801X801-300x300.webp'),
    ('Regalable Armonia Textil','Pack con bruma textil fragancia Lino, suave y natural.',29590,10,'Regalables','https://biogreenchile.com/wp-content/uploads/2025/02/REGALABLE-LINO-300X300-2-300x300.webp'),
    ('Regalable Nardos y Magnolias','Pack floral con fragancia de nardos y magnolias.',19990,14,'Regalables','https://biogreenchile.com/wp-content/uploads/2025/02/REGALABLE-MAGNOLIA-300X300-300x300.webp'),
    ('Difusor Alma Botanica Canela 250ml','Difusor de aromas con extracto natural Canela de Ceylan.',21990,11,'Difusores','https://biogreenchile.com/wp-content/uploads/2025/02/26107-05-300x300.webp'),
    ('Aromatizante Alma Botanica Canela 330ml','Aromatizante ambiental con autentica fragancia de canela.',12990,18,'Aromatizantes','https://biogreenchile.com/wp-content/uploads/2025/02/26107-01-300x300.webp'),
    ('Aromatizante Haba Tonka Repuesto 330ml','Repuesto aromatizante con fragancia exotica Haba Tonka.',12990,16,'Aromatizantes','https://biogreenchile.com/wp-content/uploads/2025/02/26107-04-300x300.webp'),
    ('Difusor Capullo de Lino 100ml','Difusor con delicada fragancia natural Capullo de Lino.',18990,13,'Difusores','https://biogreenchile.com/wp-content/uploads/2025/02/26107-02-300x300.webp'),
    ('Aromatizante Bebe 190ml','Suave aromatizante textil y ambiental especial para bebes.',9990,20,'Aromatizantes','https://biogreenchile.com/wp-content/uploads/2025/02/26107-06-300x300.webp'),
    ('Crema de Manos Lavanda 75ml','Crema hidratante con aceite esencial de lavanda puro.',19990,17,'Aromaterapia','https://biogreenchile.com/wp-content/uploads/2025/02/26107-07-300x300.webp'),
    ('Emulsion Corporal Lavanda 200ml','Emulsion hidratante corporal con lavanda natural.',24990,12,'Aromaterapia','https://biogreenchile.com/wp-content/uploads/2025/02/26107-08-300x300.webp'),
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT DEFAULT "admin",created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT,price REAL NOT NULL,stock INTEGER DEFAULT 0,category TEXT,image TEXT,active INTEGER DEFAULT 1,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,customer_name TEXT NOT NULL,customer_phone TEXT,customer_email TEXT,customer_address TEXT,items TEXT NOT NULL,total REAL NOT NULL,status TEXT DEFAULT "pendiente",notes TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,product_id INTEGER,quantity INTEGER,price REAL,FOREIGN KEY(order_id) REFERENCES orders(id),FOREIGN KEY(product_id) REFERENCES products(id))''')
    if not c.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",('admin',generate_password_hash('pupalu2026'),'admin'))
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        for p in BIOGREEN_PRODUCTS:
            c.execute("INSERT INTO products(name,description,price,stock,category,image) VALUES(?,?,?,?,?,?)",p)
    conn.commit(); conn.close()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        tok = request.headers.get('Authorization','').replace('Bearer ','')
        if not tok: return jsonify({'error':'Token requerido'}),401
        try:
            data = jwt.decode(tok,SECRET_KEY,algorithms=['HS256'])
            user = data['user']
        except jwt.ExpiredSignatureError: return jsonify({'error':'Token expirado'}),401
        except: return jsonify({'error':'Token invalido'}),401
        return f(user,*args,**kwargs)
    return decorated

@app.after_request
def cors(r):
    r.headers['Access-Control-Allow-Origin']='*'
    r.headers['Access-Control-Allow-Headers']='Content-Type,Authorization'
    r.headers['Access-Control-Allow-Methods']='GET,POST,PUT,DELETE,OPTIONS'
    return r

@app.route('/api/login',methods=['POST','OPTIONS'])
def login():
    if request.method=='OPTIONS': return jsonify({}),200
    d=request.get_json()
    conn=get_db()
    u=conn.execute("SELECT * FROM users WHERE username=?",(d.get('username',''),)).fetchone()
    conn.close()
    if u and check_password_hash(u['password'],d.get('password','')):
        tok=jwt.encode({'user':u['username'],'role':u['role'],'exp':datetime.datetime.utcnow()+datetime.timedelta(hours=12)},SECRET_KEY,algorithm='HS256')
        return jsonify({'token':tok,'username':u['username'],'role':u['role']})
    return jsonify({'error':'Credenciales incorrectas'}),401

@app.route('/api/products')
def get_products():
    conn=get_db()
    rows=conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/products')
@token_required
def admin_products(u):
    conn=get_db()
    rows=conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/products',methods=['POST'])
@token_required
def create_product(u):
    d=request.get_json()
    conn=get_db()
    conn.execute("INSERT INTO products(name,description,price,stock,category,image) VALUES(?,?,?,?,?,?)",(d['name'],d.get('description',''),float(d['price']),int(d.get('stock',0)),d.get('category',''),d.get('image','🌿')))
    conn.commit();conn.close()
    return jsonify({'ok':True}),201

@app.route('/api/admin/products/<int:pid>',methods=['PUT'])
@token_required
def update_product(u,pid):
    d=request.get_json()
    conn=get_db()
    conn.execute("UPDATE products SET name=?,description=?,price=?,stock=?,category=?,image=?,active=? WHERE id=?",(d['name'],d.get('description',''),float(d['price']),int(d['stock']),d.get('category',''),d.get('image','🌿'),int(d.get('active',1)),pid))
    conn.commit();conn.close()
    return jsonify({'ok':True})

@app.route('/api/admin/products/<int:pid>',methods=['DELETE'])
@token_required
def delete_product(u,pid):
    conn=get_db()
    conn.execute("UPDATE products SET active=0 WHERE id=?",(pid,))
    conn.commit();conn.close()
    return jsonify({'ok':True})

@app.route('/api/orders',methods=['POST'])
def create_order():
    d=request.get_json()
    items=d.get('items',[])
    total=sum(i['price']*i['quantity'] for i in items)
    conn=get_db()
    cur=conn.execute("INSERT INTO orders(customer_name,customer_phone,customer_email,customer_address,items,total,notes) VALUES(?,?,?,?,?,?,?)",(d['customer_name'],d.get('customer_phone',''),d.get('customer_email',''),d.get('customer_address',''),json.dumps(items),total,d.get('notes','')))
    oid=cur.lastrowid
    for i in items:
        conn.execute("INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)",(oid,i['id'],i['quantity'],i['price']))
        conn.execute("UPDATE products SET stock=stock-? WHERE id=? AND stock>=?",(i['quantity'],i['id'],i['quantity']))
    conn.commit();conn.close()
    return jsonify({'ok':True,'order_id':oid}),201

@app.route('/api/admin/orders')
@token_required
def get_orders(u):
    conn=get_db()
    rows=conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/orders/<int:oid>',methods=['PUT'])
@token_required
def update_order(u,oid):
    d=request.get_json()
    conn=get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?",(d['status'],oid))
    conn.commit();conn.close()
    return jsonify({'ok':True})

@app.route('/api/admin/stats')
@token_required
def get_stats(u):
    conn=get_db()
    ts=conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='cancelado'").fetchone()[0]
    to=conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    tp=conn.execute("SELECT COUNT(*) FROM orders WHERE status='pendiente'").fetchone()[0]
    tpr=conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
    ls=conn.execute("SELECT COUNT(*) FROM products WHERE stock<=3 AND active=1").fetchone()[0]
    weekly=conn.execute("SELECT DATE(created_at) day,SUM(total) total,COUNT(*) orders FROM orders WHERE created_at>=DATE('now','-7 days') AND status!='cancelado' GROUP BY DATE(created_at) ORDER BY day").fetchall()
    top=conn.execute("SELECT p.name,p.image,SUM(oi.quantity) sold,SUM(oi.quantity*oi.price) revenue FROM order_items oi JOIN products p ON p.id=oi.product_id GROUP BY oi.product_id ORDER BY sold DESC LIMIT 8").fetchall()
    sc=conn.execute("SELECT status,COUNT(*) cnt FROM orders GROUP BY status").fetchall()
    ro=conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5").fetchall()
    conn.close()
    return jsonify({'total_sales':ts,'total_orders':to,'pending':tp,'total_products':tpr,'low_stock':ls,'weekly':[dict(r) for r in weekly],'top_products':[dict(r) for r in top],'status_counts':[dict(r) for r in sc],'recent_orders':[dict(r) for r in ro]})

@app.route('/')
def index(): return send_from_directory(FRONTEND_DIR,'index.html')
@app.route('/admin')
def admin_page(): return send_from_directory(FRONTEND_DIR,'admin.html')

if __name__=='__main__':
    init_db()
    print("\n🌿 PUPALU STORE INICIANDO")
    print("Tienda: http://localhost:5000")
    print("Admin:  http://localhost:5000/admin")
    print("User: admin | Pass: pupalu2026\n")
    app.run(debug=True,port=5000,host='0.0.0.0')
