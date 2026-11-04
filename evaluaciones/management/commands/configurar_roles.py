from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from evaluaciones.roles import ADMIN,EVALUADOR,CONSULTOR
class Command(BaseCommand):
    help='Crea los roles Administrador, Evaluador y Consultor.'
    def handle(self,*args,**kwargs):
        for nombre in (ADMIN,EVALUADOR,CONSULTOR):
            Group.objects.get_or_create(name=nombre)
            self.stdout.write(self.style.SUCCESS(f'Rol disponible: {nombre}'))
