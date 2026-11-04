import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from evaluaciones.models import Dimension,Factor,Subfactor
class Command(BaseCommand):
 help='Importa los CSV originales GUIOSAD'
 def handle(self,*args,**kwargs):
  base=Path(__file__).resolve().parents[3]/'data'
  def leer(nombre):
   with (base/nombre).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
  config={r['Factor']:r for r in leer('factors.csv')}
  for r in leer('guiosad_data.csv'):
   dim,_=Dimension.objects.get_or_create(nombre=r['Dimensión'])
   cfg=config.get(r['Factor'],{})
   factor,_=Factor.objects.update_or_create(nombre=r['Factor'],defaults={'dimension':dim,'sugerida':int(cfg.get('Sugerida',1)),'alcance':cfg.get('Alcance','Interno')})
   Subfactor.objects.get_or_create(factor=factor,nombre=r['Subfactor'])
  self.stdout.write(self.style.SUCCESS(f'Importados {Factor.objects.count()} factores y {Subfactor.objects.count()} subfactores'))
