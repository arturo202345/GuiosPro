from pathlib import Path
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Carga de .env local (solo desarrollo; en Render se usan variables de entorno) ---
_env_file = BASE_DIR / '.env'
if _env_file.is_file():
    with _env_file.open(encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                _val = _v.strip().strip('"').strip("'")
                if _val:
                    os.environ.setdefault(_k.strip(), _val)

# --- Seguridad básica ---
SECRET_KEY_DESARROLLO = 'development-only-change-before-deploy'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', SECRET_KEY_DESARROLLO)
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

if not DEBUG and SECRET_KEY == SECRET_KEY_DESARROLLO:
    raise ImproperlyConfigured('Defina DJANGO_SECRET_KEY cuando DJANGO_DEBUG=0.')

# --- Hosts y orígenes (Render define RENDER_EXTERNAL_HOSTNAME automáticamente) ---
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
    if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    x.strip()
    for x in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if x.strip()
]

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    _origin = f'https://{RENDER_EXTERNAL_HOSTNAME}'
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)

# --- Apps y middleware ---
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'evaluaciones',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'evaluaciones.context_processors.user_role',
        ],
    },
}]

WSGI_APPLICATION = 'config.wsgi.application'

# --- Base de datos ---
# Render PostgreSQL: configure DATABASE_URL (Internal Database URL).
# SQLite solo para desarrollo local.
_db_url = (os.getenv('DATABASE_URL') or '').strip()
if not _db_url:
    _db_url = 'sqlite:///' + str(BASE_DIR / 'db.sqlite3')

DATABASES = {
    'default': dj_database_url.parse(
        _db_url,
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=bool(os.getenv('DATABASE_URL'))
        and not DEBUG
        and os.getenv('DB_SSL_REQUIRE', '0') == '1',
    )
}

# --- HTTPS / cookies (Render termina TLS en su proxy) ---
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = (not DEBUG) and os.getenv('DJANGO_SSL_REDIRECT', '1') == '1'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# --- Archivos estáticos ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
WHITENOISE_MANIFEST_STRICT = False

# --- Validación de contraseñas ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internacionalización ---
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Autenticación ---
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'login'

# --- Gemini / IA ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
# Tiempo máximo (ms) por llamada a Gemini y límite de consultas de IA por usuario y hora.
GEMINI_TIMEOUT_MS = int(os.environ.get('GEMINI_TIMEOUT_MS', '30000'))
IA_LIMITE_POR_HORA = int(os.environ.get('IA_LIMITE_POR_HORA', '30'))