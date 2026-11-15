# GUIOS PRO: roles y PostgreSQL de Render

## Roles
- **Administrador**: ve y gestiona todas las evaluaciones y usa el **panel de administración propio** (`/panel/`): catálogo (dimensiones, factores, subfactores), usuarios y roles, evaluaciones y configuración. Ya no se usa el panel de Django.
- **Evaluador**: crea, edita, elimina sus evaluaciones, usa Gemini y genera informes.
- **Consultor**: solo puede consultar resultados de evaluaciones **finalizadas** y descargar informes; no puede editar ni consultar Gemini.

Se crean mediante `python manage.py configurar_roles`. El registro público asigna Evaluador. Los usuarios anteriores sin grupo mantienen Evaluador. Los superusuarios son Administrador. Los roles se asignan en `/panel/usuarios/` (crear o editar usuario → campo *Rol*). El primer Administrador se crea con `python manage.py createsuperuser`; después puede crear otros administradores desde el panel. El registro público puede cerrarse en *Configuración*.

## Desarrollo local
1. Crear un entorno virtual **nuevo**; el ZIP no incluye `.env` de Python ni claves.
2. `pip install -r requirements.txt`
3. Sin `DATABASE_URL` se utiliza SQLite local; con `DATABASE_URL` se utiliza PostgreSQL.
4. `python manage.py migrate`
5. `python manage.py configurar_roles`
6. `python manage.py importar_catalogo` (no hace nada si el catálogo ya existe).
7. `python manage.py createsuperuser`
8. `python manage.py runserver`

## Render PostgreSQL
1. Subir el proyecto a GitHub, sin `.env`, claves ni `db.sqlite3`.
2. En Render crear un servicio PostgreSQL y un Web Service, o usar `render.yaml` (Blueprint).
3. Configurar `DATABASE_URL` con la **Internal Database URL** de PostgreSQL, `DJANGO_SECRET_KEY` con un secreto fuerte, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=.onrender.com`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://TU-NOMBRE.onrender.com`, `GEMINI_API_KEY` y `GEMINI_MODEL=gemini-flash-lite-latest`.
4. Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py configurar_roles && python manage.py importar_catalogo` (el catálogo se importa solo la primera vez y nunca pisa lo editado en el panel).
5. Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120` (el autocompletado con Gemini puede superar los 30 s por defecto de gunicorn).
6. Una vez desplegado, abrir la Shell de Render y ejecutar `python manage.py createsuperuser` (solo la primera vez).

**Importante:** conectar PostgreSQL nuevo no transfiere los datos SQLite anteriores. Para migrarlos, exportar desde SQLite con `dumpdata` y cargar en PostgreSQL con `loaddata`, previa copia de seguridad y comprobación de conflictos. No subir el archivo SQLite a GitHub.

**Seguridad:** en Render usar `DEBUG=0` (con `DEBUG=0` la app exige `DJANGO_SECRET_KEY`), HTTPS, no publicar secretos. `render.yaml` crea la configuración, pero la base/plan y su disponibilidad dependen de Render. `GEMINI_API_KEY` se configura manualmente.
