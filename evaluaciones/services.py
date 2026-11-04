NIVELES=['Irrelevante','Opcional','Importante','Fundamental']
SUBNIVELES=['No cumple el requisito','Desconozco si cumple el requisito','Cumple parcialmente el requisito','Cumple el requisito']

# Matriz discreta IE x IL (tesis, figura 5.10). Se utiliza también para ID x IS.
MATRIZ_IMPORTANCIA = {
 1: {1: 1, 2: 1, 3: 2, 4: 2},
 2: {1: 1, 2: 2, 3: 2, 4: 3},
 3: {1: 2, 2: 2, 3: 3, 4: 3},
 4: {1: 2, 2: 3, 3: 3, 4: 4},
}

def importancia_sugerida_tesis(ie, il):
 if ie not in MATRIZ_IMPORTANCIA or il not in range(1,5):
  raise ValueError('IE o IL fuera de rango')
 return MATRIZ_IMPORTANCIA[ie][il]

def importancia_relativa(sugerida,decisor):
 if sugerida not in range(1,5) or decisor not in range(1,5):
  raise ValueError('Importancia fuera de rango')
 return MATRIZ_IMPORTANCIA[decisor][sugerida]

def clasificar(alcance,media):
 if alcance not in ('Interno','Externo'):raise ValueError('Debe definir el alcance')
 return ('Fortaleza' if media>=3 else 'Debilidad') if alcance=='Interno' else ('Oportunidad' if media>=3 else 'Amenaza')

def analizar(evaluacion):
 resultados=[]; pendientes=[]
 valores=evaluacion.valores.select_related('factor').prefetch_related('subvalores','factor__subfactores')
 if not valores.exists():return [],None,'Primero valore los factores.'
 for v in valores:
  if v.decisor not in range(1,5):pendientes.append(v.factor.nombre);continue
  relativa=importancia_relativa(v.sugerida if v.sugerida is not None else v.factor.sugerida,v.decisor)
  if relativa==1:continue
  subfactores=list(v.factor.subfactores.filter(activo=True))
  notas={sv.subfactor_id:sv.valor for sv in v.subvalores.all()}
  if not subfactores or any(notas.get(sf.id) not in range(1,5) for sf in subfactores) or v.alcance not in ('Interno','Externo'):
   pendientes.append(v.factor.nombre);continue
  media=sum(notas[sf.id] for sf in subfactores)/len(subfactores)
  resultados.append({'factor':v.factor,'relativa':NIVELES[relativa-1],'indice':relativa,'media':round(media,2),'alcance':v.alcance,'foda':clasificar(v.alcance,media)})
 if pendientes:return resultados,None,'Evaluación incompleta. Pendientes: '+', '.join(pendientes)
 if not resultados:return resultados,None,'No hay factores relevantes. Revise la importancia asignada.'
 negativos=[r for r in resultados if r['foda'] in ('Debilidad','Amenaza')]
 if any(r['indice']>=3 for r in negativos):return resultados,'C','No se recomienda adoptar hasta garantizar recursos para corregir las debilidades o amenazas en factores importantes o fundamentales.'
 if negativos:return resultados,'B','La adopción es posible con revisión de las debilidades o amenazas presentes en factores opcionales.'
 return resultados,'A','Se recomienda adoptar: todos los factores relevantes evaluados son fortalezas u oportunidades.'
