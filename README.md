# GUIOS PRO — Django + Gemini

Guía de adopción de software libre (metodología GUIOSAD de la tesis): el evaluador valora 18 factores y 61 subfactores, Django calcula la matriz FODA y el dictamen A/B/C (RN-07) y Gemini solo propone valores y redacta la justificación.

## Instalación
```bash
python -m venv .venv
# activar .venv
pip install -r requirements.txt
python manage.py migrate
python manage.py configurar_roles
python manage.py importar_catalogo
python manage.py createsuperuser   # el superusuario es Administrador
python manage.py runserver
```

Defina `GEMINI_API_KEY` como variable de entorno (`.env.example` es solo una plantilla: Django no carga `.env` automáticamente). `GEMINI_MODEL` vale por defecto `gemini-flash-lite-latest`. Nunca coloque la clave en el frontend ni en el repositorio.

Con `DJANGO_DEBUG=0` es obligatorio definir `DJANGO_SECRET_KEY`.

## Panel de administración propio
El panel de Django (`/admin/`) fue reemplazado por pantallas propias, visibles solo para el rol **Administrador** (menú lateral → *Panel de administración*, ruta `/panel/`):

| Sección | Acciones |
|---|---|
| Dimensiones, Factores, Subfactores | Listar (con búsqueda y filtros), crear, editar, desactivar y eliminar |
| Usuarios y roles | Crear, editar datos/contraseña/rol, activar o desactivar, eliminar |
| Todas las evaluaciones | Listar, filtrar, ver y eliminar |
| Configuración | Método de importancia (Tesis/IA) y registro público abierto/cerrado |

Reglas de integridad:
- Un factor o subfactor **ya usado en evaluaciones no se elimina**; se desactiva para conservar el historial.
- Una dimensión con factores no se elimina.
- Un usuario con evaluaciones no se elimina (se desactiva); nadie puede eliminarse ni desactivarse a sí mismo y siempre debe quedar un administrador activo.
- Los superusuarios son siempre Administrador.
- `importar_catalogo` no pisa lo editado en el panel: si el catálogo existe no hace nada (`--actualizar` fuerza la importación).

## Roles
- **Administrador**: panel completo y todas las evaluaciones.
- **Evaluador**: crea y gestiona sus evaluaciones, usa Gemini y descarga informes.
- **Consultor**: solo lee evaluaciones finalizadas y descarga informes.

## Uso
Cree una evaluación, valore factores y subfactores (o use **Autocompletar con Gemini**), finalice y abra el resultado; allí puede pedir la justificación con Gemini y exportar el PDF. Sin clave o conectividad el dictamen sigue disponible.

- Una evaluación **finalizada no se edita**: use **Crear nueva versión** para copiarla como borrador (la original y su justificación se conservan).
- Gemini: cada llamada tiene tiempo máximo (`GEMINI_TIMEOUT_MS`, 30 s), reintenta ante errores 500/502/503/504 y el autocompletado envía sus lotes en paralelo. Cada usuario puede hacer hasta `IA_LIMITE_POR_HORA` consultas por hora (30 por defecto; el contador es por proceso).
- Contraseñas: se aplican los validadores estándar de Django.

## Pruebas
```bash
python manage.py test evaluaciones
```
Cubren el motor de decisión, permisos por rol, el panel (CRUD y bloqueos), historial, importación del catálogo y la integración con Gemini (simulada, sin red).

## Despliegue
Consulte `GUIA_RENDER_Y_ROLES.md`.
