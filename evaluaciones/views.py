from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import HttpResponseForbidden,HttpResponse,JsonResponse
from django.utils.html import escape
from django.utils import timezone
from .gemini_service import generar_justificacion, generar_sugerencias, GeminiNoDisponible
from .models import Dimension,Factor,Subfactor,Evaluacion,ValorFactor,ValorSubfactor,ResultadoEvaluacion,ConfiguracionSistema
from .roles import ADMIN, CONSULTOR, EVALUADOR, rol, puede_ver_todas, requiere_edicion
from .services import analizar,NIVELES,SUBNIVELES,importancia_relativa,clasificar

def registro(request):
 form=UserCreationForm(request.POST or None)
 if request.method=='POST' and form.is_valid():
  user=form.save()
  from django.contrib.auth.models import Group
  user.groups.add(Group.objects.get_or_create(name=EVALUADOR)[0]);login(request,user);return redirect('inicio')
 return render(request,'evaluaciones/registro.html',{'form':form})

@login_required
def inicio(request):
 qs=Evaluacion.objects.all() if rol(request.user)==ADMIN else (Evaluacion.objects.filter(estado='FINALIZADA') if rol(request.user)==CONSULTOR else Evaluacion.objects.filter(usuario=request.user))
 return render(request,'evaluaciones/inicio.html',{'evaluaciones':qs.order_by('-fecha'),'puede_editar':rol(request.user)!=CONSULTOR,'es_admin':rol(request.user)==ADMIN})

def propia(request,pk):
 qs=Evaluacion.objects.all() if rol(request.user)==ADMIN else (Evaluacion.objects.filter(estado='FINALIZADA') if rol(request.user)==CONSULTOR else Evaluacion.objects.filter(usuario=request.user))
 return get_object_or_404(qs,pk=pk)

def datos_formulario(request,ev,finalizar=False):
 factores=list(Factor.objects.filter(activo=True,dimension__activo=True).select_related('dimension').prefetch_related('subfactores').order_by('dimension_id','id'))
 if not factores:raise ValueError('No existe catálogo activo. Ejecute importar_catalogo.')
 datos=[]
 for f in factores:
  raw=request.POST.get(f'decisor_{f.pk}')
  if raw not in ('1','2','3','4'):raise ValueError('Seleccione la importancia de todos los factores.')
  decisor=int(raw)
  raw_sugerida=request.POST.get(f'sugerida_{f.pk}','')
  if raw_sugerida not in ('1','2','3','4'):raise ValueError('Seleccione la importancia sugerida de '+f.nombre)
  metodo=ev.metodo_importancia if ev else ConfiguracionSistema.actual().metodo_importancia
  sugerida=f.sugerida if metodo=='TESIS' else int(raw_sugerida)
  rel=importancia_relativa(sugerida,decisor)
  justificacion=('Valor de referencia del catálogo de la tesis.' if metodo=='TESIS' else request.POST.get(f'justificacion_{f.pk}','').strip()[:1500])
  alcance=request.POST.get(f'alcance_{f.pk}','') if f.alcance=='Ambos' else f.alcance
  if rel>1 and alcance not in ('Interno','Externo'):raise ValueError('Seleccione el alcance del factor '+f.nombre)
  if rel==1:alcance=f.alcance if f.alcance!='Ambos' else 'Interno'
  notas=[]
  if rel>1:
   subs=[sf for sf in f.subfactores.all() if sf.activo]
   if not subs:raise ValueError('Factor sin subfactores: '+f.nombre)
   for sf in subs:
    raw=request.POST.get(f'sub_{sf.pk}','')
    if finalizar and raw not in ('1','2','3','4'):raise ValueError('Faltan subfactores por evaluar en '+f.nombre)
    if raw in ('1','2','3','4'):notas.append((sf,int(raw)))
   if finalizar and len(notas)!=len(subs):raise ValueError('Faltan subfactores en '+f.nombre)
  datos.append((f,sugerida,justificacion,decisor,rel,alcance,notas))
 return datos

@requiere_edicion
def nueva(request,pk=None):
 ev=propia(request,pk) if pk else None
 metodo=ev.metodo_importancia if ev else ConfiguracionSistema.actual().metodo_importancia
 factores=Factor.objects.filter(activo=True,dimension__activo=True).select_related('dimension').prefetch_related('subfactores').order_by('dimension_id','id')
 if request.method=='POST':
  try:
   accion=request.POST.get('accion','finalizar');finalizar=accion=='finalizar'
   nombre=request.POST.get('nombre','').strip();software=request.POST.get('software','').strip()
   if not nombre or not software:raise ValueError('Indique el nombre de la evaluación y el software.')
   datos=datos_formulario(request,ev,finalizar)
   with transaction.atomic():
    if ev is None:ev=Evaluacion(usuario=request.user)
    if not ev.pk: ev.metodo_importancia=ConfiguracionSistema.actual().metodo_importancia
    ev.nombre=nombre;ev.software=software;ev.organizacion=request.POST.get('organizacion','').strip();ev.descripcion=request.POST.get('descripcion','').strip();ev.estado='EN_PROCESO';ev.paso_actual=2;ev.save()
    for f,sugerida,justificacion,decisor,rel,alcance,notas in datos:
     vf,_=ValorFactor.objects.update_or_create(evaluacion=ev,factor=f,defaults={'sugerida':sugerida,'justificacion_sugerida':justificacion,'decisor':decisor,'relativa':rel,'alcance':alcance,'ponderacion':None,'clasificacion':''})
     vf.subvalores.all().delete()
     for sf,valor in notas:ValorSubfactor.objects.create(valor_factor=vf,subfactor=sf,valor=valor)
     if rel>1 and len(notas)==len([sf for sf in f.subfactores.all() if sf.activo]):
      media=sum(v for _,v in notas)/len(notas);vf.ponderacion=round(media,2);vf.clasificacion=clasificar(alcance,media);vf.save(update_fields=['ponderacion','clasificacion'])
    ev.valores.exclude(factor__in=[item[0] for item in datos]).delete()
    filas,grado,mensaje=analizar(ev)
    if finalizar:
     if not grado:raise ValueError(mensaje)
     ev.estado='FINALIZADA';ev.paso_actual=6;ev.save(update_fields=['estado','paso_actual'])
     ResultadoEvaluacion.objects.update_or_create(evaluacion=ev,defaults={'recomendacion':grado,'justificacion':mensaje})
    else:ResultadoEvaluacion.objects.filter(evaluacion=ev).delete()
   messages.success(request,'Evaluación finalizada.' if finalizar else 'Progreso guardado.')
   return redirect('resultado',pk=ev.pk)
  except ValueError as error:messages.error(request,str(error))
 valores={v.factor_id:v for v in ev.valores.prefetch_related('subvalores')} if ev else {}
 for f in factores:
  v=valores.get(f.id);f.valor_actual=v.decisor if v else None;f.sugerida_actual=v.sugerida if v and v.sugerida is not None else f.sugerida;f.justificacion_actual=v.justificacion_sugerida if v else '';f.alcance_actual=v.alcance if v else ''
  notas={sv.subfactor_id:sv.valor for sv in v.subvalores.all()} if v else {}
  for sf in f.subfactores.all():sf.valor_actual=notas.get(sf.id)
 return render(request,'evaluaciones/nueva.html',{'factores':factores,'niveles':list(enumerate(NIVELES,1)),'subniveles':list(enumerate(SUBNIVELES,1)),'ev':ev,'metodo':metodo})

@login_required
def resultado(request,pk):
 ev=propia(request,pk);filas,grado,mensaje=analizar(ev)
 return render(request,'evaluaciones/resultado.html',{'ev':ev,'filas':filas,'grado':grado,'mensaje':mensaje,'puede_editar':rol(request.user)!=CONSULTOR,'resultado_guardado':ResultadoEvaluacion.objects.filter(evaluacion=ev).first()})

@requiere_edicion
@require_POST
def eliminar(request,pk):
 propia(request,pk).delete();messages.success(request,'Evaluación eliminada.');return redirect('inicio')

@login_required
def informe_pdf(request,pk):
 ev=propia(request,pk);filas,grado,mensaje=analizar(ev)
 if not grado:return HttpResponse('Complete la evaluación antes de generar el PDF.',status=400)
 try:
  from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
  from reportlab.lib.styles import getSampleStyleSheet
  from reportlab.lib import colors
  from io import BytesIO
 except ImportError:return HttpResponse('Instale reportlab para generar PDF.',status=503)
 from xml.sax.saxutils import escape as xml_escape
 buff=BytesIO();doc=SimpleDocTemplate(buff);styles=getSampleStyleSheet()
 content=[Paragraph('GUIOS PRO - Informe de evaluación',styles['Title']),Spacer(1,12)]
 for line in (ev.nombre,ev.organizacion,ev.software,'Recomendación: '+grado,mensaje):content.append(Paragraph(xml_escape(line or '—'),styles['Normal']));content.append(Spacer(1,9))
 guardado=ResultadoEvaluacion.objects.filter(evaluacion=ev).first()
 if guardado and guardado.justificacion_ia:
  content.append(Spacer(1,12));content.append(Paragraph('Justificación contextualizada con Gemini',styles['Heading2']))
  for parrafo in guardado.justificacion_ia.split('\n'):
   if parrafo.strip():content.append(Paragraph(xml_escape(parrafo),styles['Normal']));content.append(Spacer(1,8))
 tabla=[['Factor','Importancia','Media','FODA']]+[[r['factor'].nombre,r['relativa'],str(r['media']),r['foda']] for r in filas]
 data=[[Paragraph(xml_escape(str(c)),styles['BodyText']) for c in row] for row in tabla]
 table=Table(data,colWidths=[175,95,60,100],repeatRows=1);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP')]));content.append(table);doc.build(content)
 response=HttpResponse(buff.getvalue(),content_type='application/pdf');response['Content-Disposition']=f'attachment; filename="guios-evaluacion-{ev.pk}.pdf"';return response

@requiere_edicion
@require_POST
def generar_ia(request,pk):
 ev=propia(request,pk)
 filas,grado,mensaje=analizar(ev)
 if not grado or ev.estado!='FINALIZADA':
  messages.error(request,'Finalice la evaluación completa antes de consultar Gemini.')
  return redirect('resultado',pk=ev.pk)
 try:
  texto=generar_justificacion(ev,filas,grado,mensaje)
  resultado,_=ResultadoEvaluacion.objects.update_or_create(evaluacion=ev,defaults={'recomendacion':grado,'justificacion':mensaje})
  resultado.justificacion_ia=texto
  from django.conf import settings
  resultado.modelo_ia=settings.GEMINI_MODEL
  resultado.fecha_ia=timezone.now()
  resultado.save(update_fields=['justificacion_ia','modelo_ia','fecha_ia'])
  messages.success(request,'Justificación generada con Gemini.')
 except GeminiNoDisponible as error:
  messages.error(request,str(error))
 return redirect('resultado',pk=ev.pk)


@requiere_edicion
@require_POST
def sugerir_ia(request):
 software=request.POST.get('software','').strip()
 if not software:
  return JsonResponse({'error':'Indique el software antes de autocompletar.'},status=400)
 pk=request.POST.get('evaluacion_id','').strip()
 if pk:
  if not pk.isdigit():return JsonResponse({'error':'Evaluación inválida.'},status=400)
  ev=propia(request,int(pk))
  metodo=ev.metodo_importancia
 else:
  metodo=ConfiguracionSistema.actual().metodo_importancia
 factores=list(Factor.objects.filter(activo=True,dimension__activo=True).select_related('dimension').prefetch_related('subfactores').order_by('dimension_id','id'))
 if not factores:return JsonResponse({'error':'Primero importe el catálogo de factores.'},status=400)
 try:
  sugerencias=generar_sugerencias(software,request.POST.get('organizacion','').strip(),request.POST.get('descripcion','').strip(),factores)
  if metodo=='TESIS':
   for item in sugerencias:
    factor=next(f for f in factores if f.pk==item['id'])
    item['sugerida']=factor.sugerida
    item['justificacion']='Importancia sugerida de referencia según la tesis (catálogo). '+item['justificacion']
 except GeminiNoDisponible as error:
  return JsonResponse({'error':str(error)},status=503)
 return JsonResponse({'factores':sugerencias,'metodo':metodo})


@login_required
def configuracion(request):
 if rol(request.user)!=ADMIN:
  from django.core.exceptions import PermissionDenied
  raise PermissionDenied('Solo el administrador puede modificar el método.')
 config=ConfiguracionSistema.actual()
 if request.method=='POST':
  metodo=request.POST.get('metodo_importancia')
  if metodo not in ('TESIS','IA'):
   messages.error(request,'Método inválido.')
  else:
   config.metodo_importancia=metodo
   config.save(update_fields=['metodo_importancia','actualizado'])
   messages.success(request,'Método actualizado. Solo afecta a nuevas evaluaciones.')
   return redirect('configuracion')
 return render(request,'evaluaciones/configuracion.html',{'config':config})
