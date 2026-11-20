from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured
BASE_DIR=Path(__file__).resolve().parent.parent

_env_file = BASE_DIR / '.env'
if _env_file.is_file():
    with _env_file.open(encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                _val = _v.strip()
                if _val:
                    os.environ.setdefault(_k.strip(), _val)
SECRET_KEY_DESARROLLO='development-only-change-before-deploy'
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY',SECRET_KEY_DESARROLLO)
DEBUG=os.environ.get('DJANGO_DEBUG','1')=='1'
if not DEBUG and SECRET_KEY==SECRET_KEY_DESARROLLO:
    raise ImproperlyConfigured('Defina DJANGO_SECRET_KEY cuando DJANGO_DEBUG=0.')
ALLOWED_HOSTS=os.environ.get('DJANGO_ALLOWED_HOSTS','127.0.0.1,localhost').split(',')
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','evaluaciones']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','evaluaciones.context_processors.user_role']}}]
WSGI_APPLICATION='config.wsgi.application'
# Render PostgreSQL: configure DATABASE_URL (Internal Database URL).
# SQLite remains available for local development only.
import dj_database_url
_db_url = os.getenv('DATABASE_URL')
if not _db_url or not _db_url.strip():
    _db_url = 'sqlite:///' + str(BASE_DIR / 'db.sqlite3')
DATABASES = {'default': dj_database_url.parse(_db_url, conn_max_age=600, conn_health_checks=True, ssl_require=bool(os.getenv('DATABASE_URL')) and not DEBUG and os.getenv('DB_SSL_REQUIRE', '0') == '1')}
CSRF_TRUSTED_ORIGINS=[x.strip() for x in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS','').split(',') if x.strip()]
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
STATIC_ROOT=BASE_DIR/'staticfiles'
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
AUTH_PASSWORD_VALIDATORS=[
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE='es'
TIME_ZONE='America/Guayaquil'
USE_I18N=True
USE_TZ=True
STATIC_URL='static/'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'

LOGIN_URL='login'
LOGIN_REDIRECT_URL='inicio'
LOGOUT_REDIRECT_URL='login'

GEMINI_API_KEY=os.environ.get('GEMINI_API_KEY','')
GEMINI_MODEL=os.environ.get('GEMINI_MODEL','gemini-3.5-flash-lite')
# Tiempo máximo (ms) de cada llamada a Gemini y límite de consultas de IA por usuario y hora.
GEMINI_TIMEOUT_MS=int(os.environ.get('GEMINI_TIMEOUT_MS','30000'))
IA_LIMITE_POR_HORA=int(os.environ.get('IA_LIMITE_POR_HORA','30'))
