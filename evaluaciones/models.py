from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
V4=[MinValueValidator(1),MaxValueValidator(4)]
class Dimension(models.Model):
 nombre=models.CharField(max_length=120,unique=True)
 descripcion=models.TextField(blank=True)
 activo=models.BooleanField(default=True)
 def __str__(self):return self.nombre
class Factor(models.Model):
 dimension=models.ForeignKey(Dimension,on_delete=models.CASCADE,related_name='factores')
 nombre=models.CharField(max_length=180,unique=True)
 descripcion=models.TextField(blank=True)
 activo=models.BooleanField(default=True)
 sugerida=models.PositiveSmallIntegerField(default=1,validators=V4)
 alcance=models.CharField(max_length=10,choices=[('Interno','Interno'),('Externo','Externo'),('Ambos','Ambos')],default='Interno')
 def __str__(self):return self.nombre
class Subfactor(models.Model):
 factor=models.ForeignKey(Factor,on_delete=models.CASCADE,related_name='subfactores')
 nombre=models.TextField()
 descripcion=models.TextField(blank=True)
 activo=models.BooleanField(default=True)
 def __str__(self):return self.nombre
class Evaluacion(models.Model):
 nombre=models.CharField(max_length=180)
 organizacion=models.CharField(max_length=180,blank=True)
 software=models.CharField(max_length=180)
 descripcion=models.TextField(blank=True)
 usuario=models.ForeignKey("auth.User",on_delete=models.CASCADE,null=True,blank=True,related_name="evaluaciones")
 estado=models.CharField(max_length=20,default="EN_PROCESO")
 paso_actual=models.PositiveSmallIntegerField(default=1)
 metodo_importancia=models.CharField(max_length=5,choices=[('TESIS','Tesis'),('IA','Gemini')],default='TESIS')
 fecha=models.DateTimeField(auto_now_add=True)
 def __str__(self):return f'{self.nombre} - {self.software}'
class ValorFactor(models.Model):
 evaluacion=models.ForeignKey(Evaluacion,on_delete=models.CASCADE,related_name='valores')
 factor=models.ForeignKey(Factor,on_delete=models.CASCADE)
 sugerida=models.PositiveSmallIntegerField(null=True,blank=True,validators=V4)
 justificacion_sugerida=models.TextField(blank=True)
 decisor=models.PositiveSmallIntegerField(null=True,blank=True,validators=V4)
 relativa=models.PositiveSmallIntegerField(null=True,blank=True)
 ponderacion=models.DecimalField(max_digits=4,decimal_places=2,null=True,blank=True)
 clasificacion=models.CharField(max_length=20,blank=True)
 alcance=models.CharField(max_length=10,choices=[('Interno','Interno'),('Externo','Externo')])
 class Meta:constraints=[models.UniqueConstraint(fields=['evaluacion','factor'],name='valor_factor_unico')]
class ValorSubfactor(models.Model):
 valor_factor=models.ForeignKey(ValorFactor,on_delete=models.CASCADE,related_name='subvalores')
 subfactor=models.ForeignKey(Subfactor,on_delete=models.CASCADE)
 valor=models.PositiveSmallIntegerField(null=True,blank=True,validators=V4)
 class Meta:constraints=[models.UniqueConstraint(fields=['valor_factor','subfactor'],name='valor_subfactor_unico')]

class ResultadoEvaluacion(models.Model):
 evaluacion=models.OneToOneField(Evaluacion,on_delete=models.CASCADE,related_name="resultado")
 recomendacion=models.CharField(max_length=100)
 justificacion=models.TextField()
 fecha_generacion=models.DateTimeField(auto_now=True)
 justificacion_ia=models.TextField(blank=True)
 modelo_ia=models.CharField(max_length=80,blank=True)
 fecha_ia=models.DateTimeField(null=True,blank=True)


class ConfiguracionSistema(models.Model):
    """Única configuración global, modificable únicamente por Administrador."""
    METODOS = [('TESIS', 'Metodología de la tesis'), ('IA', 'Gemini IA')]
    metodo_importancia = models.CharField(max_length=5, choices=METODOS, default='TESIS')
    actualizado = models.DateTimeField(auto_now=True)

    @classmethod
    def actual(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def __str__(self):
        return self.get_metodo_importancia_display()
