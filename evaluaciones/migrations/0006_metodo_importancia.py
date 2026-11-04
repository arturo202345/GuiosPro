from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('evaluaciones','0005_alter_factor_sugerida_alter_valorfactor_decisor_and_more')]
    operations=[
        migrations.CreateModel(name='ConfiguracionSistema',fields=[('id',models.BigAutoField(primary_key=True,serialize=False)),('metodo_importancia',models.CharField(choices=[('TESIS','Metodología de la tesis'),('IA','Gemini IA')],default='TESIS',max_length=5)),('actualizado',models.DateTimeField(auto_now=True))]),
        migrations.AddField(model_name='evaluacion',name='metodo_importancia',field=models.CharField(choices=[('TESIS','Tesis'),('IA','Gemini')],default='TESIS',max_length=5)),
    ]
