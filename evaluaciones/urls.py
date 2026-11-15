from django.contrib.auth import views as auth_views
from django.urls import path

from . import panel, views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('registro/', views.registro, name='registro'),
    path('ingresar/', views.Ingreso.as_view(), name='login'),
    path('salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('nueva/', views.nueva, name='nueva'),
    path('sugerir-ia/', views.sugerir_ia, name='sugerir_ia'),
    path('evaluacion/<int:pk>/editar/', views.nueva, name='editar'),
    path('evaluacion/<int:pk>/nueva-version/', views.nueva_version, name='nueva_version'),
    path('evaluacion/<int:pk>/', views.resultado, name='resultado'),
    path('evaluacion/<int:pk>/gemini/', views.generar_ia, name='generar_ia'),
    path('evaluacion/<int:pk>/pdf/', views.informe_pdf, name='informe_pdf'),
    path('evaluacion/<int:pk>/eliminar/', views.eliminar, name='eliminar'),
    path('configuracion/', views.configuracion, name='configuracion'),

    # Panel de administración propio (solo rol Administrador)
    path('panel/', panel.inicio_panel, name='panel'),
    path('panel/dimensiones/', panel.dimension_lista, name='panel_dimensiones'),
    path('panel/dimensiones/nueva/', panel.dimension_nueva, name='panel_dimension_nueva'),
    path('panel/dimensiones/<int:pk>/editar/', panel.dimension_editar, name='panel_dimension_editar'),
    path('panel/dimensiones/<int:pk>/eliminar/', panel.dimension_eliminar, name='panel_dimension_eliminar'),
    path('panel/factores/', panel.factor_lista, name='panel_factores'),
    path('panel/factores/nuevo/', panel.factor_nuevo, name='panel_factor_nuevo'),
    path('panel/factores/<int:pk>/editar/', panel.factor_editar, name='panel_factor_editar'),
    path('panel/factores/<int:pk>/eliminar/', panel.factor_eliminar, name='panel_factor_eliminar'),
    path('panel/subfactores/', panel.subfactor_lista, name='panel_subfactores'),
    path('panel/subfactores/nuevo/', panel.subfactor_nuevo, name='panel_subfactor_nuevo'),
    path('panel/subfactores/<int:pk>/editar/', panel.subfactor_editar, name='panel_subfactor_editar'),
    path('panel/subfactores/<int:pk>/eliminar/', panel.subfactor_eliminar, name='panel_subfactor_eliminar'),
    path('panel/usuarios/', panel.usuario_lista, name='panel_usuarios'),
    path('panel/usuarios/nuevo/', panel.usuario_nuevo, name='panel_usuario_nuevo'),
    path('panel/usuarios/<int:pk>/editar/', panel.usuario_editar, name='panel_usuario_editar'),
    path('panel/usuarios/<int:pk>/eliminar/', panel.usuario_eliminar, name='panel_usuario_eliminar'),
    path('panel/evaluaciones/', panel.evaluacion_lista, name='panel_evaluaciones'),
    path('panel/evaluaciones/<int:pk>/eliminar/', panel.evaluacion_eliminar, name='panel_evaluacion_eliminar'),
]
