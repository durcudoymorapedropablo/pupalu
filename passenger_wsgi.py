import sys, os

# Ajusta esta ruta a donde esté tu app en el servidor
INTERP = os.path.join(os.environ['HOME'], 'virtualenv', 'pupalu', '3.11', 'bin', 'python3')
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, os.path.dirname(__file__))

from app import app as application

# Inicializar DB al arrancar
from app import init_db, os as _os
_os.makedirs('static/uploads', exist_ok=True)
init_db()
