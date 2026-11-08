"""Pruebas del formulario nuevo de Tania, sin Discord ni datos reales."""

import unittest

import metas_reporte as m


class RosterTests(unittest.TestCase):
    def test_reportes_nuevos_excluyen_yuselis_e_incluyen_karina(self):
        claves = [t["key"] for t in m.trabajadores_produccion_activos()]
        self.assertNotIn("yuselis_m", claves)
        self.assertIn("karina_r", claves)
        self.assertEqual(
            claves,
            [
                "adrian_l",
                "angel_l",
                "jose_m_p",
                "luis_p",
                "maria_r",
                "margaret_m",
                "karina_r",
            ],
        )
        self.assertFalse(m.YUSELIS_HISTORICA["activa"])
        self.assertEqual(m.YUSELIS_HISTORICA["nombre"], "Yuselis M.")

    def test_karina_tiene_exactamente_las_metas_de_maria(self):
        self.assertEqual(m.metas_de("karina_r"), m.metas_de("maria_r"))
        self.assertEqual(
            m.metas_de("maria_r"),
            (m.META_ASISTENCIA, m.META_LICUADAS),
        )
        self.assertEqual(m.metas_de("maria_r"), m.METAS_MARIA_Y_KARINA)

    def test_no_hay_otra_trabajadora_rosario(self):
        nombres = [t["nombre"] for t in m.trabajadores_produccion_activos()]
        self.assertIn("María R.", nombres)
        self.assertNotIn("Rosario", nombres)
        self.assertNotIn("Rosario R.", nombres)
        claves = [t["key"] for t in m.trabajadores_produccion_activos()]
        self.assertNotIn("rosario", claves)
        self.assertNotIn("rosario_r", claves)

    def test_otros_trabajadores_conservan_sus_metas(self):
        self.assertEqual(
            m.metas_de("adrian_l"),
            (
                m.META_ASISTENCIA_ENVASADO,
                m.META_TIEMPO_BATIDA,
                m.META_PROTOCOLO_BATIDORAS,
                m.META_AGUA_SAL,
                m.META_ENVASADO,
                m.META_ALISTAMIENTO_TARDE,
                m.META_CIERRE,
            ),
        )
        self.assertEqual(
            m.metas_de("angel_l"),
            (
                m.META_ASISTENCIA_ENVASADO,
                m.META_ENVASADO,
                m.META_ALISTAMIENTO_TARDE,
                m.META_CIERRE,
            ),
        )
        self.assertEqual(m.metas_de("jose_m_p"), m.metas_de("angel_l"))
        self.assertEqual(
            m.metas_de("luis_p"),
            (
                m.META_ASISTENCIA_ENVASADO,
                m.META_TIEMPO_BATIDA,
                m.META_ENVASADO,
                m.META_ALISTAMIENTO_TARDE,
                m.META_CIERRE,
            ),
        )
        self.assertEqual(
            m.metas_de("margaret_m"),
            (m.META_ASISTENCIA, m.META_IMPLEMENTOS, m.META_REPORTE_MATERIA),
        )
        self.assertEqual(
            m.metas_de("yuselis_m"),
            (
                m.META_ASISTENCIA_ENVASADO,
                m.META_PROTOCOLO_BATIDORAS,
                m.META_AGUA_SAL,
                m.META_ENVASADO,
                m.META_ALISTAMIENTO_TARDE,
                m.META_CIERRE,
            ),
        )

    def test_pregunta_de_rendimiento_solo_en_maria_y_karina(self):
        items = m.items_personas_tania()
        claves = [item["key"] for item in items]
        self.assertNotIn("yuselis_m", claves)
        self.assertNotIn("rendimiento_crema_yuselis_m", claves)
        crema = [item for item in items if item["tipo"] == m.TIPO_RENDIMIENTO_CREMA]
        self.assertEqual(
            [item["trabajador_key"] for item in crema],
            ["maria_r", "karina_r"],
        )
        for item in crema:
            self.assertIn(m.PREGUNTA_RENDIMIENTO_CREMA, item["texto"])
            self.assertNotIn("suficientes vasitos disponibles", item["texto"].lower())
            self.assertNotIn("sin interrupciones", item["texto"].lower())
            self.assertIn("no disponibilidad", item["reglas"].lower() + item["texto"].lower())
        textos_otros = [
            item["texto"]
            for item in items
            if item["trabajador_key"] not in {"maria_r", "karina_r"}
        ]
        for texto in textos_otros:
            self.assertNotIn(m.PREGUNTA_RENDIMIENTO_CREMA, texto)

    def test_la_pregunta_no_inventa_cantidad(self):
        self.assertNotIn("80", m.PREGUNTA_RENDIMIENTO_CREMA)
        self.assertNotIn("estipulada de", m.PREGUNTA_RENDIMIENTO_CREMA)
        for item in m.items_personas_tania():
            if item["tipo"] == m.TIPO_RENDIMIENTO_CREMA:
                self.assertIn("cantidad de vasitos estipulada vigente", item["texto"])


class PolaridadTests(unittest.TestCase):
    def test_si_cumple_y_no_afecta_extras(self):
        for texto in (
            "Sí",
            "si",
            "Sí, rindió la cantidad estipulada",
            "Sí, aunque hubo una pausa por otra cosa, rindió lo estipulado",
        ):
            self.assertEqual(m.clasificar_rendimiento_crema(texto), "cumple", texto)
            self.assertFalse(m.afecta_extras("cumple"))

    def test_no_por_manejo_o_endurecimiento_incumple(self):
        for texto in (
            "No, la manejaron mal",
            "No, manejo incorrecto del turno de la mañana",
            "No, la crema se endureció",
            "No, se endureció",
            "No rindió porque se endureció la crema",
            "Salieron menos porque la dejaron endurecer",
            "No, sacaron la crema mal",
        ):
            self.assertEqual(m.clasificar_rendimiento_crema(texto), "incumple", texto)
            self.assertTrue(m.afecta_extras("incumple"))

    def test_sin_respuesta_o_sin_evidencia_queda_pendiente(self):
        for texto in ("", "   ", None, "No", "No sé", "No estoy segura", "Pendiente"):
            self.assertEqual(m.clasificar_rendimiento_crema(texto), "pendiente", texto)
            self.assertFalse(m.afecta_extras("pendiente"))

    def test_otra_causa_no_se_atribuye_a_la_meta(self):
        for texto in (
            "No, faltaron vasitos",
            "No porque no había envases",
            "No, se acabaron los vasitos y no pudieron envasar",
            "No rindió porque se fue la luz",
            "No, se dañó la batidora",
            "Salieron menos porque no hubo producción",
            "No, el turno de la tarde dejó endurecer la crema",
            "No, se endureció porque faltaron vasitos",
            "Se endureció, pero no hay evidencia de que fuera la mañana",
        ):
            self.assertEqual(m.clasificar_rendimiento_crema(texto), "pendiente", texto)

    def test_un_si_no_se_convierte_en_falta_de_envases(self):
        self.assertEqual(
            m.clasificar_rendimiento_crema("Sí, pero faltaron vasitos"),
            "cumple",
        )


class HistoricoTests(unittest.TestCase):
    def test_exportar_no_toca_respuestas_ni_pagos_viejos(self):
        historico = {
            "yuselis_m": "Sí, cumplió alistamiento",
            "maria_r": "Sí",
            "pago_aprobado_cop": "50000",
        }
        antes = dict(historico)
        out = m.exportar_evaluacion(historico)
        self.assertEqual(historico, antes)
        self.assertEqual(out["answers"], historico)
        self.assertEqual(out["answers"]["yuselis_m"], "Sí, cumplió alistamiento")
        self.assertEqual(out["evaluacion_rendimiento_crema"], {})
        self.assertNotIn("pago", str(out["evaluacion_rendimiento_crema"]))

    def test_pregunta_ausente_no_inventa_incumplimiento(self):
        out = m.exportar_evaluacion({"maria_r": "No", "karina_r": "Sí"})
        self.assertEqual(out["evaluacion_rendimiento_crema"], {})
        self.assertEqual(out["answers"]["maria_r"], "No")

    def test_reporte_nuevo_anota_polaridad_sin_borrar_historico_mezclado(self):
        mixto = {
            "yuselis_m": "No, llegó tarde",
            "pago_aprobado_cop": "15000",
            "rendimiento_crema_maria_r": "Sí",
            "rendimiento_crema_karina_r": "No, la crema se endureció",
        }
        out = m.exportar_evaluacion(mixto)
        self.assertEqual(out["answers"]["yuselis_m"], "No, llegó tarde")
        self.assertEqual(out["answers"]["pago_aprobado_cop"], "15000")
        self.assertEqual(mixto["pago_aprobado_cop"], "15000")
        maria = out["evaluacion_rendimiento_crema"]["rendimiento_crema_maria_r"]
        karina = out["evaluacion_rendimiento_crema"]["rendimiento_crema_karina_r"]
        self.assertEqual(maria["polaridad"], "cumple")
        self.assertFalse(maria["afecta_extras"])
        self.assertEqual(karina["polaridad"], "incumple")
        self.assertTrue(karina["afecta_extras"])
        self.assertNotIn("yuselis_m", out["evaluacion_rendimiento_crema"])

    def test_respuesta_vacia_de_la_pregunta_nueva_queda_pendiente(self):
        out = m.exportar_evaluacion(
            {
                "rendimiento_crema_maria_r": "",
                "rendimiento_crema_karina_r": "No, faltaron vasitos",
            }
        )
        self.assertEqual(
            out["evaluacion_rendimiento_crema"]["rendimiento_crema_maria_r"]["polaridad"],
            "pendiente",
        )
        self.assertFalse(
            out["evaluacion_rendimiento_crema"]["rendimiento_crema_maria_r"]["afecta_extras"]
        )
        self.assertEqual(
            out["evaluacion_rendimiento_crema"]["rendimiento_crema_karina_r"]["polaridad"],
            "pendiente",
        )


class FormularioDiscordTests(unittest.TestCase):
    def test_flujo_real_de_tania_usa_el_roster_nuevo(self):
        import bot_desempeno as bot

        claves = [item["key"] for item in bot.TANIA_FLOW]
        self.assertNotIn("yuselis_m", claves)
        self.assertIn("karina_r", claves)
        self.assertIn("maria_r", claves)
        self.assertEqual(
            [c for c in claves if c.startswith("rendimiento_crema_")],
            ["rendimiento_crema_maria_r", "rendimiento_crema_karina_r"],
        )
        por_clave = {item["key"]: item for item in bot.TANIA_FLOW}
        self.assertEqual(
            por_clave["karina_r"]["texto"].replace("Karina R.", "María R."),
            por_clave["maria_r"]["texto"],
        )
        for clave in ("rendimiento_crema_maria_r", "rendimiento_crema_karina_r"):
            self.assertIn(m.PREGUNTA_RENDIMIENTO_CREMA, por_clave[clave]["texto"])
            self.assertEqual(por_clave[clave]["tipo"], m.TIPO_RENDIMIENTO_CREMA)
        ronald = [item["key"] for item in bot.RONALD_FLOW]
        self.assertNotIn("karina_r", ronald)
        self.assertNotIn("yuselis_m", ronald)
        self.assertNotIn("rendimiento_crema_maria_r", ronald)


if __name__ == "__main__":
    unittest.main()
