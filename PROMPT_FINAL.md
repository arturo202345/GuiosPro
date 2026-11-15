# Prompt completo para continuar GUIOS PRO

Desarrolla y mejora GUIOS PRO en Django tomando como fuente normativa el documento S7-COMPONENTE PRÁCTICO_1_Grupo10.pdf y como base el código del ZIP. No incluir CV ni currículums. Respeta el diseño de la BD de páginas 16-27 y los mockups de páginas 33-38 (acceso, historial, registro de evaluación, filtro, ponderación, FODA y dictamen).

## Implementado en esta entrega
- Se conserva el catálogo jerárquico Dimensión → Factor → Subfactor, autenticación Django, evaluaciones de cada usuario, valoraciones de factores y subfactores, y ResultadoEvaluacion.
- Motor RN-01 a RN-08: escalas 1-4, importancia relativa por matriz IS×ID (equivale a floor((sugerida+decisor)/2)), exclusión de importancia 1, media aritmética incluyendo valor 2, resolución de alcance Ambos, umbral FODA 3, dictamen A/B/C RN-07, y bloqueo de evaluaciones incompletas.
- Integración con Google Gemini por SDK oficial google-genai, clave GEMINI_API_KEY del entorno, generación en POST autenticado y resultado persistido en justificacion_ia, modelo_ia y fecha_ia. Gemini NO altera el dictamen determinista.
- Mejoras visuales inspiradas en mockups: barra lateral, bloques, indicadores, matriz FODA, dictamen, acceso a IA y exportación PDF. No son una réplica píxel a píxel.
- Migración 0003 para campos de IA.

## Pendientes para equivalencia total con PDF
- Implementar rol explícito separado del auth.User si se requiere esquema físico literal; hoy los roles son grupos de Django (Administrador, Evaluador, Consultor).
- Separar el formulario actual en pantallas persistentes de los 3 bloques como los mockups; hoy conserva el formulario funcional existente y un resumen por bloques.
- Incorporar comparador de software. (La administración visual propia ya existe en `/panel/`; el Django admin fue retirado.)
- Pendiente: auditoría de cambios y validación en navegadores. (Ya hay pruebas automáticas, `python manage.py test evaluaciones`, y paginación en listados.)
- Verificado por prueba automática: la importación CSV produce 3 dimensiones, 18 factores y 61 subfactores. Falta confirmar que correspondan al catálogo oficial de la tesis.
- Ejecutar migraciones y pruebas en un entorno con dependencias instaladas; verificar una llamada real con clave válida de Gemini.

## Condiciones obligatorias
No inventar datos, no exponer claves API, no permitir acceso a evaluaciones ajenas, usar POST+CSRF para llamadas con costo, preservar historial, bloquear IA si evaluación incompleta, no sustituir la lógica RN-07 con una decisión generativa.
