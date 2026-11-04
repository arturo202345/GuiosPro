# GUIOS PRO: roles y PostgreSQL de Render

## Roles
- **Administrador**: ve y gestiona todas las evaluaciones; usa `/admin/` si tiene `is_staff=True`. Puede gestionar catálogo y usuarios en Django Admin.
- **Evaluador**: crea, edita, elimina sus evaluaciones, usa Gemini y genera informes.
- **Consultor**: solo puede consultar resultados de evaluaciones **finalizadas** y descargar informes; no puede editar ni consultar Gemini.

Se crean mediante `python manage.py configurar_roles`. El registro público asigna Evaluador. Los usuarios anteriores sin grupo mantienen Evaluador. Los superusuarios son Administrador. Para asignar roles: `/admin/` > Usuarios > seleccionar usuario > Grupos. Para habilitar el panel de administración a un Administrador, marcar **Staff status**; no marcar superusuario salvo necesidad.

## Desarrollo local
1. Crear un entorno virtual **nuevo**; el ZIP no incluye `.env` de Python ni claves.
2. `pip install -r requirements.txt`
3. Sin `DATABASE_URL` se utiliza SQLite local; con `DATABASE_URL` se utiliza PostgreSQL.
4. `python manage.py migrate`
5. `python manage.py configurar_roles`
6. `python manage.py importar_catalogo` (solo si la base está vacía).
7. `python manage.py createsuperuser`
8. `python manage.py runserver`

## Render PostgreSQL
1. Subir el proyecto a GitHub, sin `.env`, claves ni `db.sqlite3`.
2. En Render crear un servicio PostgreSQL y un Web Service, o usar `render.yaml` (Blueprint).
3. Configurar `DATABASE_URL` con la **Internal Database URL** de PostgreSQL, `DJANGO_SECRET_KEY` con un secreto fuerte, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=.onrender.com`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://TU-NOMBRE.onrender.com`, `GEMINI_API_KEY` y `GEMINI_MODEL=gemini-flash-lite-latest`.
4. Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py configurar_roles`.
5. Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
6. Una vez desplegado, abrir la Shell de Render para ejecutar `python manage.py createsuperuser` y `python manage.py importar_catalogo` (solo la primera vez).

**Importante:** conectar PostgreSQL nuevo no transfiere los datos SQLite anteriores. Para migrarlos, exportar desde SQLite con `dumpdata` y cargar en PostgreSQL con `loaddata`, previa copia de seguridad y comprobación de conflictos. No subir el archivo SQLite a GitHub.

**Seguridad:** en Render usar `DEBUG=0`, HTTPS, no publicar secretos. `render.yaml` crea la configuración, pero la base/plan y su disponibilidad dependen de Render. `GEMINI_API_KEY` se configura manualmente.
