# 🌸 Pupalu — Tienda Virtual

## ¿Cómo ejecutar?

### Requisitos
- Python 3.8+
- Flask (`pip install flask`)

### Iniciar el servidor

```bash
cd backend
python app.py
```

### URLs
- 🛍️ **Tienda:** http://localhost:5000
- 🔐 **Admin:** http://localhost:5000/admin

### Credenciales Admin
- **Usuario:** admin
- **Contraseña:** pupalu2024

---

## Estructura del proyecto

```
pupalu/
├── backend/
│   ├── app.py          # Servidor Flask + API REST
│   └── pupalu.db       # Base de datos SQLite (se crea automáticamente)
├── frontend/
│   ├── index.html      # Tienda (cliente)
│   └── admin.html      # Panel administrativo
└── README.md
```

---

## Funcionalidades

### 🛍️ Tienda (index.html)
- Catálogo de productos con filtros por categoría
- Carrito de compras persistente
- Modal de checkout con formulario
- Botón de WhatsApp flotante
- Pedido directo por WhatsApp

### 🔐 Panel Admin (admin.html)
- Login seguro con JWT
- **Dashboard:** ventas totales, pedidos, gráfico de ventas, top productos
- **Pedidos:** listado completo, filtros por estado, actualizar estado, detalle
- **Productos:** CRUD completo, agregar/editar/eliminar
- **Stock:** control de inventario, alertas de stock bajo

### 🔌 API REST (app.py)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /api/login | Autenticación |
| GET | /api/products | Productos públicos |
| POST | /api/orders | Crear pedido |
| GET | /api/admin/products | Productos (admin) |
| POST | /api/admin/products | Crear producto |
| PUT | /api/admin/products/:id | Editar producto |
| DELETE | /api/admin/products/:id | Eliminar producto |
| GET | /api/admin/orders | Ver pedidos |
| PUT | /api/admin/orders/:id | Actualizar estado |
| GET | /api/admin/stats | Estadísticas |

---

## Personalización

### Número de WhatsApp
En `frontend/index.html`, busca:
```javascript
const WHATSAPP_NUMBER = '56900000000';
```
Reemplaza con tu número real (sin + ni espacios).

### Cambiar contraseña admin
En `backend/app.py`, la contraseña por defecto es `pupalu2024`.
Para cambiarla, elimina `pupalu.db` y en `app.py` modifica:
```python
generate_password_hash('TU_NUEVA_CONTRASEÑA')
```

---

*Desarrollado con ❤️ para Pupalu*
