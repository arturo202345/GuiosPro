"""Panel de administración propio (reemplaza al Django admin). Solo para el rol Administrador."""
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import DimensionForm, FactorForm, SubfactorForm, UsuarioForm
from .models import (ConfiguracionSistema, Dimension, Evaluacion, Factor, Subfactor, ValorFactor,
                     ValorSubfactor)
from .paginacion import paginar
from .roles import ADMIN, admins_activos, requiere_admin, rol

PLANTILLAS = 'evaluaciones/panel/'


def _si_no(valor):
    return 'Sí' if valor else 'No'


def _lista(request, titulo, columnas, filas, pagina, qs, nuevo_url=None, filtros=(), buscar=False):
    return render(request, PLANTILLAS + 'lista.html', {
        'titulo': titulo, 'columnas': columnas, 'ncols': len(columnas) + 1, 'filas': filas,
        'page': pagina, 'qs': qs, 'nuevo_url': nuevo_url, 'filtros': filtros,
        'buscar_activo': buscar, 'q': request.GET.get('q', '').strip()})


def _formulario(request, clase, instancia, titulo, volver, mensaje, **extra):
    form = clase(request.POST or None, instance=instancia, **extra)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, mensaje)
        return redirect(volver)
    return render(request, PLANTILLAS + 'form.html', {'form': form, 'titulo': titulo, 'volver': reverse(volver)})


def _eliminar(request, objeto, titulo, volver, bloqueo='', aviso=''):
    """Pide confirmación (GET) y elimina (POST) salvo que exista un bloqueo de integridad."""
    if bloqueo:
        messages.error(request, bloqueo)
        return redirect(volver)
    if request.method == 'POST':
        nombre = str(objeto)
        objeto.delete()
        messages.success(request, f'«{nombre}» eliminado.')
        return redirect(volver)
    return render(request, PLANTILLAS + 'confirmar_eliminar.html',
                  {'titulo': titulo, 'objeto': objeto, 'aviso': aviso, 'volver': reverse(volver)})


@requiere_admin
def inicio_panel(request):
    return render(request, PLANTILLAS + 'inicio.html', {
        'config': ConfiguracionSistema.actual(),
        'conteos': [
            ('Dimensiones', Dimension.objects.count(), 'panel_dimensiones'),
            ('Factores', Factor.objects.count(), 'panel_factores'),
            ('Subfactores', Subfactor.objects.count(), 'panel_subfactores'),
            ('Usuarios', User.objects.count(), 'panel_usuarios'),
            ('Evaluaciones', Evaluacion.objects.count(), 'panel_evaluaciones'),
            ('Administradores activos', admins_activos().count(), 'panel_usuarios'),
        ]})


# ---------- Dimensiones ----------
@requiere_admin
def dimension_lista(request):
    qs = Dimension.objects.annotate(n=Count('factores')).order_by('nombre')
    texto = request.GET.get('q', '').strip()
    if texto:
        qs = qs.filter(nombre__icontains=texto)
    pagina, params = paginar(request, qs)
    filas = [{'celdas': [d.nombre, d.n, _si_no(d.activo)],
              'editar': reverse('panel_dimension_editar', args=[d.pk]),
              'eliminar': reverse('panel_dimension_eliminar', args=[d.pk])} for d in pagina]
    return _lista(request, 'Dimensiones', ['Nombre', 'Factores', 'Activa'], filas, pagina, params,
                  reverse('panel_dimension_nueva'), buscar=True)


@requiere_admin
def dimension_nueva(request):
    return _formulario(request, DimensionForm, None, 'Nueva dimensión', 'panel_dimensiones', 'Dimensión creada.')


@requiere_admin
def dimension_editar(request, pk):
    dimension = get_object_or_404(Dimension, pk=pk)
    return _formulario(request, DimensionForm, dimension, f'Editar dimensión: {dimension.nombre}',
                       'panel_dimensiones', 'Dimensión actualizada.')


@requiere_admin
@require_http_methods(['GET', 'POST'])
def dimension_eliminar(request, pk):
    dimension = get_object_or_404(Dimension, pk=pk)
    bloqueo = ''
    if dimension.factores.exists():
        bloqueo = 'La dimensión tiene factores. Elimine o reasigne sus factores, o desactívela.'
    return _eliminar(request, dimension, 'Eliminar dimensión', 'panel_dimensiones', bloqueo)


# ---------- Factores ----------
@requiere_admin
def factor_lista(request):
    qs = Factor.objects.select_related('dimension').annotate(n=Count('subfactores')).order_by('dimension_id', 'id')
    dimension = request.GET.get('dimension', '')
    if dimension.isdigit():
        qs = qs.filter(dimension_id=int(dimension))
    texto = request.GET.get('q', '').strip()
    if texto:
        qs = qs.filter(nombre__icontains=texto)
    pagina, params = paginar(request, qs)
    filas = [{'celdas': [f.nombre, f.dimension.nombre, f'{f.sugerida} · {f.alcance}', f.n, _si_no(f.activo)],
              'extras': [('Subfactores', reverse('panel_subfactores') + f'?factor={f.pk}')],
              'editar': reverse('panel_factor_editar', args=[f.pk]),
              'eliminar': reverse('panel_factor_eliminar', args=[f.pk])} for f in pagina]
    filtros = [{'nombre': 'dimension', 'label': 'Dimensión', 'actual': dimension,
                'opciones': [(str(d.pk), d.nombre) for d in Dimension.objects.order_by('nombre')]}]
    return _lista(request, 'Factores', ['Factor', 'Dimensión', 'Sugerida · Alcance', 'Subfactores', 'Activo'],
                  filas, pagina, params, reverse('panel_factor_nuevo'), filtros, buscar=True)


@requiere_admin
def factor_nuevo(request):
    return _formulario(request, FactorForm, None, 'Nuevo factor', 'panel_factores', 'Factor creado.')


@requiere_admin
def factor_editar(request, pk):
    factor = get_object_or_404(Factor, pk=pk)
    return _formulario(request, FactorForm, factor, f'Editar factor: {factor.nombre}',
                       'panel_factores', 'Factor actualizado.')


@requiere_admin
@require_http_methods(['GET', 'POST'])
def factor_eliminar(request, pk):
    factor = get_object_or_404(Factor, pk=pk)
    bloqueo = ''
    if ValorFactor.objects.filter(factor=factor).exists():
        bloqueo = 'El factor ya forma parte de evaluaciones. Para conservar el historial, desactívelo en lugar de eliminarlo.'
    aviso = f'Se eliminarán también sus {factor.subfactores.count()} subfactores.' if factor.subfactores.exists() else ''
    return _eliminar(request, factor, 'Eliminar factor', 'panel_factores', bloqueo, aviso)


# ---------- Subfactores ----------
@requiere_admin
def subfactor_lista(request):
    qs = Subfactor.objects.select_related('factor').order_by('factor_id', 'id')
    factor = request.GET.get('factor', '')
    if factor.isdigit():
        qs = qs.filter(factor_id=int(factor))
    texto = request.GET.get('q', '').strip()
    if texto:
        qs = qs.filter(Q(nombre__icontains=texto) | Q(factor__nombre__icontains=texto))
    pagina, params = paginar(request, qs)
    filas = [{'celdas': [s.nombre, s.factor.nombre, _si_no(s.activo)],
              'editar': reverse('panel_subfactor_editar', args=[s.pk]),
              'eliminar': reverse('panel_subfactor_eliminar', args=[s.pk])} for s in pagina]
    filtros = [{'nombre': 'factor', 'label': 'Factor', 'actual': factor,
                'opciones': [(str(f.pk), f.nombre) for f in Factor.objects.order_by('nombre')]}]
    return _lista(request, 'Subfactores', ['Subfactor', 'Factor', 'Activo'], filas, pagina, params,
                  reverse('panel_subfactor_nuevo'), filtros, buscar=True)


@requiere_admin
def subfactor_nuevo(request):
    return _formulario(request, SubfactorForm, None, 'Nuevo subfactor', 'panel_subfactores', 'Subfactor creado.')


@requiere_admin
def subfactor_editar(request, pk):
    subfactor = get_object_or_404(Subfactor, pk=pk)
    return _formulario(request, SubfactorForm, subfactor, 'Editar subfactor', 'panel_subfactores',
                       'Subfactor actualizado.')


@requiere_admin
@require_http_methods(['GET', 'POST'])
def subfactor_eliminar(request, pk):
    subfactor = get_object_or_404(Subfactor, pk=pk)
    bloqueo = ''
    if ValorSubfactor.objects.filter(subfactor=subfactor).exists():
        bloqueo = 'El subfactor ya fue valorado en evaluaciones. Para conservar el historial, desactívelo.'
    return _eliminar(request, subfactor, 'Eliminar subfactor', 'panel_subfactores', bloqueo)


# ---------- Usuarios y roles ----------
@requiere_admin
def usuario_lista(request):
    qs = User.objects.prefetch_related('groups').annotate(n=Count('evaluaciones')).order_by('username')
    texto = request.GET.get('q', '').strip()
    if texto:
        qs = qs.filter(Q(username__icontains=texto) | Q(first_name__icontains=texto)
                       | Q(last_name__icontains=texto) | Q(email__icontains=texto))
    pagina, params = paginar(request, qs)
    filas = [{'celdas': [u.username, f'{u.first_name} {u.last_name}'.strip() or '—', u.email or '—',
                         rol(u), _si_no(u.is_active), u.n],
              'editar': reverse('panel_usuario_editar', args=[u.pk]),
              'eliminar': reverse('panel_usuario_eliminar', args=[u.pk])} for u in pagina]
    return _lista(request, 'Usuarios y roles',
                  ['Usuario', 'Nombre', 'Correo', 'Rol', 'Activo', 'Evaluaciones'], filas, pagina, params,
                  reverse('panel_usuario_nuevo'), buscar=True)


@requiere_admin
def usuario_nuevo(request):
    return _formulario(request, UsuarioForm, None, 'Nuevo usuario', 'panel_usuarios', 'Usuario creado.',
                       actor=request.user)


@requiere_admin
def usuario_editar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    return _formulario(request, UsuarioForm, usuario, f'Editar usuario: {usuario.username}',
                       'panel_usuarios', 'Usuario actualizado.', actor=request.user)


@requiere_admin
@require_http_methods(['GET', 'POST'])
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    bloqueo = ''
    if usuario.pk == request.user.pk:
        bloqueo = 'No puede eliminar su propia cuenta.'
    elif usuario.evaluaciones.exists():
        bloqueo = 'El usuario tiene evaluaciones. Desactívelo para conservar su historial.'
    elif usuario.is_active and rol(usuario) == ADMIN and not admins_activos().exclude(pk=usuario.pk).exists():
        bloqueo = 'Debe existir al menos un administrador activo.'
    return _eliminar(request, usuario, 'Eliminar usuario', 'panel_usuarios', bloqueo)


# ---------- Evaluaciones (vista global del administrador) ----------
@requiere_admin
def evaluacion_lista(request):
    qs = Evaluacion.objects.select_related('usuario').order_by('-fecha')
    estado = request.GET.get('estado', '')
    if estado in ('EN_PROCESO', 'FINALIZADA'):
        qs = qs.filter(estado=estado)
    texto = request.GET.get('q', '').strip()
    if texto:
        qs = qs.filter(Q(nombre__icontains=texto) | Q(software__icontains=texto)
                       | Q(usuario__username__icontains=texto))
    pagina, params = paginar(request, qs)
    filas = [{'celdas': [e.nombre, e.software, e.usuario.username if e.usuario else '—', e.estado,
                         e.fecha.strftime('%d/%m/%Y %H:%M')],
              'extras': [('Ver', reverse('resultado', args=[e.pk]))],
              'eliminar': reverse('panel_evaluacion_eliminar', args=[e.pk])} for e in pagina]
    filtros = [{'nombre': 'estado', 'label': 'Estado', 'actual': estado,
                'opciones': [('EN_PROCESO', 'En proceso'), ('FINALIZADA', 'Finalizada')]}]
    return _lista(request, 'Todas las evaluaciones', ['Evaluación', 'Software', 'Usuario', 'Estado', 'Fecha'],
                  filas, pagina, params, None, filtros, buscar=True)


@requiere_admin
@require_http_methods(['GET', 'POST'])
def evaluacion_eliminar(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    return _eliminar(request, evaluacion, 'Eliminar evaluación', 'panel_evaluaciones', '',
                     'Se eliminarán también sus valoraciones y su dictamen. Esta acción no se puede deshacer.')
