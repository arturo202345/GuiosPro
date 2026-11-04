# GUIOS PRO: método de importancia sugerida

- Acceda como usuario del grupo **Administrador** (o superusuario) y abra **Método de importancia** en el menú lateral.
- **TESIS** (predeterminado): utiliza el valor de referencia `Factor.sugerida` importado en el catálogo, sin sustituirlo por Gemini. La importancia relativa se calcula mediante la matriz de la tesis, no por promedio truncado. Gemini puede proponer el cumplimiento y el decisor; nunca sustituye IS en este modo.
- **IA**: Gemini propone `sugerida` entre 1 y 4 y una explicación; el evaluador puede editarla. La importancia relativa se calcula con la misma matriz.
- La selección se congela en cada evaluación al crearla; cambiar la configuración global solo afecta a evaluaciones nuevas.
- En ambos modos la justificación final puede generarse con Gemini.
- Los valores de referencia del catálogo proceden de los datos importados en este proyecto; verifique que coincidan con la tabla 5.3 de la tesis antes de usarlos académicamente.

## Instalación

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py configurar_roles
python manage.py runserver
```

Para Render configure `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `GEMINI_API_KEY` y `GEMINI_MODEL=gemini-flash-lite-latest`. Nunca incluya secretos en el repositorio.
