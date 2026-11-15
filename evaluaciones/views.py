from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .gemini_service import GeminiNoDisponible, generar_justificacion, generar_sugerencias
from .models import (ConfiguracionSistema, Evaluacion, Factor, ResultadoEvaluacion, ValorFactor,
                     ValorSubfactor)
from .paginacion import paginar
from .roles import ADMIN, CONSULTOR, EVALUADOR, asignar_rol, requiere_admin, requiere_edicion, rol
from .services import NIVELES, SUBNIVELES, analizar, clasificar, importancia_relativa


class Ingreso(LoginView):
    template_name = 'evaluaciones/login.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['registro_abierto'] = ConfiguracionSistema.actual().registro_abierto
        return contexto


def registro(request):
    if not ConfiguracionSistema.actual().registro_abierto:
        return render(request, 'evaluaciones/registro.html', {'cerrado': True}, status=403)
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        asignar_rol(usuario, EVALUADOR)
        login(request, usuario)
        return redirect('inicio')
    return render(request, 'evaluaciones/registro.html', {'form': form})


def visibles(user):
    """Evaluaciones que el usuario puede consultar según su rol."""
    actual = rol(user)
    if actual == ADMIN:
        return Evaluacion.objects.all()
    if actual == CONSULTOR:
        return Evaluacion.objects.filter(estado='FINALIZADA')
    return Evaluacion.objects.filter(usuario=user)


def propia(request, pk):
    return get_object_or_404(visibles(request.user), pk=pk)


def limite_ia(usuario):
    """Limita las consultas a Gemini por usuario y hora (protege la cuota de la API)."""
    clave = f'ia:{usuario.pk}'
    cache.add(clave, 0, 3600)
    try:
        usadas = cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, 3600)
        usadas = 1
    return usadas <= getattr(settings, 'IA_LIMITE_POR_HORA', 30)


@login_required
def inicio(request):
    actual = rol(request.user)
    pagina, qs = paginar(request, visibles(request.user).order_by('-fecha'), 10)
    return render(request, 'evaluaciones/inicio.html', {
        'evaluaciones': pagina, 'page': pagina, 'qs': qs,
        'puede_editar': actual != CONSULTOR, 'es_admin': actual == ADMIN})


def datos_formulario(request, metodo, finalizar=False):
    factores = list(Factor.objects.filter(activo=True, dimension__activo=True)
                    .select_related('dimension').prefetch_related('subfactores').order_by('dimension_id', 'id'))
    if not factores:
        raise ValueError('No existe catálogo activo. Ejecute importar_catalogo o créelo desde el panel.')
    datos = []
    for f in factores:
        raw = request.POST.get(f'decisor_{f.pk}')
        if raw not in ('1', '2', '3', '4'):
            raise ValueError('Seleccione la importancia de todos los factores.')
        decisor = int(raw)
        raw_sugerida = request.POST.get(f'sugerida_{f.pk}', '')
        if metodo == 'IA' and raw_sugerida not in ('1', '2', '3', '4'):
            raise ValueError('Seleccione la importancia sugerida de ' + f.nombre)
        sugerida = f.sugerida if metodo == 'TESIS' else int(raw_sugerida)
        rel = importancia_relativa(sugerida, decisor)
        justificacion = ('Valor de referencia del catálogo de la tesis.' if metodo == 'TESIS'
                         else request.POST.get(f'justificacion_{f.pk}', '').strip()[:1500])
        alcance = request.POST.get(f'alcance_{f.pk}', '') if f.alcance == 'Ambos' else f.alcance
        if rel > 1 and alcance not in ('Interno', 'Externo'):
            raise ValueError('Seleccione el alcance del factor ' + f.nombre)
        if rel == 1:
            alcance = f.alcance if f.alcance != 'Ambos' else 'Interno'
        notas = []
        if rel > 1:
            subs = [sf for sf in f.subfactores.all() if sf.activo]
            if not subs:
                raise ValueError('Factor sin subfactores: ' + f.nombre)
            for sf in subs:
                raw = request.POST.get(f'sub_{sf.pk}', '')
                if finalizar and raw not in ('1', '2', '3', '4'):
                    raise ValueError('Faltan subfactores por evaluar en ' + f.nombre)
                if raw in ('1', '2', '3', '4'):
                    notas.append((sf, int(raw)))
            if finalizar and len(notas) != len(subs):
                raise ValueError('Faltan subfactores en ' + f.nombre)
        datos.append((f, sugerida, justificacion, decisor, rel, alcance, notas))
    return datos


@requiere_edicion
def nueva(request, pk=None):
    ev = propia(request, pk) if pk else None
    if ev and ev.estado == 'FINALIZADA':
        messages.error(request, 'Una evaluación finalizada no se modifica para conservar el historial. '
                                'Cree una nueva versión desde el resultado.')
        return redirect('resultado', pk=ev.pk)
    metodo = ev.metodo_importancia if ev else ConfiguracionSistema.actual().metodo_importancia
    factores = (Factor.objects.filter(activo=True, dimension__activo=True)
                .select_related('dimension').prefetch_related('subfactores').order_by('dimension_id', 'id'))
    if request.method == 'POST':
        try:
            finalizar = request.POST.get('accion', 'finalizar') == 'finalizar'
            nombre = request.POST.get('nombre', '').strip()
            software = request.POST.get('software', '').strip()
            if not nombre or not software:
                raise ValueError('Indique el nombre de la evaluación y el software.')
            datos = datos_formulario(request, metodo, finalizar)
            with transaction.atomic():
                destino = ev if ev is not None else Evaluacion(usuario=request.user, metodo_importancia=metodo)
                destino.nombre, destino.software = nombre, software
                destino.organizacion = request.POST.get('organizacion', '').strip()
                destino.descripcion = request.POST.get('descripcion', '').strip()
                destino.estado, destino.paso_actual = 'EN_PROCESO', 2
                destino.save()
                for f, sugerida, justificacion, decisor, rel, alcance, notas in datos:
                    vf, _ = ValorFactor.objects.update_or_create(
                        evaluacion=destino, factor=f,
                        defaults={'sugerida': sugerida, 'justificacion_sugerida': justificacion,
                                  'decisor': decisor, 'relativa': rel, 'alcance': alcance,
                                  'ponderacion': None, 'clasificacion': ''})
                    vf.subvalores.all().delete()
                    for sf, valor in notas:
                        ValorSubfactor.objects.create(valor_factor=vf, subfactor=sf, valor=valor)
                    if rel > 1 and len(notas) == len([sf for sf in f.subfactores.all() if sf.activo]):
                        media = sum(v for _, v in notas) / len(notas)
                        vf.ponderacion = round(media, 2)
                        vf.clasificacion = clasificar(alcance, media)
                        vf.save(update_fields=['ponderacion', 'clasificacion'])
                destino.valores.exclude(factor__in=[item[0] for item in datos]).delete()
                filas, grado, mensaje = analizar(destino)
                if finalizar:
                    if not grado:
                        raise ValueError(mensaje)
                    destino.estado, destino.paso_actual = 'FINALIZADA', 6
                    destino.save(update_fields=['estado', 'paso_actual'])
                    ResultadoEvaluacion.objects.update_or_create(
                        evaluacion=destino, defaults={'recomendacion': grado, 'justificacion': mensaje})
                else:
                    ResultadoEvaluacion.objects.filter(evaluacion=destino).delete()
            messages.success(request, 'Evaluación finalizada.' if finalizar else 'Progreso guardado.')
            return redirect('resultado', pk=destino.pk)
        except ValueError as error:
            messages.error(request, str(error))
    valores = {v.factor_id: v for v in ev.valores.prefetch_related('subvalores')} if ev else {}
    for f in factores:
        v = valores.get(f.id)
        f.valor_actual = v.decisor if v else None
        f.sugerida_actual = v.sugerida if v and v.sugerida is not None else f.sugerida
        f.justificacion_actual = v.justificacion_sugerida if v else ''
        f.alcance_actual = v.alcance if v else ''
        notas = {sv.subfactor_id: sv.valor for sv in v.subvalores.all()} if v else {}
        for sf in f.subfactores.all():
            sf.valor_actual = notas.get(sf.id)
    return render(request, 'evaluaciones/nueva.html', {
        'factores': factores, 'niveles': list(enumerate(NIVELES, 1)),
        'subniveles': list(enumerate(SUBNIVELES, 1)), 'ev': ev, 'metodo': metodo})


@requiere_edicion
@require_POST
def nueva_version(request, pk):
    """Copia una evaluación finalizada como borrador nuevo; la original queda intacta."""
    original = propia(request, pk)
    if original.estado != 'FINALIZADA':
        messages.error(request, 'Solo se crean versiones a partir de evaluaciones finalizadas.')
        return redirect('editar', pk=original.pk)
    with transaction.atomic():
        copia = Evaluacion.objects.create(
            nombre=f'{original.nombre} (nueva versión)'[:180], organizacion=original.organizacion,
            software=original.software, descripcion=original.descripcion, usuario=request.user,
            estado='EN_PROCESO', paso_actual=2, metodo_importancia=original.metodo_importancia, origen=original)
        for vf in original.valores.prefetch_related('subvalores'):
            nuevo = ValorFactor.objects.create(
                evaluacion=copia, factor=vf.factor, sugerida=vf.sugerida,
                justificacion_sugerida=vf.justificacion_sugerida, decisor=vf.decisor, relativa=vf.relativa,
                ponderacion=vf.ponderacion, clasificacion=vf.clasificacion, alcance=vf.alcance)
            ValorSubfactor.objects.bulk_create([
                ValorSubfactor(valor_factor=nuevo, subfactor_id=sv.subfactor_id, valor=sv.valor)
                for sv in vf.subvalores.all()])
    messages.success(request, 'Nueva versión creada como borrador. La evaluación original se conserva.')
    return redirect('editar', pk=copia.pk)


@login_required
def resultado(request, pk):
    ev = propia(request, pk)
    filas, grado, mensaje = analizar(ev)
    return render(request, 'evaluaciones/resultado.html', {
        'ev': ev, 'filas': filas, 'grado': grado, 'mensaje': mensaje,
        'puede_editar': rol(request.user) != CONSULTOR,
        'resultado_guardado': ResultadoEvaluacion.objects.filter(evaluacion=ev).first()})


@requiere_edicion
@require_POST
def eliminar(request, pk):
    propia(request, pk).delete()
    messages.success(request, 'Evaluación eliminada.')
    return redirect('inicio')


@login_required
def informe_pdf(request, pk):
    ev = propia(request, pk)
    filas, grado, mensaje = analizar(ev)
    if not grado:
        return HttpResponse('Complete la evaluación antes de generar el PDF.', status=400)
    try:
        from io import BytesIO

        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return HttpResponse('Instale reportlab para generar PDF.', status=503)
    from xml.sax.saxutils import escape as xml_escape
    buff = BytesIO()
    doc = SimpleDocTemplate(buff)
    styles = getSampleStyleSheet()
    content = [Paragraph('GUIOS PRO - Informe de evaluación', styles['Title']), Spacer(1, 12)]
    for line in (ev.nombre, ev.organizacion, ev.software, 'Recomendación: ' + grado, mensaje):
        content.append(Paragraph(xml_escape(line or '—'), styles['Normal']))
        content.append(Spacer(1, 9))
    guardado = ResultadoEvaluacion.objects.filter(evaluacion=ev).first()
    if guardado and guardado.justificacion_ia:
        content.append(Spacer(1, 12))
        content.append(Paragraph('Justificación contextualizada con Gemini', styles['Heading2']))
        for parrafo in guardado.justificacion_ia.split('\n'):
            if parrafo.strip():
                content.append(Paragraph(xml_escape(parrafo), styles['Normal']))
                content.append(Spacer(1, 8))
    tabla = [['Factor', 'Importancia', 'Media', 'FODA']] + [
        [r['factor'].nombre, r['relativa'], str(r['media']), r['foda']] for r in filas]
    data = [[Paragraph(xml_escape(str(c)), styles['BodyText']) for c in row] for row in tabla]
    table = Table(data, colWidths=[175, 95, 60, 100], repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                               ('GRID', (0, 0), (-1, -1), .3, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    content.append(table)
    doc.build(content)
    response = HttpResponse(buff.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="guios-evaluacion-{ev.pk}.pdf"'
    return response


@requiere_edicion
@require_POST
def generar_ia(request, pk):
    ev = propia(request, pk)
    filas, grado, mensaje = analizar(ev)
    if not grado or ev.estado != 'FINALIZADA':
        messages.error(request, 'Finalice la evaluación completa antes de consultar Gemini.')
        return redirect('resultado', pk=ev.pk)
    if not limite_ia(request.user):
        messages.error(request, 'Alcanzó el límite de consultas a Gemini por hora. Inténtelo más tarde.')
        return redirect('resultado', pk=ev.pk)
    try:
        texto = generar_justificacion(ev, filas, grado, mensaje)
        resultado, _ = ResultadoEvaluacion.objects.update_or_create(
            evaluacion=ev, defaults={'recomendacion': grado, 'justificacion': mensaje})
        resultado.justificacion_ia = texto
        resultado.modelo_ia = settings.GEMINI_MODEL
        resultado.fecha_ia = timezone.now()
        resultado.save(update_fields=['justificacion_ia', 'modelo_ia', 'fecha_ia'])
        messages.success(request, 'Justificación generada con Gemini.')
    except GeminiNoDisponible as error:
        messages.error(request, str(error))
    return redirect('resultado', pk=ev.pk)


@requiere_edicion
@require_POST
def sugerir_ia(request):
    software = request.POST.get('software', '').strip()
    if not software:
        return JsonResponse({'error': 'Indique el software antes de autocompletar.'}, status=400)
    pk = request.POST.get('evaluacion_id', '').strip()
    if pk:
        if not pk.isdigit():
            return JsonResponse({'error': 'Evaluación inválida.'}, status=400)
        metodo = propia(request, int(pk)).metodo_importancia
    else:
        metodo = ConfiguracionSistema.actual().metodo_importancia
    factores = list(Factor.objects.filter(activo=True, dimension__activo=True)
                    .select_related('dimension').prefetch_related('subfactores').order_by('dimension_id', 'id'))
    if not factores:
        return JsonResponse({'error': 'Primero importe o cree el catálogo de factores.'}, status=400)
    if not limite_ia(request.user):
        return JsonResponse({'error': 'Alcanzó el límite de consultas a Gemini por hora.'}, status=429)
    try:
        sugerencias = generar_sugerencias(software, request.POST.get('organizacion', '').strip(),
                                          request.POST.get('descripcion', '').strip(), factores)
        if metodo == 'TESIS':
            por_id = {f.pk: f for f in factores}
            for item in sugerencias:
                item['sugerida'] = por_id[item['id']].sugerida
                item['justificacion'] = ('Importancia sugerida de referencia según la tesis (catálogo). '
                                         + item['justificacion'])
    except GeminiNoDisponible as error:
        return JsonResponse({'error': str(error)}, status=503)
    return JsonResponse({'factores': sugerencias, 'metodo': metodo})


@requiere_admin
def configuracion(request):
    config = ConfiguracionSistema.actual()
    if request.method == 'POST':
        metodo = request.POST.get('metodo_importancia')
        if metodo not in ('TESIS', 'IA'):
            messages.error(request, 'Método inválido.')
        else:
            config.metodo_importancia = metodo
            config.registro_abierto = request.POST.get('registro_abierto') == 'on'
            config.save(update_fields=['metodo_importancia', 'registro_abierto', 'actualizado'])
            messages.success(request, 'Configuración actualizada. El método solo afecta a nuevas evaluaciones.')
            return redirect('configuracion')
    return render(request, 'evaluaciones/configuracion.html', {'config': config})
