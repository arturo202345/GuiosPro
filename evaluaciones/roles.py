"""Permisos aplicados en el servidor, no solo ocultando botones."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import Q

ADMIN = 'Administrador'
EVALUADOR = 'Evaluador'
CONSULTOR = 'Consultor'
ROLES = [(ADMIN, ADMIN), (EVALUADOR, EVALUADOR), (CONSULTOR, CONSULTOR)]


def rol(user):
    """Rol efectivo del usuario (se calcula una vez por objeto usuario)."""
    if not user.is_authenticated:
        return None
    guardado = getattr(user, '_rol_cache', None)
    if guardado:
        return guardado
    nombres = {g.name for g in user.groups.all()}
    if user.is_superuser or ADMIN in nombres:
        resultado = ADMIN
    elif CONSULTOR in nombres:
        resultado = CONSULTOR
    else:
        # Las cuentas anteriores sin grupo conservan el acceso de Evaluador.
        resultado = EVALUADOR
    user._rol_cache = resultado
    return resultado


def asignar_rol(user, nombre):
    """Deja al usuario con exactamente uno de los tres roles."""
    if nombre not in (ADMIN, EVALUADOR, CONSULTOR):
        raise ValueError('Rol inválido')
    user.groups.remove(*Group.objects.filter(name__in=[ADMIN, EVALUADOR, CONSULTOR]))
    grupo, _ = Group.objects.get_or_create(name=nombre)
    user.groups.add(grupo)
    user._rol_cache = None


def admins_activos():
    return User.objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(groups__name=ADMIN)).distinct()


def puede_editar(user):
    return rol(user) in (ADMIN, EVALUADOR)


def puede_ver_todas(user):
    return rol(user) in (ADMIN, CONSULTOR)


def requiere_edicion(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not puede_editar(request.user):
            raise PermissionDenied('Su rol es de solo lectura.')
        return view(request, *args, **kwargs)
    return wrapped


def requiere_admin(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if rol(request.user) != ADMIN:
            raise PermissionDenied('Solo el Administrador puede acceder a esta sección.')
        return view(request, *args, **kwargs)
    return wrapped
