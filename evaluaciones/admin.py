from django.contrib import admin
from .models import Dimension,Factor,Subfactor,Evaluacion,ValorFactor,ValorSubfactor,ResultadoEvaluacion,ConfiguracionSistema
@admin.register(Dimension)
class DimensionAdmin(admin.ModelAdmin):list_display=('nombre','activo');list_filter=('activo',)
@admin.register(Factor)
class FactorAdmin(admin.ModelAdmin):list_display=('nombre','dimension','sugerida','alcance','activo');list_filter=('dimension','activo','alcance');search_fields=('nombre',)
@admin.register(Subfactor)
class SubfactorAdmin(admin.ModelAdmin):list_display=('nombre','factor','activo');list_filter=('activo',);search_fields=('nombre',)
admin.site.register([Evaluacion,ValorFactor,ValorSubfactor,ResultadoEvaluacion])

@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
 list_display=('metodo_importancia','actualizado')
 def has_add_permission(self,request):
  return request.user.is_superuser and not ConfiguracionSistema.objects.exists()
 def has_change_permission(self,request,obj=None):
  return request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()
 def has_delete_permission(self,request,obj=None):
  return False
