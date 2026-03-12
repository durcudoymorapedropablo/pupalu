from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from zoneinfo import ZoneInfo
import sqlite3, os, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'pupalu_secret_key_2025'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB

ALLOWED_IMAGE = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
TZ = ZoneInfo('America/Santiago')

def now_cl():
    return datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')

def today_cl():
    return datetime.now(TZ).date().isoformat()

# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect('pupalu.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT DEFAULT 'cliente',
            telefono TEXT,
            direccion TEXT,
            activo INTEGER DEFAULT 1,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            imagen TEXT,
            activo INTEGER DEFAULT 1,
            orden INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            precio REAL NOT NULL,
            precio_oferta REAL,
            stock INTEGER DEFAULT 0,
            categoria_id INTEGER,
            imagen TEXT,
            imagenes TEXT DEFAULT '[]',
            destacado INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        );

        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            usuario_id INTEGER,
            nombre_cliente TEXT NOT NULL,
            email_cliente TEXT NOT NULL,
            telefono TEXT,
            direccion TEXT NOT NULL,
            ciudad TEXT NOT NULL,
            region TEXT,
            total REAL NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            metodo_pago TEXT DEFAULT 'transferencia',
            notas TEXT,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS pedido_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            nombre_producto TEXT NOT NULL,
            precio_unitario REAL NOT NULL,
            cantidad INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        );

        CREATE TABLE IF NOT EXISTS resenas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            usuario_id INTEGER,
            nombre TEXT NOT NULL,
            calificacion INTEGER NOT NULL CHECK(calificacion BETWEEN 1 AND 5),
            comentario TEXT,
            aprobada INTEGER DEFAULT 0,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS favoritos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, producto_id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        );

        CREATE TABLE IF NOT EXISTS cupones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            tipo TEXT DEFAULT 'porcentaje',
            valor REAL NOT NULL,
            minimo_compra REAL DEFAULT 0,
            usos_max INTEGER DEFAULT 100,
            usos_actual INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            fecha_expira TEXT
        );

        CREATE TABLE IF NOT EXISTS banners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            subtitulo TEXT,
            imagen TEXT,
            link TEXT,
            activo INTEGER DEFAULT 1,
            orden INTEGER DEFAULT 0
        );
    ''')

    # Datos de ejemplo
    admin = db.execute("SELECT id FROM usuarios WHERE email='admin@pupalu.cl'").fetchone()
    if not admin:
        db.execute("INSERT INTO usuarios (nombre,email,password,rol) VALUES (?,?,?,?)",
            ('Administradora','admin@pupalu.cl', generate_password_hash('pupalu2025'), 'admin'))

        # Categorías
        cats = [
            ('Ropa','ropa','Prendas femeninas con estilo único'),
            ('Accesorios','accesorios','Complementos para cada look'),
            ('Bolsos','bolsos','Bolsos y carteras'),
            ('Joyería','joyeria','Collares, aretes y pulseras'),
        ]
        for c in cats:
            db.execute("INSERT OR IGNORE INTO categorias (nombre,slug,descripcion,activo,orden) VALUES (?,?,?,1,0)", c)

        # Productos de ejemplo
        prods = [
            ('Blusa Floral Turquesa','blusa-floral-turquesa','Blusa liviana con estampado floral en tonos turquesa. Perfecta para el verano.',24990,None,15,1,1),
            ('Falda Midi Blanca','falda-midi-blanca','Falda elegante de tela fluida, corte midi. Versátil y atemporal.',29990,22990,8,1,1),
            ('Vestido Boho Verde','vestido-boho-verde','Vestido estilo bohemio con detalles bordados. Ideal para ocasiones especiales.',45990,None,5,1,1),
            ('Collar Perlas Naturales','collar-perlas','Collar artesanal con perlas de agua dulce y cierre dorado.',18990,None,20,4,1),
            ('Aretes Turquesa','aretes-turquesa','Aretes colgantes con piedras turquesa genuinas. Hecho a mano.',12990,9990,30,4,1),
            ('Bolso Tote Lino','bolso-tote-lino','Bolso de lino natural con asa de cuero. Espacioso y elegante.',34990,None,10,3,1),
            ('Pañuelo Seda Floral','panuelo-seda','Pañuelo de seda con estampado floral. Úsalo en el cabello o el cuello.',9990,None,25,2,0),
            ('Cartera Mini Turquesa','cartera-mini','Cartera pequeña en cuero vegano color turquesa con cadena dorada.',27990,24990,7,3,1),
        ]
        for p in prods:
            db.execute('''INSERT OR IGNORE INTO productos
                (nombre,slug,descripcion,precio,precio_oferta,stock,categoria_id,destacado,activo)
                VALUES (?,?,?,?,?,?,?,?,?)''', p)

        # Cupón de ejemplo
        db.execute("INSERT OR IGNORE INTO cupones (codigo,tipo,valor,minimo_compra,activo) VALUES (?,?,?,?,?)",
            ('PUPALU10','porcentaje',10,15000,1))

    db.commit()
    db.close()

# ── HELPERS ───────────────────────────────────────────────────────────────────

def allowed_img(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_IMAGE

def save_image(file, prefix='img'):
    if not file or file.filename == '' or not allowed_img(file.filename):
        return None
    ext = file.filename.rsplit('.',1)[1].lower()
    fname = f"{prefix}_{datetime.now(TZ).strftime('%Y%m%d%H%M%S')}.{ext}"
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    return fname

def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session or session.get('rol') != 'admin':
            flash('Acceso restringido.', 'error')
            return redirect(url_for('index'))
        return f(*a, **kw)
    return d

def get_carrito():
    return session.get('carrito', {})

def total_carrito():
    carrito = get_carrito()
    return sum(v['precio'] * v['cantidad'] for v in carrito.values())

def items_carrito():
    return sum(v['cantidad'] for v in get_carrito().values())

app.jinja_env.globals.update(
    items_carrito=items_carrito,
    total_carrito=total_carrito,
    get_carrito=get_carrito
)

# ── TIENDA PÚBLICA ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    destacados = db.execute(
        "SELECT p.*, c.nombre as cat_nombre FROM productos p LEFT JOIN categorias c ON p.categoria_id=c.id WHERE p.destacado=1 AND p.activo=1 LIMIT 8"
    ).fetchall()
    categorias = db.execute("SELECT * FROM categorias WHERE activo=1 ORDER BY orden").fetchall()
    ofertas = db.execute(
        "SELECT * FROM productos WHERE precio_oferta IS NOT NULL AND activo=1 LIMIT 4"
    ).fetchall()
    banners = db.execute("SELECT * FROM banners WHERE activo=1 ORDER BY orden").fetchall()
    db.close()
    return render_template('index.html', destacados=destacados, categorias=categorias,
                           ofertas=ofertas, banners=banners)

@app.route('/tienda')
def tienda():
    db = get_db()
    q = request.args.get('q', '')
    cat_slug = request.args.get('categoria', '')
    orden = request.args.get('orden', 'reciente')
    precio_min = request.args.get('precio_min', '')
    precio_max = request.args.get('precio_max', '')

    query = '''SELECT p.*, c.nombre as cat_nombre FROM productos p
               LEFT JOIN categorias c ON p.categoria_id=c.id WHERE p.activo=1'''
    params = []

    if q:
        query += ' AND (p.nombre LIKE ? OR p.descripcion LIKE ?)'
        params += [f'%{q}%', f'%{q}%']
    if cat_slug:
        query += ' AND c.slug=?'
        params.append(cat_slug)
    if precio_min:
        query += ' AND p.precio >= ?'
        params.append(float(precio_min))
    if precio_max:
        query += ' AND p.precio <= ?'
        params.append(float(precio_max))

    orden_sql = {
        'reciente': 'p.fecha_creacion DESC',
        'precio_asc': 'p.precio ASC',
        'precio_desc': 'p.precio DESC',
        'nombre': 'p.nombre ASC'
    }.get(orden, 'p.fecha_creacion DESC')
    query += f' ORDER BY {orden_sql}'

    productos = db.execute(query, params).fetchall()
    categorias = db.execute("SELECT * FROM categorias WHERE activo=1 ORDER BY orden").fetchall()
    categoria_actual = db.execute("SELECT * FROM categorias WHERE slug=?", (cat_slug,)).fetchone() if cat_slug else None
    db.close()
    return render_template('tienda.html', productos=productos, categorias=categorias,
                           categoria_actual=categoria_actual, q=q, orden=orden,
                           precio_min=precio_min, precio_max=precio_max)

@app.route('/producto/<slug>')
def producto(slug):
    db = get_db()
    prod = db.execute('''SELECT p.*, c.nombre as cat_nombre FROM productos p
        LEFT JOIN categorias c ON p.categoria_id=c.id WHERE p.slug=? AND p.activo=1''', (slug,)).fetchone()
    if not prod:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('tienda'))
    resenas = db.execute(
        "SELECT * FROM resenas WHERE producto_id=? AND aprobada=1 ORDER BY fecha DESC", (prod['id'],)
    ).fetchall()
    relacionados = db.execute(
        "SELECT * FROM productos WHERE categoria_id=? AND id!=? AND activo=1 LIMIT 4",
        (prod['categoria_id'], prod['id'])
    ).fetchall()
    # Favorito
    es_favorito = False
    if 'user_id' in session:
        fav = db.execute("SELECT id FROM favoritos WHERE usuario_id=? AND producto_id=?",
            (session['user_id'], prod['id'])).fetchone()
        es_favorito = fav is not None
    db.close()
    return render_template('producto.html', prod=prod, resenas=resenas,
                           relacionados=relacionados, es_favorito=es_favorito)

# ── CARRITO ───────────────────────────────────────────────────────────────────

@app.route('/carrito')
def carrito():
    carrito = get_carrito()
    db = get_db()
    # Actualizar precios desde DB
    items = []
    for slug, item in carrito.items():
        prod = db.execute("SELECT * FROM productos WHERE slug=?", (slug,)).fetchone()
        if prod:
            precio = prod['precio_oferta'] if prod['precio_oferta'] else prod['precio']
            items.append({**dict(prod), 'cantidad': item['cantidad'], 'precio_actual': precio,
                          'subtotal': precio * item['cantidad']})
    db.close()
    total = sum(i['subtotal'] for i in items)
    return render_template('carrito.html', items=items, total=total)

@app.route('/carrito/agregar/<slug>', methods=['POST'])
def agregar_carrito(slug):
    cantidad = int(request.form.get('cantidad', 1))
    db = get_db()
    prod = db.execute("SELECT * FROM productos WHERE slug=? AND activo=1", (slug,)).fetchone()
    db.close()
    if not prod:
        flash('Producto no disponible.', 'error')
        return redirect(url_for('tienda'))
    carrito = get_carrito()
    precio = prod['precio_oferta'] if prod['precio_oferta'] else prod['precio']
    if slug in carrito:
        carrito[slug]['cantidad'] = min(carrito[slug]['cantidad'] + cantidad, prod['stock'])
    else:
        carrito[slug] = {'nombre': prod['nombre'], 'precio': precio,
                         'imagen': prod['imagen'], 'cantidad': cantidad, 'stock': prod['stock']}
    session['carrito'] = carrito
    flash(f'"{prod["nombre"]}" agregado al carrito. 🛍️', 'success')
    return redirect(request.referrer or url_for('tienda'))

@app.route('/carrito/actualizar', methods=['POST'])
def actualizar_carrito():
    slug = request.form.get('slug')
    cantidad = int(request.form.get('cantidad', 1))
    carrito = get_carrito()
    if slug in carrito:
        if cantidad <= 0:
            del carrito[slug]
        else:
            carrito[slug]['cantidad'] = cantidad
    session['carrito'] = carrito
    return redirect(url_for('carrito'))

@app.route('/carrito/eliminar/<slug>', methods=['POST'])
def eliminar_carrito(slug):
    carrito = get_carrito()
    carrito.pop(slug, None)
    session['carrito'] = carrito
    return redirect(url_for('carrito'))

@app.route('/carrito/vaciar', methods=['POST'])
def vaciar_carrito():
    session['carrito'] = {}
    return redirect(url_for('carrito'))

# ── CHECKOUT ──────────────────────────────────────────────────────────────────

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    carrito = get_carrito()
    if not carrito:
        flash('Tu carrito está vacío.', 'error')
        return redirect(url_for('tienda'))

    if request.method == 'POST':
        db = get_db()
        # Calcular total
        total = 0
        items_data = []
        for slug, item in carrito.items():
            prod = db.execute("SELECT * FROM productos WHERE slug=?", (slug,)).fetchone()
            if prod:
                precio = prod['precio_oferta'] if prod['precio_oferta'] else prod['precio']
                subtotal = precio * item['cantidad']
                total += subtotal
                items_data.append((prod, item['cantidad'], precio, subtotal))

        # Aplicar cupón
        cupon_codigo = request.form.get('cupon', '').upper().strip()
        descuento = 0
        if cupon_codigo:
            cupon = db.execute(
                "SELECT * FROM cupones WHERE codigo=? AND activo=1", (cupon_codigo,)
            ).fetchone()
            if cupon and (not cupon['fecha_expira'] or cupon['fecha_expira'] >= today_cl()):
                if total >= cupon['minimo_compra']:
                    if cupon['tipo'] == 'porcentaje':
                        descuento = total * cupon['valor'] / 100
                    else:
                        descuento = cupon['valor']
                    db.execute("UPDATE cupones SET usos_actual=usos_actual+1 WHERE id=?", (cupon['id'],))

        total_final = total - descuento

        # Número de pedido
        ultimo = db.execute("SELECT numero FROM pedidos ORDER BY id DESC LIMIT 1").fetchone()
        num = 1
        if ultimo:
            try: num = int(ultimo['numero'].split('-')[-1]) + 1
            except: pass
        numero = f"PPL-{datetime.now(TZ).year}-{num:04d}"

        # Crear pedido
        db.execute('''INSERT INTO pedidos (numero, usuario_id, nombre_cliente, email_cliente,
            telefono, direccion, ciudad, region, total, metodo_pago, notas, fecha, fecha_actualizacion)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
            numero,
            session.get('user_id'),
            request.form['nombre'],
            request.form['email'],
            request.form.get('telefono', ''),
            request.form['direccion'],
            request.form['ciudad'],
            request.form.get('region', ''),
            total_final,
            request.form.get('metodo_pago', 'transferencia'),
            request.form.get('notas', ''),
            now_cl(), now_cl()
        ))
        pedido_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        for prod, cantidad, precio, subtotal in items_data:
            db.execute('''INSERT INTO pedido_items
                (pedido_id, producto_id, nombre_producto, precio_unitario, cantidad, subtotal)
                VALUES (?,?,?,?,?,?)''',
                (pedido_id, prod['id'], prod['nombre'], precio, cantidad, subtotal))
            db.execute("UPDATE productos SET stock=stock-? WHERE id=?", (cantidad, prod['id']))

        db.commit()
        db.close()
        session['carrito'] = {}
        session['ultimo_pedido'] = numero
        flash(f'¡Pedido {numero} realizado con éxito! Te contactaremos pronto. 💚', 'success')
        return redirect(url_for('confirmacion'))

    # Prefill si está logueada
    user = None
    if 'user_id' in session:
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE id=?", (session['user_id'],)).fetchone()
        db.close()

    db = get_db()
    items = []
    total = 0
    for slug, item in carrito.items():
        prod = db.execute("SELECT * FROM productos WHERE slug=?", (slug,)).fetchone()
        if prod:
            precio = prod['precio_oferta'] if prod['precio_oferta'] else prod['precio']
            sub = precio * item['cantidad']
            items.append({**dict(prod), 'cantidad': item['cantidad'], 'subtotal': sub})
            total += sub
    db.close()
    return render_template('checkout.html', items=items, total=total, user=user)

@app.route('/confirmacion')
def confirmacion():
    numero = session.get('ultimo_pedido')
    return render_template('confirmacion.html', numero=numero)

@app.route('/api/cupon', methods=['POST'])
def verificar_cupon():
    codigo = request.json.get('codigo', '').upper().strip()
    total = float(request.json.get('total', 0))
    db = get_db()
    cupon = db.execute("SELECT * FROM cupones WHERE codigo=? AND activo=1", (codigo,)).fetchone()
    db.close()
    if not cupon:
        return jsonify({'ok': False, 'mensaje': 'Cupón no válido'})
    if cupon['fecha_expira'] and cupon['fecha_expira'] < today_cl():
        return jsonify({'ok': False, 'mensaje': 'Cupón expirado'})
    if total < cupon['minimo_compra']:
        return jsonify({'ok': False, 'mensaje': f'Mínimo ${cupon["minimo_compra"]:,.0f} para usar este cupón'})
    descuento = total * cupon['valor'] / 100 if cupon['tipo'] == 'porcentaje' else cupon['valor']
    return jsonify({'ok': True, 'descuento': descuento, 'tipo': cupon['tipo'], 'valor': cupon['valor'],
                    'mensaje': f'Cupón aplicado: {cupon["valor"]}{"%" if cupon["tipo"]=="porcentaje" else "$"} de descuento'})

# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        db = get_db()
        u = db.execute("SELECT * FROM usuarios WHERE email=? AND activo=1", (request.form['email'],)).fetchone()
        db.close()
        if u and check_password_hash(u['password'], request.form['password']):
            session.update({'user_id': u['id'], 'nombre': u['nombre'], 'rol': u['rol'], 'email': u['email']})
            flash(f'¡Bienvenida, {u["nombre"]}! 💚', 'success')
            return redirect(request.args.get('next') or url_for('index'))
        flash('Email o contraseña incorrectos.', 'error')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        db = get_db()
        try:
            db.execute("INSERT INTO usuarios (nombre,email,password,telefono) VALUES (?,?,?,?)", (
                request.form['nombre'], request.form['email'],
                generate_password_hash(request.form['password']),
                request.form.get('telefono', '')
            ))
            db.commit()
            u = db.execute("SELECT * FROM usuarios WHERE email=?", (request.form['email'],)).fetchone()
            session.update({'user_id': u['id'], 'nombre': u['nombre'], 'rol': u['rol'], 'email': u['email']})
            flash('¡Cuenta creada! Bienvenida a Pupalu 💚', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Ese email ya está registrado.', 'error')
        finally:
            db.close()
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/mi-cuenta')
@login_required
def mi_cuenta():
    db = get_db()
    user = db.execute("SELECT * FROM usuarios WHERE id=?", (session['user_id'],)).fetchone()
    pedidos = db.execute("SELECT * FROM pedidos WHERE usuario_id=? ORDER BY fecha DESC", (session['user_id'],)).fetchall()
    favoritos = db.execute('''SELECT p.* FROM favoritos f JOIN productos p ON f.producto_id=p.id
        WHERE f.usuario_id=? AND p.activo=1''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('mi_cuenta.html', user=user, pedidos=pedidos, favoritos=favoritos)

@app.route('/favorito/<int:prod_id>', methods=['POST'])
@login_required
def toggle_favorito(prod_id):
    db = get_db()
    fav = db.execute("SELECT id FROM favoritos WHERE usuario_id=? AND producto_id=?",
        (session['user_id'], prod_id)).fetchone()
    if fav:
        db.execute("DELETE FROM favoritos WHERE id=?", (fav['id'],))
        msg = 'Eliminado de favoritos'
    else:
        db.execute("INSERT INTO favoritos (usuario_id, producto_id, fecha) VALUES (?,?,?)",
            (session['user_id'], prod_id, now_cl()))
        msg = 'Agregado a favoritos 💚'
    db.commit()
    db.close()
    flash(msg, 'success')
    return redirect(request.referrer or url_for('tienda'))

@app.route('/resena/<int:prod_id>', methods=['POST'])
def agregar_resena(prod_id):
    db = get_db()
    db.execute("INSERT INTO resenas (producto_id, usuario_id, nombre, calificacion, comentario, fecha) VALUES (?,?,?,?,?,?)",
        (prod_id, session.get('user_id'), request.form['nombre'],
         int(request.form['calificacion']), request.form.get('comentario',''), now_cl()))
    db.commit()
    db.close()
    flash('Gracias por tu reseña. Será revisada pronto. 💚', 'success')
    return redirect(request.referrer or url_for('tienda'))

# ── ADMIN ─────────────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        'total_pedidos': db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0],
        'pedidos_pendientes': db.execute("SELECT COUNT(*) FROM pedidos WHERE estado='pendiente'").fetchone()[0],
        'total_productos': db.execute("SELECT COUNT(*) FROM productos WHERE activo=1").fetchone()[0],
        'total_clientes': db.execute("SELECT COUNT(*) FROM usuarios WHERE rol='cliente'").fetchone()[0],
        'ventas_hoy': db.execute("SELECT COALESCE(SUM(total),0) FROM pedidos WHERE fecha LIKE ?", (today_cl()+'%',)).fetchone()[0],
        'ventas_mes': db.execute("SELECT COALESCE(SUM(total),0) FROM pedidos WHERE fecha LIKE ?", (today_cl()[:7]+'%',)).fetchone()[0],
    }
    pedidos_recientes = db.execute("SELECT * FROM pedidos ORDER BY fecha DESC LIMIT 8").fetchall()
    productos_sin_stock = db.execute("SELECT * FROM productos WHERE stock=0 AND activo=1").fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats,
                           pedidos_recientes=pedidos_recientes,
                           productos_sin_stock=productos_sin_stock)

@app.route('/admin/productos')
@admin_required
def admin_productos():
    db = get_db()
    productos = db.execute('''SELECT p.*, c.nombre as cat_nombre FROM productos p
        LEFT JOIN categorias c ON p.categoria_id=c.id ORDER BY p.fecha_creacion DESC''').fetchall()
    categorias = db.execute("SELECT * FROM categorias WHERE activo=1 ORDER BY nombre").fetchall()
    db.close()
    return render_template('admin/productos.html', productos=productos, categorias=categorias)

@app.route('/admin/productos/nuevo', methods=['POST'])
@admin_required
def admin_nuevo_producto():
    db = get_db()
    imagen = save_image(request.files.get('imagen'), 'prod')
    nombre = request.form['nombre']
    slug = nombre.lower().replace(' ', '-').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    db.execute('''INSERT INTO productos (nombre,slug,descripcion,precio,precio_oferta,stock,
        categoria_id,imagen,destacado,activo,fecha_creacion) VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (
        nombre, slug, request.form.get('descripcion',''),
        float(request.form['precio']),
        float(request.form['precio_oferta']) if request.form.get('precio_oferta') else None,
        int(request.form.get('stock', 0)),
        request.form.get('categoria_id') or None,
        imagen,
        1 if request.form.get('destacado') else 0,
        1 if request.form.get('activo') else 0,
        now_cl()
    ))
    db.commit()
    db.close()
    flash('Producto creado.', 'success')
    return redirect(url_for('admin_productos'))

@app.route('/admin/productos/<int:pid>/editar', methods=['POST'])
@admin_required
def admin_editar_producto(pid):
    db = get_db()
    imagen = save_image(request.files.get('imagen'), 'prod')
    if not imagen:
        prod = db.execute("SELECT imagen FROM productos WHERE id=?", (pid,)).fetchone()
        imagen = prod['imagen'] if prod else None
    db.execute('''UPDATE productos SET nombre=?,descripcion=?,precio=?,precio_oferta=?,
        stock=?,categoria_id=?,imagen=?,destacado=?,activo=? WHERE id=?''', (
        request.form['nombre'], request.form.get('descripcion',''),
        float(request.form['precio']),
        float(request.form['precio_oferta']) if request.form.get('precio_oferta') else None,
        int(request.form.get('stock', 0)),
        request.form.get('categoria_id') or None,
        imagen,
        1 if request.form.get('destacado') else 0,
        1 if request.form.get('activo') else 0,
        pid
    ))
    db.commit()
    db.close()
    flash('Producto actualizado.', 'success')
    return redirect(url_for('admin_productos'))

@app.route('/admin/productos/<int:pid>/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_producto(pid):
    db = get_db()
    db.execute("UPDATE productos SET activo=0 WHERE id=?", (pid,))
    db.commit()
    db.close()
    flash('Producto eliminado.', 'success')
    return redirect(url_for('admin_productos'))

@app.route('/admin/pedidos')
@admin_required
def admin_pedidos():
    db = get_db()
    estado = request.args.get('estado', '')
    q = "SELECT * FROM pedidos"
    p = []
    if estado:
        q += " WHERE estado=?"
        p.append(estado)
    q += " ORDER BY fecha DESC"
    pedidos = db.execute(q, p).fetchall()
    db.close()
    return render_template('admin/pedidos.html', pedidos=pedidos, estado_filter=estado)

@app.route('/admin/pedidos/<int:pid>')
@admin_required
def admin_ver_pedido(pid):
    db = get_db()
    pedido = db.execute("SELECT * FROM pedidos WHERE id=?", (pid,)).fetchone()
    items = db.execute("SELECT * FROM pedido_items WHERE pedido_id=?", (pid,)).fetchall()
    db.close()
    return render_template('admin/ver_pedido.html', pedido=pedido, items=items)

@app.route('/admin/pedidos/<int:pid>/estado', methods=['POST'])
@admin_required
def admin_estado_pedido(pid):
    db = get_db()
    db.execute("UPDATE pedidos SET estado=?, fecha_actualizacion=? WHERE id=?",
        (request.form['estado'], now_cl(), pid))
    db.commit()
    db.close()
    flash('Estado actualizado.', 'success')
    return redirect(url_for('admin_pedidos'))

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    db = get_db()
    users = db.execute("SELECT * FROM usuarios ORDER BY rol, nombre").fetchall()
    db.close()
    return render_template('admin/usuarios.html', users=users)

@app.route('/admin/resenas')
@admin_required
def admin_resenas():
    db = get_db()
    resenas = db.execute('''SELECT r.*, p.nombre as prod_nombre FROM resenas r
        JOIN productos p ON r.producto_id=p.id ORDER BY r.fecha DESC''').fetchall()
    db.close()
    return render_template('admin/resenas.html', resenas=resenas)

@app.route('/admin/resenas/<int:rid>/aprobar', methods=['POST'])
@admin_required
def admin_aprobar_resena(rid):
    db = get_db()
    db.execute("UPDATE resenas SET aprobada=1 WHERE id=?", (rid,))
    db.commit()
    db.close()
    return redirect(url_for('admin_resenas'))

@app.route('/admin/resenas/<int:rid>/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_resena(rid):
    db = get_db()
    db.execute("DELETE FROM resenas WHERE id=?", (rid,))
    db.commit()
    db.close()
    return redirect(url_for('admin_resenas'))

@app.route('/admin/cupones')
@admin_required
def admin_cupones():
    db = get_db()
    cupones = db.execute("SELECT * FROM cupones ORDER BY id DESC").fetchall()
    db.close()
    return render_template('admin/cupones.html', cupones=cupones)

@app.route('/admin/cupones/nuevo', methods=['POST'])
@admin_required
def admin_nuevo_cupon():
    db = get_db()
    try:
        db.execute("INSERT INTO cupones (codigo,tipo,valor,minimo_compra,usos_max,activo,fecha_expira) VALUES (?,?,?,?,?,?,?)", (
            request.form['codigo'].upper(), request.form.get('tipo','porcentaje'),
            float(request.form['valor']), float(request.form.get('minimo_compra', 0)),
            int(request.form.get('usos_max', 100)),
            1 if request.form.get('activo') else 0,
            request.form.get('fecha_expira') or None
        ))
        db.commit()
        flash('Cupón creado.', 'success')
    except sqlite3.IntegrityError:
        flash('Ese código ya existe.', 'error')
    db.close()
    return redirect(url_for('admin_cupones'))

@app.route('/admin/categorias')
@admin_required
def admin_categorias():
    db = get_db()
    cats = db.execute("SELECT c.*, COUNT(p.id) as num_productos FROM categorias c LEFT JOIN productos p ON c.id=p.categoria_id GROUP BY c.id ORDER BY c.orden").fetchall()
    db.close()
    return render_template('admin/categorias.html', categorias=cats)

@app.route('/admin/categorias/nueva', methods=['POST'])
@admin_required
def admin_nueva_categoria():
    db = get_db()
    nombre = request.form['nombre']
    slug = nombre.lower().replace(' ','-').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    imagen = save_image(request.files.get('imagen'), 'cat')
    try:
        db.execute("INSERT INTO categorias (nombre,slug,descripcion,imagen,activo,orden) VALUES (?,?,?,?,?,?)",
            (nombre, slug, request.form.get('descripcion',''), imagen,
             1 if request.form.get('activo') else 0, int(request.form.get('orden',0))))
        db.commit()
        flash('Categoría creada.', 'success')
    except sqlite3.IntegrityError:
        flash('Esa categoría ya existe.', 'error')
    db.close()
    return redirect(url_for('admin_categorias'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    init_db()
    app.run(debug=True)
