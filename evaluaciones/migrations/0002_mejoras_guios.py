from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
 dependencies=[('evaluaciones','0001_initial'),('auth','0012_alter_user_first_name_max_length')]
 operations=[
  migrations.AddField(model_name='dimension',name='descripcion',field=models.TextField(blank=True)),
  migrations.AddField(model_name='dimension',name='activo',field=models.BooleanField(default=True)),
  migrations.AddField(model_name='factor',name='descripcion',field=models.TextField(blank=True)),
  migrations.AddField(model_name='factor',name='activo',field=models.BooleanField(default=True)),
  migrations.AddField(model_name='subfactor',name='descripcion',field=models.TextField(blank=True)),
  migrations.AddField(model_name='subfactor',name='activo',field=models.BooleanField(default=True)),
  migrations.AddField(model_name='evaluacion',name='descripcion',field=models.TextField(blank=True)),
  migrations.AddField(model_name='evaluacion',name='usuario',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.CASCADE,related_name='evaluaciones',to='auth.user')),
  migrations.AddField(model_name='evaluacion',name='estado',field=models.CharField(default='EN_PROCESO',max_length=20)),
  migrations.AddField(model_name='evaluacion',name='paso_actual',field=models.PositiveSmallIntegerField(default=1)),
  migrations.AlterField(model_name='valorfactor',name='decisor',field=models.PositiveSmallIntegerField(blank=True,null=True)),
  migrations.AddField(model_name='valorfactor',name='relativa',field=models.PositiveSmallIntegerField(blank=True,null=True)),
  migrations.AddField(model_name='valorfactor',name='ponderacion',field=models.DecimalField(blank=True,decimal_places=2,max_digits=4,null=True)),
  migrations.AddField(model_name='valorfactor',name='clasificacion',field=models.CharField(blank=True,max_length=20)),
  migrations.AlterField(model_name='valorsubfactor',name='valor',field=models.PositiveSmallIntegerField(blank=True,null=True)),
  migrations.CreateModel(name='ResultadoEvaluacion',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('recomendacion',models.CharField(max_length=100)),('justificacion',models.TextField()),('fecha_generacion',models.DateTimeField(auto_now=True)),('evaluacion',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name='resultado',to='evaluaciones.evaluacion'))]),
 ]
