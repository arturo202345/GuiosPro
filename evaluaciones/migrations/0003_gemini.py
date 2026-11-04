from django.db import migrations, models
class Migration(migrations.Migration):
 dependencies=[('evaluaciones','0002_mejoras_guios')]
 operations=[
 migrations.AddField(model_name='resultadoevaluacion',name='justificacion_ia',field=models.TextField(blank=True)),
 migrations.AddField(model_name='resultadoevaluacion',name='modelo_ia',field=models.CharField(max_length=80,blank=True)),
 migrations.AddField(model_name='resultadoevaluacion',name='fecha_ia',field=models.DateTimeField(null=True,blank=True)),
 ]
