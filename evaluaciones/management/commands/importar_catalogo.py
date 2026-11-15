import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from evaluaciones.models import Dimension, Factor, Subfactor


class Command(BaseCommand):
    help = ('Importa el catálogo GUIOSAD desde data/*.csv. Por seguridad, si el catálogo ya existe no '
            'hace nada (así los despliegues no pisan lo editado en el panel). Use --actualizar para '
            'agregar lo que falte y restaurar importancia y alcance de referencia.')

    def add_arguments(self, parser):
        parser.add_argument('--actualizar', action='store_true',
                            help='Completa el catálogo existente y restablece sugerida/alcance desde el CSV.')

    @transaction.atomic
    def handle(self, *args, **opciones):
        if Factor.objects.exists() and not opciones['actualizar']:
            self.stdout.write(f'Catálogo existente ({Factor.objects.count()} factores): sin cambios. '
                              'Use --actualizar para forzar la importación.')
            return
        base = Path(__file__).resolve().parents[3] / 'data'

        def leer(nombre):
            with (base / nombre).open(encoding='utf-8-sig', newline='') as archivo:
                return list(csv.DictReader(archivo, delimiter='\t'))

        config = {r['Factor']: r for r in leer('factors.csv')}
        for r in leer('guiosad_data.csv'):
            dimension, _ = Dimension.objects.get_or_create(nombre=r['Dimensión'])
            cfg = config.get(r['Factor'], {})
            factor, _ = Factor.objects.update_or_create(
                nombre=r['Factor'],
                defaults={'dimension': dimension, 'sugerida': int(cfg.get('Sugerida', 1)),
                          'alcance': cfg.get('Alcance', 'Interno')})
            Subfactor.objects.get_or_create(factor=factor, nombre=r['Subfactor'])
        self.stdout.write(self.style.SUCCESS(
            f'Importados {Factor.objects.count()} factores y {Subfactor.objects.count()} subfactores'))
