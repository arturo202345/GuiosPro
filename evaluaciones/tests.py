import json
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from . import gemini_service
from .gemini_service import GeminiNoDisponible
from .models import (ConfiguracionSistema, Dimension, Evaluacion, Factor, ResultadoEvaluacion, Subfactor,
                     ValorFactor, ValorSubfactor)
from .roles import ADMIN, CONSULTOR, EVALUADOR, asignar_rol, rol
from .services import MATRIZ_IMPORTANCIA, analizar, clasificar, importancia_relativa

CLAVE_FUERTE = 'Tr0ub4dor&3-xyz'


def crear_usuario(nombre, rol_nombre=EVALUADOR):
    usuario = User.objects.create_user(nombre, f'{nombre}@ejemplo.com', CLAVE_FUERTE)
    asignar_rol(usuario, rol_nombre)
    return usuario


def crear_catalogo():
    """Catálogo mínimo: F1 interno y F2 externo, con dos y un subfactor activos."""
    dimension = Dimension.objects.create(nombre='Tecnológica')
    f1 = Factor.objects.create(dimension=dimension, nombre='F1', sugerida=3, alcance='Interno')
    f2 = Factor.objects.create(dimension=dimension, nombre='F2', sugerida=3, alcance='Externo')
    s11 = Subfactor.objects.create(factor=f1, nombre='S11')
    s12 = Subfactor.objects.create(factor=f1, nombre='S12')
    s21 = Subfactor.objects.create(factor=f2, nombre='S21')
    return dimension, f1, f2, (s11, s12, s21)


def datos_post(decisor=4, sub=4, accion='finalizar'):
    datos = {'nombre': 'Evaluación', 'software': 'Software X', 'accion': accion}
    for factor in Factor.objects.filter(activo=True):
        datos[f'decisor_{factor.pk}'] = str(decisor)
    for subfactor in Subfactor.objects.filter(activo=True):
        datos[f'sub_{subfactor.pk}'] = str(sub)
    return datos


def evaluacion_finalizada(usuario, sub=4):
    """Crea y finaliza una evaluación mediante el formulario real."""
    from django.test import Client
    cliente = Client()
    cliente.force_login(usuario)
    cliente.post(reverse('nueva'), datos_post(sub=sub))
    return Evaluacion.objects.filter(usuario=usuario).latest('pk')


class ReglasNegocioTests(SimpleTestCase):
    def test_importancia_relativa(self):
        self.assertEqual(importancia_relativa(1, 1), 1)
        self.assertEqual(importancia_relativa(3, 4), 3)
        self.assertEqual(importancia_relativa(4, 4), 4)

    def test_matriz_equivale_al_promedio_truncado(self):
        for decisor, fila in MATRIZ_IMPORTANCIA.items():
            for sugerida, valor in fila.items():
                self.assertEqual(valor, (decisor + sugerida) // 2)

    def test_clasificacion_foda(self):
        self.assertEqual(clasificar('Interno', 3), 'Fortaleza')
        self.assertEqual(clasificar('Interno', 2.99), 'Debilidad')
        self.assertEqual(clasificar('Externo', 3), 'Oportunidad')
        self.assertEqual(clasificar('Externo', 2), 'Amenaza')

    def test_valores_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            importancia_relativa(0, 2)
        with self.assertRaises(ValueError):
            clasificar('Ambos', 3)


class AnalisisTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario('eva')
        self.dim, self.f1, self.f2, self.subs = crear_catalogo()

    def evaluacion(self, f1, f2):
        """f1 y f2: (sugerida, decisor, media de subfactores)."""
        ev = Evaluacion.objects.create(nombre='E', software='S', usuario=self.usuario)
        for factor, (sugerida, decisor, nota), alcance in ((self.f1, f1, 'Interno'), (self.f2, f2, 'Externo')):
            vf = ValorFactor.objects.create(evaluacion=ev, factor=factor, sugerida=sugerida, decisor=decisor,
                                            alcance=alcance, relativa=importancia_relativa(sugerida, decisor))
            for sf in factor.subfactores.all():
                ValorSubfactor.objects.create(valor_factor=vf, subfactor=sf, valor=nota)
        return ev

    def test_dictamen_a(self):
        _, grado, _ = analizar(self.evaluacion((3, 4, 4), (3, 4, 3)))
        self.assertEqual(grado, 'A')

    def test_dictamen_b_con_debilidad_opcional(self):
        filas, grado, _ = analizar(self.evaluacion((2, 2, 1), (3, 4, 4)))
        self.assertEqual(grado, 'B')
        self.assertEqual({r['factor'].nombre: r['foda'] for r in filas}['F1'], 'Debilidad')

    def test_dictamen_c_con_amenaza_importante(self):
        _, grado, _ = analizar(self.evaluacion((3, 4, 4), (3, 4, 2)))
        self.assertEqual(grado, 'C')

    def test_factor_irrelevante_se_excluye(self):
        filas, grado, _ = analizar(self.evaluacion((1, 1, 1), (3, 4, 4)))
        self.assertEqual([r['factor'].nombre for r in filas], ['F2'])
        self.assertEqual(grado, 'A')

    def test_todos_irrelevantes(self):
        filas, grado, mensaje = analizar(self.evaluacion((1, 1, 1), (1, 1, 1)))
        self.assertIsNone(grado)
        self.assertIn('No hay factores relevantes', mensaje)

    def test_incompleta_si_falta_decisor_o_subfactor(self):
        ev = self.evaluacion((3, 4, 4), (3, 4, 4))
        ev.valores.filter(factor=self.f1).update(decisor=None)
        _, grado, mensaje = analizar(ev)
        self.assertIsNone(grado)
        self.assertIn('F1', mensaje)
        ev.valores.filter(factor=self.f1).update(decisor=4)
        ValorSubfactor.objects.filter(subfactor=self.subs[0]).delete()
        self.assertIsNone(analizar(ev)[1])

    def test_sin_valores(self):
        ev = Evaluacion.objects.create(nombre='E', software='S', usuario=self.usuario)
        self.assertEqual(analizar(ev)[2], 'Primero valore los factores.')


class FlujoEvaluacionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = crear_usuario('eva')
        self.dim, self.f1, self.f2, self.subs = crear_catalogo()
        self.client.force_login(self.usuario)

    def test_finalizar_en_modo_tesis_sin_enviar_sugerida(self):
        respuesta = self.client.post(reverse('nueva'), datos_post())
        ev = Evaluacion.objects.get()
        self.assertRedirects(respuesta, reverse('resultado', args=[ev.pk]))
        self.assertEqual(ev.estado, 'FINALIZADA')
        self.assertEqual(ev.resultado.recomendacion, 'A')

    def test_guardar_progreso_no_finaliza(self):
        self.client.post(reverse('nueva'), datos_post(sub=3, accion='borrador'))
        ev = Evaluacion.objects.get()
        self.assertEqual(ev.estado, 'EN_PROCESO')
        self.assertFalse(ResultadoEvaluacion.objects.exists())

    def test_finalizar_incompleta_no_deja_basura_y_conserva_el_formulario_nuevo(self):
        datos = datos_post()
        del datos[f'sub_{self.subs[0].pk}']
        respuesta = self.client.post(reverse('nueva'), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Evaluacion.objects.exists())
        self.assertContains(respuesta, 'Faltan subfactores')
        self.assertIsNone(respuesta.context['ev'])


class HistorialTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario('eva')
        crear_catalogo()
        self.ev = evaluacion_finalizada(self.usuario)
        self.client.force_login(self.usuario)

    def test_no_se_edita_una_evaluacion_finalizada(self):
        respuesta = self.client.get(reverse('editar', args=[self.ev.pk]))
        self.assertRedirects(respuesta, reverse('resultado', args=[self.ev.pk]))
        self.client.post(reverse('editar', args=[self.ev.pk]), datos_post(sub=1))
        self.ev.refresh_from_db()
        self.assertEqual(self.ev.resultado.recomendacion, 'A')

    def test_nueva_version_copia_sin_tocar_el_original(self):
        ResultadoEvaluacion.objects.filter(evaluacion=self.ev).update(justificacion_ia='texto de IA')
        respuesta = self.client.post(reverse('nueva_version', args=[self.ev.pk]))
        copia = Evaluacion.objects.exclude(pk=self.ev.pk).get()
        self.assertRedirects(respuesta, reverse('editar', args=[copia.pk]))
        self.assertEqual((copia.origen_id, copia.estado), (self.ev.pk, 'EN_PROCESO'))
        self.assertEqual(copia.valores.count(), self.ev.valores.count())
        self.assertEqual(ValorSubfactor.objects.filter(valor_factor__evaluacion=copia).count(), 3)
        self.assertFalse(ResultadoEvaluacion.objects.filter(evaluacion=copia).exists())
        self.assertEqual(ResultadoEvaluacion.objects.get(evaluacion=self.ev).justificacion_ia, 'texto de IA')

    def test_la_copia_se_puede_modificar_y_finalizar(self):
        self.client.post(reverse('nueva_version', args=[self.ev.pk]))
        copia = Evaluacion.objects.exclude(pk=self.ev.pk).get()
        self.client.post(reverse('editar', args=[copia.pk]), datos_post(sub=1))
        copia.refresh_from_db()
        self.assertEqual(copia.estado, 'FINALIZADA')
        self.assertEqual(copia.resultado.recomendacion, 'C')
        self.assertEqual(Evaluacion.objects.get(pk=self.ev.pk).resultado.recomendacion, 'A')

    def test_nueva_version_solo_con_post_y_con_rol_de_edicion(self):
        self.assertEqual(self.client.get(reverse('nueva_version', args=[self.ev.pk])).status_code, 405)
        consultor = crear_usuario('con', CONSULTOR)
        self.client.force_login(consultor)
        self.assertEqual(self.client.post(reverse('nueva_version', args=[self.ev.pk])).status_code, 403)


class PermisosTests(TestCase):
    def setUp(self):
        self.eva, self.otro = crear_usuario('eva'), crear_usuario('otro')
        self.consultor = crear_usuario('con', CONSULTOR)
        crear_catalogo()
        self.ev = evaluacion_finalizada(self.eva)

    def test_evaluador_no_ve_evaluaciones_ajenas(self):
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(reverse('resultado', args=[self.ev.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('eliminar', args=[self.ev.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('inicio')), 'Software X')

    def test_consultor_solo_ve_finalizadas_y_no_edita(self):
        borrador = Evaluacion.objects.create(nombre='Borrador', software='S', usuario=self.eva)
        self.client.force_login(self.consultor)
        self.assertEqual(self.client.get(reverse('resultado', args=[self.ev.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('resultado', args=[borrador.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('nueva')).status_code, 403)
        self.assertEqual(self.client.post(reverse('generar_ia', args=[self.ev.pk])).status_code, 403)

    def test_anonimo_va_al_login(self):
        self.assertEqual(self.client.get(reverse('inicio')).status_code, 302)
        self.assertEqual(self.client.get(reverse('panel')).status_code, 302)
        resp_landing = self.client.get(reverse('landing'))
        self.assertEqual(resp_landing.status_code, 200)
        self.assertContains(resp_landing, 'Evalúa software libre sin suposiciones')

    def test_admin_de_django_ya_no_existe(self):
        self.assertEqual(self.client.get('/admin/').status_code, 404)

    def test_rol_por_defecto_y_superusuario(self):
        self.assertEqual(rol(User.objects.create_user('sin_grupo', password=CLAVE_FUERTE)), EVALUADOR)
        self.assertEqual(rol(User.objects.create_superuser('root', 'r@e.com', CLAVE_FUERTE)), ADMIN)


RUTAS_PANEL = ['panel', 'panel_dimensiones', 'panel_dimension_nueva', 'panel_factores', 'panel_factor_nuevo',
               'panel_subfactores', 'panel_subfactor_nuevo', 'panel_usuarios', 'panel_usuario_nuevo',
               'panel_evaluaciones', 'configuracion']


class PanelAccesoTests(TestCase):
    def test_solo_el_administrador_entra_al_panel(self):
        for nombre, esperado in ((EVALUADOR, 403), (CONSULTOR, 403), (ADMIN, 200)):
            usuario = crear_usuario(f'u_{nombre}', nombre)
            self.client.force_login(usuario)
            for ruta in RUTAS_PANEL:
                self.assertEqual(self.client.get(reverse(ruta)).status_code, esperado, (nombre, ruta))

    def test_las_acciones_de_escritura_tambien_estan_protegidas(self):
        evaluador = crear_usuario('eva')
        dimension, factor, _, subs = crear_catalogo()
        self.client.force_login(evaluador)
        peticiones = [
            (reverse('panel_dimension_nueva'), {'nombre': 'X'}),
            (reverse('panel_dimension_eliminar', args=[dimension.pk]), {}),
            (reverse('panel_factor_editar', args=[factor.pk]), {'nombre': 'Y'}),
            (reverse('panel_subfactor_eliminar', args=[subs[0].pk]), {}),
            (reverse('panel_usuario_nuevo'), {'username': 'nuevo'}),
        ]
        for url, datos in peticiones:
            self.assertEqual(self.client.post(url, datos).status_code, 403, url)
        self.assertEqual(Dimension.objects.count(), 1)
        self.assertFalse(User.objects.filter(username='nuevo').exists())


class PanelCatalogoTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario('admin', ADMIN)
        self.client.force_login(self.admin)

    def test_crud_dimension(self):
        self.client.post(reverse('panel_dimension_nueva'), {'nombre': 'Organizacional', 'activo': 'on'})
        dimension = Dimension.objects.get(nombre='Organizacional')
        self.client.post(reverse('panel_dimension_editar', args=[dimension.pk]), {'nombre': 'Org.', 'descripcion': 'd'})
        dimension.refresh_from_db()
        self.assertEqual((dimension.nombre, dimension.activo), ('Org.', False))
        self.assertContains(self.client.get(reverse('panel_dimensiones')), 'Org.')
        self.assertContains(self.client.get(reverse('panel_dimension_eliminar', args=[dimension.pk])), 'Sí, eliminar')
        self.client.post(reverse('panel_dimension_eliminar', args=[dimension.pk]))
        self.assertFalse(Dimension.objects.exists())

    def test_nombre_de_dimension_duplicado_se_rechaza(self):
        Dimension.objects.create(nombre='A')
        respuesta = self.client.post(reverse('panel_dimension_nueva'), {'nombre': 'A'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Dimension.objects.count(), 1)

    def test_dimension_con_factores_no_se_elimina(self):
        dimension, *_ = crear_catalogo()
        self.client.post(reverse('panel_dimension_eliminar', args=[dimension.pk]))
        self.assertTrue(Dimension.objects.filter(pk=dimension.pk).exists())

    def test_crud_factor_y_filtros(self):
        dimension, f1, _, _ = crear_catalogo()
        self.client.post(reverse('panel_factor_nuevo'), {
            'dimension': dimension.pk, 'nombre': 'F3', 'descripcion': '', 'sugerida': '2', 'alcance': 'Ambos',
            'activo': 'on'})
        f3 = Factor.objects.get(nombre='F3')
        self.assertEqual((f3.sugerida, f3.alcance), (2, 'Ambos'))
        self.client.post(reverse('panel_factor_editar', args=[f3.pk]), {
            'dimension': dimension.pk, 'nombre': 'F3b', 'descripcion': '', 'sugerida': '4', 'alcance': 'Interno'})
        f3.refresh_from_db()
        self.assertEqual((f3.nombre, f3.sugerida, f3.activo), ('F3b', 4, False))
        lista = self.client.get(reverse('panel_factores'), {'q': 'F3b'})
        self.assertContains(lista, 'F3b')
        self.assertNotContains(lista, '>F1<')
        self.client.post(reverse('panel_factor_eliminar', args=[f3.pk]))
        self.assertFalse(Factor.objects.filter(pk=f3.pk).exists())

    def test_factor_usado_en_evaluaciones_solo_se_desactiva(self):
        _, f1, _, _ = crear_catalogo()
        ev = Evaluacion.objects.create(nombre='E', software='S', usuario=self.admin)
        ValorFactor.objects.create(evaluacion=ev, factor=f1, sugerida=3, decisor=3, alcance='Interno')
        respuesta = self.client.post(reverse('panel_factor_eliminar', args=[f1.pk]), follow=True)
        self.assertTrue(Factor.objects.filter(pk=f1.pk).exists())
        self.assertContains(respuesta, 'desactívelo')

    def test_crud_subfactor(self):
        _, f1, _, subs = crear_catalogo()
        self.client.post(reverse('panel_subfactor_nuevo'), {'factor': f1.pk, 'nombre': 'Nuevo', 'activo': 'on'})
        nuevo = Subfactor.objects.get(nombre='Nuevo')
        self.client.post(reverse('panel_subfactor_editar', args=[nuevo.pk]), {'factor': f1.pk, 'nombre': 'Otro'})
        nuevo.refresh_from_db()
        self.assertEqual((nuevo.nombre, nuevo.activo), ('Otro', False))
        self.assertContains(self.client.get(reverse('panel_subfactores'), {'factor': f1.pk}), 'Otro')
        self.client.post(reverse('panel_subfactor_eliminar', args=[nuevo.pk]))
        self.assertFalse(Subfactor.objects.filter(pk=nuevo.pk).exists())

    def test_subfactor_valorado_no_se_elimina(self):
        _, f1, _, subs = crear_catalogo()
        ev = Evaluacion.objects.create(nombre='E', software='S', usuario=self.admin)
        vf = ValorFactor.objects.create(evaluacion=ev, factor=f1, sugerida=3, decisor=3, alcance='Interno')
        ValorSubfactor.objects.create(valor_factor=vf, subfactor=subs[0], valor=3)
        self.client.post(reverse('panel_subfactor_eliminar', args=[subs[0].pk]))
        self.assertTrue(Subfactor.objects.filter(pk=subs[0].pk).exists())

    def test_el_catalogo_editado_se_usa_en_el_formulario_de_evaluacion(self):
        dimension, f1, _, _ = crear_catalogo()
        Factor.objects.filter(pk=f1.pk).update(activo=False)
        self.assertNotContains(self.client.get(reverse('nueva')), 'name="decisor_%d"' % f1.pk)


class PanelUsuariosTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario('admin', ADMIN)
        self.client.force_login(self.admin)

    def datos(self, **extra):
        base = {'username': 'maria', 'first_name': 'María', 'last_name': 'Paz', 'email': 'm@e.com',
                'is_active': 'on', 'rol': CONSULTOR, 'password1': CLAVE_FUERTE, 'password2': CLAVE_FUERTE}
        base.update(extra)
        return base

    def test_crear_usuario_con_rol_y_contrasena(self):
        self.client.post(reverse('panel_usuario_nuevo'), self.datos())
        usuario = User.objects.get(username='maria')
        self.assertEqual(rol(usuario), CONSULTOR)
        self.assertTrue(self.client.login(username='maria', password=CLAVE_FUERTE))

    def test_contrasena_debil_o_distinta_se_rechaza(self):
        self.client.post(reverse('panel_usuario_nuevo'), self.datos(password1='123', password2='123'))
        self.client.post(reverse('panel_usuario_nuevo'), self.datos(password2='otra-Clave-9'))
        self.client.post(reverse('panel_usuario_nuevo'), self.datos(password1='', password2=''))
        self.assertFalse(User.objects.filter(username='maria').exists())

    def test_editar_rol_sin_cambiar_contrasena(self):
        maria = crear_usuario('maria')
        self.client.post(reverse('panel_usuario_editar', args=[maria.pk]), self.datos(
            rol=ADMIN, password1='', password2=''))
        maria = User.objects.get(pk=maria.pk)
        self.assertEqual(rol(maria), ADMIN)
        self.assertTrue(maria.check_password(CLAVE_FUERTE))
        self.assertEqual(maria.groups.count(), 1)

    def test_desactivar_usuario_le_impide_ingresar(self):
        maria = crear_usuario('maria')
        datos = self.datos(password1='', password2='')
        del datos['is_active']
        self.client.post(reverse('panel_usuario_editar', args=[maria.pk]), datos)
        self.assertFalse(self.client.login(username='maria', password=CLAVE_FUERTE))

    def test_no_se_puede_dejar_el_sistema_sin_administrador(self):
        respuesta = self.client.post(reverse('panel_usuario_editar', args=[self.admin.pk]), self.datos(
            username='admin', rol=EVALUADOR, password1='', password2=''))
        self.assertContains(respuesta, 'al menos un administrador')
        self.assertEqual(rol(User.objects.get(pk=self.admin.pk)), ADMIN)

    def test_puede_degradarse_si_hay_otro_administrador(self):
        otro = crear_usuario('otro', ADMIN)
        self.client.post(reverse('panel_usuario_editar', args=[otro.pk]), self.datos(
            username='otro', rol=EVALUADOR, password1='', password2=''))
        self.assertEqual(rol(User.objects.get(pk=otro.pk)), EVALUADOR)

    def test_no_puede_desactivarse_a_si_mismo(self):
        crear_usuario('otro', ADMIN)
        datos = self.datos(username='admin', rol=ADMIN, password1='', password2='')
        del datos['is_active']
        respuesta = self.client.post(reverse('panel_usuario_editar', args=[self.admin.pk]), datos)
        self.assertContains(respuesta, 'propia cuenta')
        self.assertTrue(User.objects.get(pk=self.admin.pk).is_active)

    def test_superusuario_conserva_el_rol_administrador(self):
        root = User.objects.create_superuser('root', 'r@e.com', CLAVE_FUERTE)
        self.client.post(reverse('panel_usuario_editar', args=[root.pk]), self.datos(
            username='root', rol=EVALUADOR, password1='', password2=''))
        self.assertEqual(rol(User.objects.get(pk=root.pk)), ADMIN)

    def test_eliminar_usuario_y_sus_bloqueos(self):
        crear_catalogo()
        con_historial = crear_usuario('hist')
        evaluacion_finalizada(con_historial)
        self.client.post(reverse('panel_usuario_eliminar', args=[con_historial.pk]))
        self.assertTrue(User.objects.filter(pk=con_historial.pk).exists())
        self.client.post(reverse('panel_usuario_eliminar', args=[self.admin.pk]))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        libre = crear_usuario('libre')
        self.client.post(reverse('panel_usuario_eliminar', args=[libre.pk]))
        self.assertFalse(User.objects.filter(pk=libre.pk).exists())

    def test_listado_muestra_rol_y_busca(self):
        crear_usuario('lucia', CONSULTOR)
        crear_usuario('pedro')
        pagina = self.client.get(reverse('panel_usuarios'), {'q': 'luc'})
        self.assertContains(pagina, 'lucia')
        self.assertContains(pagina, CONSULTOR)
        self.assertNotContains(pagina, 'pedro')


class PanelEvaluacionesYConfiguracionTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario('admin', ADMIN)
        self.eva = crear_usuario('eva')
        crear_catalogo()
        self.ev = evaluacion_finalizada(self.eva)
        self.client.force_login(self.admin)

    def test_el_administrador_ve_y_elimina_cualquier_evaluacion(self):
        self.assertContains(self.client.get(reverse('panel_evaluaciones'), {'q': 'eva'}), 'Software X')
        self.assertContains(self.client.get(reverse('panel_evaluaciones'), {'estado': 'FINALIZADA'}), 'Software X')
        self.assertNotContains(self.client.get(reverse('panel_evaluaciones'), {'estado': 'EN_PROCESO'}), 'Software X')
        self.client.post(reverse('panel_evaluacion_eliminar', args=[self.ev.pk]))
        self.assertFalse(Evaluacion.objects.exists())

    def test_cambiar_configuracion_y_cerrar_registro(self):
        self.client.post(reverse('configuracion'), {'metodo_importancia': 'IA'})
        config = ConfiguracionSistema.actual()
        self.assertEqual((config.metodo_importancia, config.registro_abierto), ('IA', False))
        self.client.logout()
        self.assertNotContains(self.client.get(reverse('login')), reverse('registro'))
        respuesta = self.client.post(reverse('registro'), {
            'username': 'intruso', 'password1': CLAVE_FUERTE, 'password2': CLAVE_FUERTE})
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(User.objects.filter(username='intruso').exists())

    def test_metodo_invalido(self):
        self.client.post(reverse('configuracion'), {'metodo_importancia': 'XX'})
        self.assertEqual(ConfiguracionSistema.actual().metodo_importancia, 'TESIS')

    def test_registro_abierto_crea_evaluador(self):
        self.client.logout()
        self.client.post(reverse('registro'), {
            'username': 'nuevo', 'password1': CLAVE_FUERTE, 'password2': CLAVE_FUERTE})
        self.assertEqual(rol(User.objects.get(username='nuevo')), EVALUADOR)

    def test_registro_rechaza_contrasena_debil(self):
        self.client.logout()
        self.client.post(reverse('registro'), {'username': 'nuevo', 'password1': '12345678', 'password2': '12345678'})
        self.assertFalse(User.objects.filter(username='nuevo').exists())


class CatalogoComandoTests(TestCase):
    def test_importa_el_catalogo_oficial(self):
        call_command('importar_catalogo', verbosity=0)
        self.assertEqual((Dimension.objects.count(), Factor.objects.count(), Subfactor.objects.count()), (3, 18, 61))

    def test_no_pisa_lo_editado_en_el_panel(self):
        call_command('importar_catalogo', verbosity=0)
        factor = Factor.objects.get(nombre='Compatibilidad')
        Factor.objects.filter(pk=factor.pk).update(sugerida=1)
        sub = factor.subfactores.first()
        Subfactor.objects.filter(pk=sub.pk).update(nombre='Renombrado')
        call_command('importar_catalogo', verbosity=0)
        self.assertEqual(Factor.objects.get(pk=factor.pk).sugerida, 1)
        self.assertEqual(Subfactor.objects.count(), 61)

    def test_actualizar_restablece_los_valores_de_referencia(self):
        call_command('importar_catalogo', verbosity=0)
        Factor.objects.filter(nombre='Compatibilidad').update(sugerida=1)
        call_command('importar_catalogo', actualizar=True, verbosity=0)
        self.assertEqual(Factor.objects.get(nombre='Compatibilidad').sugerida, 3)


class GeminiServicioTests(TestCase):
    def setUp(self):
        cache.clear()
        self.eva = crear_usuario('eva')
        self.dim, self.f1, self.f2, self.subs = crear_catalogo()

    def lote(self):
        return [(self.f1.pk, 'Interno', [self.subs[0].pk, self.subs[1].pk])]

    def respuesta_valida(self):
        return {'factores': [{'id': self.f1.pk, 'sugerida': 3, 'decisor': 4, 'alcance': 'Interno',
                              'justificacion': 'ok', 'subfactores': [
                                  {'id': self.subs[0].pk, 'valor': 2}, {'id': self.subs[1].pk, 'valor': 4}]}]}

    def test_validar_lote_correcto(self):
        salida = gemini_service._validar_lote(self.respuesta_valida(), self.lote())
        self.assertEqual(salida[0]['decisor'], 4)
        self.assertEqual([s['valor'] for s in salida[0]['subfactores']], [2, 4])

    def test_validar_lote_rechaza_respuestas_invalidas(self):
        casos = []
        malo = self.respuesta_valida(); malo['factores'][0]['sugerida'] = 5; casos.append(malo)
        malo = self.respuesta_valida(); malo['factores'][0]['subfactores'].pop(); casos.append(malo)
        malo = self.respuesta_valida(); malo['factores'][0]['id'] = 999; casos.append(malo)
        malo = self.respuesta_valida(); malo['factores'][0]['decisor'] = True; casos.append(malo)
        casos += [{}, {'factores': 'x'}]
        for caso in casos:
            with self.assertRaises(GeminiNoDisponible):
                gemini_service._validar_lote(caso, self.lote())

    def test_alcance_del_catalogo_prevalece(self):
        datos = self.respuesta_valida()
        datos['factores'][0]['alcance'] = 'Externo'
        self.assertEqual(gemini_service._validar_lote(datos, self.lote())[0]['alcance'], 'Interno')

    def test_reintenta_ante_503_y_luego_responde(self):
        from google.genai import errors
        cliente = mock.Mock()
        cliente.models.generate_content.side_effect = [
            errors.ServerError(503, {'error': {'message': 'saturado'}}),
            errors.ServerError(503, {'error': {'message': 'saturado'}}), 'RESPUESTA']
        with mock.patch.object(gemini_service.time, 'sleep') as dormir:
            self.assertEqual(gemini_service._generar(cliente, errors, model='m'), 'RESPUESTA')
        self.assertEqual(dormir.call_count, 2)

    def test_503_persistente_se_informa_sin_reintentar_para_siempre(self):
        from google.genai import errors
        cliente = mock.Mock()
        cliente.models.generate_content.side_effect = errors.ServerError(503, {'error': {'message': 's'}})
        with mock.patch.object(gemini_service.time, 'sleep'):
            with self.assertRaises(GeminiNoDisponible):
                gemini_service._generar(cliente, errors, model='m')
        self.assertEqual(cliente.models.generate_content.call_count, gemini_service.MAX_INTENTOS)

    def test_error_no_temporal_no_se_reintenta(self):
        from google.genai import errors
        cliente = mock.Mock()
        cliente.models.generate_content.side_effect = errors.ServerError(501, {'error': {'message': 'x'}})
        with mock.patch.object(gemini_service.time, 'sleep'):
            with self.assertRaises(errors.ServerError):
                gemini_service._generar(cliente, errors, model='m')
        self.assertEqual(cliente.models.generate_content.call_count, 1)

    @override_settings(GEMINI_API_KEY='')
    def test_sin_clave_se_informa(self):
        with self.assertRaises(GeminiNoDisponible):
            gemini_service.generar_sugerencias('S', '', '', [self.f1])

    def test_sugerencias_en_lotes_paralelos_conservan_el_orden(self):
        from google.genai import types
        dimension = self.dim
        for n in range(5):  # 7 factores en total -> 3 lotes
            factor = Factor.objects.create(dimension=dimension, nombre=f'X{n}', alcance='Ambos')
            Subfactor.objects.create(factor=factor, nombre=f'XS{n}')

        def generar(model, contents, config):
            catalogo = json.loads(contents)['catalogo']
            return SimpleNamespace(text=json.dumps({'factores': [
                {'id': c['id'], 'sugerida': 2, 'decisor': 3, 'alcance': 'Externo', 'justificacion': 'j',
                 'subfactores': [{'id': s['id'], 'valor': 3} for s in c['subfactores']]} for c in catalogo]}))

        cliente = mock.MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.models.generate_content.side_effect = generar
        falso_genai = SimpleNamespace(Client=mock.Mock(return_value=cliente))
        from google.genai import errors
        factores = list(Factor.objects.select_related('dimension').prefetch_related('subfactores').order_by('id'))
        with override_settings(GEMINI_API_KEY='k'), mock.patch.object(
                gemini_service, '_dependencias', return_value=('k', falso_genai, types, errors)):
            salida = gemini_service.generar_sugerencias('S', 'O', 'D', factores)
        self.assertEqual([s['id'] for s in salida], [f.pk for f in factores])
        self.assertEqual(cliente.models.generate_content.call_count, 3)
        self.assertEqual(salida[0]['alcance'], 'Interno')  # F1 es Interno en el catálogo


class IaVistasTests(TestCase):
    def setUp(self):
        cache.clear()
        self.eva = crear_usuario('eva')
        self.dim, self.f1, self.f2, self.subs = crear_catalogo()
        self.client.force_login(self.eva)

    def sugerencia(self):
        return [{'id': self.f1.pk, 'sugerida': 1, 'decisor': 3, 'alcance': 'Interno', 'justificacion': 'x',
                 'subfactores': []}]

    def test_modo_tesis_conserva_la_sugerida_del_catalogo(self):
        with mock.patch('evaluaciones.views.generar_sugerencias', return_value=self.sugerencia()):
            datos = self.client.post(reverse('sugerir_ia'), {'software': 'S'}).json()
        self.assertEqual(datos['factores'][0]['sugerida'], 3)
        self.assertEqual(datos['metodo'], 'TESIS')

    def test_error_de_gemini_devuelve_503_controlado(self):
        with mock.patch('evaluaciones.views.generar_sugerencias', side_effect=GeminiNoDisponible('caído')):
            respuesta = self.client.post(reverse('sugerir_ia'), {'software': 'S'})
        self.assertEqual((respuesta.status_code, respuesta.json()['error']), (503, 'caído'))

    def test_requiere_software_y_post(self):
        self.assertEqual(self.client.post(reverse('sugerir_ia'), {'software': ' '}).status_code, 400)
        self.assertEqual(self.client.get(reverse('sugerir_ia')).status_code, 405)

    @override_settings(IA_LIMITE_POR_HORA=2)
    def test_limite_por_usuario_y_hora(self):
        with mock.patch('evaluaciones.views.generar_sugerencias', return_value=self.sugerencia()):
            codigos = [self.client.post(reverse('sugerir_ia'), {'software': 'S'}).status_code for _ in range(3)]
        self.assertEqual(codigos, [200, 200, 429])
        otro = crear_usuario('otro')
        self.client.force_login(otro)
        with mock.patch('evaluaciones.views.generar_sugerencias', return_value=self.sugerencia()):
            self.assertEqual(self.client.post(reverse('sugerir_ia'), {'software': 'S'}).status_code, 200)

    def test_justificacion_ia_se_guarda_y_no_cambia_el_dictamen(self):
        ev = evaluacion_finalizada(self.eva)
        with mock.patch('evaluaciones.views.generar_justificacion', return_value='Texto IA'):
            self.client.post(reverse('generar_ia', args=[ev.pk]))
        resultado = ResultadoEvaluacion.objects.get(evaluacion=ev)
        self.assertEqual((resultado.justificacion_ia, resultado.recomendacion), ('Texto IA', 'A'))

    def test_justificacion_exige_evaluacion_finalizada(self):
        borrador = Evaluacion.objects.create(nombre='B', software='S', usuario=self.eva)
        with mock.patch('evaluaciones.views.generar_justificacion') as llamada:
            self.client.post(reverse('generar_ia', args=[borrador.pk]))
        llamada.assert_not_called()

    @override_settings(IA_LIMITE_POR_HORA=1)
    def test_limite_tambien_aplica_a_la_justificacion(self):
        ev = evaluacion_finalizada(self.eva)
        with mock.patch('evaluaciones.views.generar_justificacion', return_value='T') as llamada:
            self.client.post(reverse('generar_ia', args=[ev.pk]))
            self.client.post(reverse('generar_ia', args=[ev.pk]))
        self.assertEqual(llamada.call_count, 1)

    def test_pdf_incluye_el_informe(self):
        ev = evaluacion_finalizada(self.eva)
        respuesta = self.client.get(reverse('informe_pdf', args=[ev.pk]))
        self.assertEqual((respuesta.status_code, respuesta['Content-Type']), (200, 'application/pdf'))
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
