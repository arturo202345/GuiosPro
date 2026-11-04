# GUIOS PRO — Django + Gemini

Basado en documento S7-COMPONENTE PRÁCTICO_1 (modelo y mockups).

## Instalación
```bash
python -m venv .venv
# activar .venv
pip install -r requirements.txt
python manage.py migrate
python manage.py importar_catalogo
python manage.py createsuperuser
python manage.py runserver
```

Defina `GEMINI_API_KEY` como variable de entorno (el archivo `.env.example` es solo una plantilla: Django no carga `.env` automáticamente). Puede configurar `GEMINI_MODEL`; valor inicial `gemini-2.5-flash`. Compruebe que su cuenta tenga acceso a ese modelo. Nunca coloque la clave en el frontend.

## Uso
Registre un evaluador, cree evaluación, valore factores y subfactores, finalice y abra resultados. Allí pulse «Generar justificación con Gemini». Sin clave o conectividad, el dictamen de RN-07 sigue disponible y se muestra un mensaje de error controlado. Los resultados de IA se guardan y se incorporan al PDF.

## Estado y límites
El motor de decisión es determinista. Las pantallas de resultados, navegación y panel siguen los mockups como referencia visual; el formulario de evaluación previo aún no replica exactamente la división del asistente en tres pantallas. Es necesario probar en entorno Django instalado y revisar catálogo contra documento. Consulte PROMPT_FINAL.md.


## Autocompletado con Gemini (versión modificada)

1. Configure `GEMINI_API_KEY` en las variables de entorno; no la incluya en el código.
2. Configure `GEMINI_MODEL=gemini-flash-lite-latest` (modelo probado por el usuario).
3. Ejecute `python manage.py migrate` para añadir importancia sugerida y justificación por evaluación.
4. Abra **Nueva evaluación**, complete software y contexto y pulse **Autocompletar con Gemini**.
5. Revise y edite las importancias sugeridas, las importancias del decisor y los cumplimientos antes de guardar.
6. Finalice la evaluación y utilice el botón de justificación Gemini en la pantalla de resultados.

Las propuestas de la IA no se guardan hasta que se envía el formulario. Si falta evidencia sobre cumplimiento, la IA recibe la instrucción de proponer **2 (Desconozco)**. El índice relativo, la matriz FODA y el dictamen se calculan en Django. Los valores sugeridos se guardan en `ValorFactor` para no cambiar el catálogo compartido. La generación con IA necesita conexión y cuota disponible.
