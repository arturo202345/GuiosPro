from django.test import SimpleTestCase
from .services import importancia_relativa,clasificar

class ReglasNegocioTests(SimpleTestCase):
 def test_importancia_relativa(self):
  self.assertEqual(importancia_relativa(1,1),1)
  self.assertEqual(importancia_relativa(3,4),3)
  self.assertEqual(importancia_relativa(4,4),4)
 def test_clasificacion_foda(self):
  self.assertEqual(clasificar('Interno',3),'Fortaleza')
  self.assertEqual(clasificar('Interno',2.99),'Debilidad')
  self.assertEqual(clasificar('Externo',3),'Oportunidad')
  self.assertEqual(clasificar('Externo',2),'Amenaza')
