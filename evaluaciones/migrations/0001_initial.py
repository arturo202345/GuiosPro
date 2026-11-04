from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name='Dimension',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('nombre',models.CharField(max_length=120,unique=True))]),
        migrations.CreateModel(name='Evaluacion',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('nombre',models.CharField(max_length=180)),('organizacion',models.CharField(blank=True,max_length=180)),('software',models.CharField(max_length=180)),('fecha',models.DateTimeField(auto_now_add=True))]),
        migrations.CreateModel(name='Factor',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('nombre',models.CharField(max_length=180,unique=True)),('sugerida',models.PositiveSmallIntegerField(default=1)),('alcance',models.CharField(choices=[('Interno','Interno'),('Externo','Externo'),('Ambos','Ambos')],default='Interno',max_length=10)),('dimension',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='factores',to='evaluaciones.dimension'))]),
        migrations.CreateModel(name='Subfactor',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('nombre',models.TextField()),('factor',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='subfactores',to='evaluaciones.factor'))]),
        migrations.CreateModel(name='ValorFactor',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('decisor',models.PositiveSmallIntegerField(default=1)),('alcance',models.CharField(choices=[('Interno','Interno'),('Externo','Externo')],max_length=10)),('evaluacion',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='valores',to='evaluaciones.evaluacion')),('factor',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='evaluaciones.factor'))]),
        migrations.CreateModel(name='ValorSubfactor',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('valor',models.PositiveSmallIntegerField(default=1)),('subfactor',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='evaluaciones.subfactor')),('valor_factor',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='subvalores',to='evaluaciones.valorfactor'))]),
        migrations.AddConstraint(model_name='valorfactor',constraint=models.UniqueConstraint(fields=('evaluacion','factor'),name='valor_factor_unico')),
        migrations.AddConstraint(model_name='valorsubfactor',constraint=models.UniqueConstraint(fields=('valor_factor','subfactor'),name='valor_subfactor_unico')),
    ]
