from django.db import migrations, models
import django.core.validators

class Migration(migrations.Migration):
 dependencies=[('evaluaciones','0003_gemini')]
 operations=[
  migrations.AddField(model_name='valorfactor',name='sugerida',field=models.PositiveSmallIntegerField(blank=True,null=True,validators=[django.core.validators.MinValueValidator(1),django.core.validators.MaxValueValidator(4)])),
  migrations.AddField(model_name='valorfactor',name='justificacion_sugerida',field=models.TextField(blank=True)),
 ]
