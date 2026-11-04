"""Permissions enforced server-side, not only by hiding buttons."""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ADMIN='Administrador'
EVALUADOR='Evaluador'
CONSULTOR='Consultor'

def rol(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser or user.groups.filter(name=ADMIN).exists():
        return ADMIN
    if user.groups.filter(name=CONSULTOR).exists():
        return CONSULTOR
    if user.groups.filter(name=EVALUADOR).exists():
        return EVALUADOR
    # Existing accounts keep their previous evaluation access.
    return EVALUADOR

def puede_editar(user):
    return rol(user) in (ADMIN,EVALUADOR)

def puede_ver_todas(user):
    return rol(user) in (ADMIN,CONSULTOR)

def requiere_edicion(view):
    @login_required
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if not puede_editar(request.user):
            raise PermissionDenied('Su rol es de solo lectura.')
        return view(request,*args,**kwargs)
    return wrapped
