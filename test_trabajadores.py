"""Lista activa del reporte de Tania: Yuselis fuera, Karina igual que Rosario."""

import os
import unittest

os.environ.setdefault("TOKEN", "test-token")
os.environ.setdefault("CHANNEL_ID", "1")
os.environ.setdefault("XAI_API_KEY", "test-key")

import bot_desempeno as bot  # noqa: E402


class TrabajadoresProduccionTest(unittest.TestCase):
    def test_yuselis_no_entra_en_reportes_nuevos(self):
        claves = [t["key"] for t in bot.TRABAJADORES_PRODUCCION]
        nombres = [t["nombre"] for t in bot.TRABAJADORES_PRODUCCION]
        self.assertNotIn("yuselis_m", claves)
        self.assertNotIn("Yuselis M.", nombres)
        flow_keys = [item["key"] for item in bot.TANIA_FLOW]
        self.assertNotIn("yuselis_m", flow_keys)
        textos = "\n".join(item["texto"] for item in bot.TANIA_FLOW)
        self.assertNotIn("Yuselis", textos)

    def test_historial_de_yuselis_sigue_en_el_codigo(self):
        ficha = bot.YUSELIS_HISTORICA
        self.assertEqual(ficha["key"], "yuselis_m")
        self.assertEqual(ficha["nombre"], "Yuselis M.")
        self.assertEqual(
            ficha["metas"],
            [
                bot.META_ASISTENCIA_ENVASADO,
                bot.META_PROTOCOLO_BATIDORAS,
                bot.META_AGUA_SAL,
                bot.META_ENVASADO,
                bot.META_ALISTAMIENTO_TARDE,
                bot.META_CIERRE,
            ],
        )

    def test_karina_tiene_las_mismas_metas_que_rosario(self):
        por_clave = {t["key"]: t for t in bot.TRABAJADORES_PRODUCCION}
        maria = por_clave["maria_r"]
        karina = por_clave["karina_r"]
        self.assertEqual(maria["nombre"], "María R.")
        self.assertEqual(karina["nombre"], "Karina R.")
        self.assertIs(karina["metas"], maria["metas"])
        self.assertEqual(karina["metas"], bot.METAS_MARIA_ROSARIO)
        self.assertEqual(len(karina["metas"]), 2)

        pregunta_maria = bot._pregunta_cumplimiento(maria["nombre"], maria["metas"])
        pregunta_karina = bot._pregunta_cumplimiento(karina["nombre"], karina["metas"])
        self.assertEqual(
            pregunta_karina,
            pregunta_maria.replace("María R.", "Karina R."),
        )
        item_maria = next(i for i in bot.TANIA_FLOW if i["key"] == "maria_r")
        item_karina = next(i for i in bot.TANIA_FLOW if i["key"] == "karina_r")
        self.assertEqual(item_karina["tipo"], item_maria["tipo"])
        self.assertEqual(item_karina["reglas"], item_maria["reglas"])
        self.assertEqual(item_karina["reglas"], bot.REGLAS_CUMPLIMIENTO_TRABAJADOR)

    def test_el_resto_de_produccion_no_cambia(self):
        por_clave = {t["key"]: t["metas"] for t in bot.TRABAJADORES_PRODUCCION}
        self.assertEqual(
            [t["key"] for t in bot.TRABAJADORES_PRODUCCION],
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
        self.assertEqual(
            por_clave["adrian_l"],
            [
                bot.META_ASISTENCIA_ENVASADO,
                bot.META_TIEMPO_BATIDA,
                bot.META_PROTOCOLO_BATIDORAS,
                bot.META_AGUA_SAL,
                bot.META_ENVASADO,
                bot.META_ALISTAMIENTO_TARDE,
                bot.META_CIERRE,
            ],
        )
        self.assertEqual(
            por_clave["angel_l"],
            [
                bot.META_ASISTENCIA_ENVASADO,
                bot.META_ENVASADO,
                bot.META_ALISTAMIENTO_TARDE,
                bot.META_CIERRE,
            ],
        )
        self.assertEqual(por_clave["jose_m_p"], por_clave["angel_l"])
        self.assertEqual(
            por_clave["luis_p"],
            [
                bot.META_ASISTENCIA_ENVASADO,
                bot.META_TIEMPO_BATIDA,
                bot.META_ENVASADO,
                bot.META_ALISTAMIENTO_TARDE,
                bot.META_CIERRE,
            ],
        )
        self.assertEqual(
            por_clave["margaret_m"],
            [
                bot.META_ASISTENCIA,
                (
                    "Implementos listos para la siguiente jornada: vasitos, tapitas y "
                    "complementos separados, contados y ubicados en su lugar antes de "
                    "terminar, para que la producción no se detenga al día siguiente."
                ),
                (
                    "Reporte diario de materia prima: inventario inicial y final en bultos, "
                    "consumo de adicionales e insumos próximos a agotarse, enviado "
                    "completo el mismo día (no al día siguiente)."
                ),
            ],
        )

    def test_orden_del_reporte_de_tania_y_ronald_intacto(self):
        self.assertEqual(
            [item["key"] for item in bot.TANIA_FLOW],
            [
                "alistamiento",
                "produccion",
                "adrian_l",
                "angel_l",
                "jose_m_p",
                "luis_p",
                "maria_r",
                "margaret_m",
                "karina_r",
                "incidencia",
                "notas",
            ],
        )
        self.assertEqual(
            [item["key"] for item in bot.RONALD_FLOW],
            [
                "q1",
                "q2",
                "q3",
                "q5",
                "q6",
                "q7",
                "q8",
                "q9",
                "q10",
                "q11",
                "q12",
                "incidencia",
                "notas",
            ],
        )


if __name__ == "__main__":
    unittest.main()
