# Prompt completo de continuación de GUIOS PRO

Actúa como ingeniero de software especializado en Django y mejora el proyecto GUIOS PRO adjunto sin sustituir su interfaz de evaluación por un diseño genérico. Usa como fuente de requisitos el documento «S7-COMPONENTE PRÁCTICO_1» y conserva los CSV originales de GUIOSAD. Elimina cualquier funcionalidad de CV, currículums, hojas de vida o análisis de candidatos, porque no pertenece al alcance.

## Estado de la versión entregada
- Django con aplicación `evaluaciones`, modelos Dimension, Factor, Subfactor, Evaluacion, ValorFactor, ValorSubfactor y ResultadoEvaluacion.
- Migración `0002_mejoras_guios` para ampliar modelos sin reemplazar `0001_initial`.
- Registro de usuarios, autenticación Django, historial individual y controles de propiedad.
- Administración de catálogo mediante Django Admin, con campos de descripción y activación.
- Importador del catálogo desde `data/factors.csv` y `data/guiosad_data.csv`.
- Formulario con tres pestañas que agrupan los seis pasos del modelo, selectores 1–4 y alcance interno/externo.
- Guardado de progreso, edición, eliminación, finalización, FODA y reporte PDF.
- Cálculo corregido y pruebas unitarias básicas.

## Reglas de negocio obligatorias
RN-01: importancia del factor de 1 a 4: Irrelevante, Opcional, Importante, Fundamental.
RN-02: importancia relativa = parte entera de (importancia sugerida + importancia del decisor)/2, sin restar 1.
RN-03: solo son relevantes factores con importancia relativa > 1.
RN-04: subfactores de 1 a 4: No cumple, Desconozco, Cumple parcialmente, Cumple.
RN-05 y RN-08: promedio aritmético de todos los subfactores, incluyendo los que tengan valor 2.
RN-06: alcance interno con media >= 3 = Fortaleza; interno < 3 = Debilidad; externo >= 3 = Oportunidad; externo < 3 = Amenaza. Si el alcance sugerido es Ambos, solicitar selección explícita.
RN-07: si existe un negativo importante/fundamental, recomendación C (no adoptar hasta corregir); si los negativos son solo opcionales, recomendación B (adoptar con revisión); si todos son positivos, recomendación A (adoptar). No generar resultado definitivo si faltan factores relevantes por evaluar.

## Requisitos y siguientes mejoras
Verifica RF-01 a RF-23 y RNF-01 a RNF-10 del documento. Completa lo pendiente, especialmente integración LLM real y opcional para justificar la recomendación sin modificar RN-07, comparación de software, ayudas contextuales, pruebas de integración y validación de seguridad. Comprueba que el catálogo tenga 18 factores y 60 subfactores después de importar. Mejora los estilos manteniendo la estructura y terminología GUIOS PRO. Ejecuta `python manage.py migrate`, `python manage.py importar_catalogo`, `python manage.py check` y `python manage.py test` en un entorno con dependencias instaladas. Revisa el flujo completo desde registro hasta PDF. No afirmes que una función existe si no está implementada. Entrega el proyecto completo en ZIP y un registro verificable de los cambios.
