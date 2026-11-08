"""Metas del reporte conversacional de Tania y polaridad del rendimiento de crema.

María R. es María del Rosario Reverón Caicedo (nómina y ficha de trabajadora).
En las instrucciones aparece como «María» y como «Rosario»: es la misma persona.
No se crea otra trabajadora ni se renombra la clave histórica ``maria_r``.

Yuselis M. ya no entra en reportes nuevos. Su ficha queda solo como registro
histórico para no perder el significado de respuestas ya dadas. Este módulo
no borra, reescribe ni recalcula esas respuestas, ni toca pagos.
"""

from __future__ import annotations

import re
import unicodedata

# ==================== METAS COMPARTIDAS (texto vigente del formulario) ====================
META_ASISTENCIA = (
    "Asistencia y puntualidad: llegó a la hora acordada y registró huella "
    "al entrar y al salir."
)
META_ASISTENCIA_ENVASADO = (
    META_ASISTENCIA + " En turno de envasado el día solo cuenta si también "
    "se cumplió el tiempo de envasado."
)
META_ENVASADO = (
    "Tiempo de envasado (turno tarde): 14 segundos por vasito con 4 trabajadores, "
    "18 s con 3, o 26 s con 2."
)
META_CIERRE = (
    "Protocolo diario de cierre (turno tarde): se cumplió el 100% y se envió "
    "toda la información solicitada."
)
META_ALISTAMIENTO_TARDE = (
    "Alistamiento de pedidos (turno tarde): pedidos del día siguiente completos "
    "y sin errores (no cuenta si se alistaron el mismo día o a medias)."
)
META_TIEMPO_BATIDA = (
    "Tiempo de producción por batida (turno mañana): promedio de 30 minutos o menos."
)
META_PROTOCOLO_BATIDORAS = (
    "Protocolo de encendido y apagado de las batidoras (turno mañana), "
    "reportando todo lo solicitado."
)
META_AGUA_SAL = (
    "Agua sal de las batidoras (turno mañana): máximo 1 cambio por batidora "
    "cada dos meses. Si hoy hubo cambio, debe reportarse."
)
META_LICUADAS = (
    "Licuadas y alistamiento de materiales (turno mañana): las batidas "
    "del día sin errores de fórmula, tanto en la preparación de las "
    "licuadas como en el alistamiento de los materiales."
)
META_IMPLEMENTOS = (
    "Implementos listos para la siguiente jornada: vasitos, tapitas y "
    "complementos separados, contados y ubicados en su lugar antes de "
    "terminar, para que la producción no se detenga al día siguiente."
)
META_REPORTE_MATERIA = (
    "Reporte diario de materia prima: inventario inicial y final en bultos, "
    "consumo de adicionales e insumos próximos a agotarse, enviado "
    "completo el mismo día (no al día siguiente)."
)

# Indicadores que el formulario ya le pregunta a María. Karina usa esta misma
# lista, sin sumar metas de otros turnos. El rendimiento de crema no va aquí:
# tiene pregunta y polaridad propias.
METAS_MARIA_Y_KARINA = (
    META_ASISTENCIA,
    META_LICUADAS,
)

REGLAS_CUMPLIMIENTO_TRABAJADOR = (
    "Sí/No válido. 'Sí' = cumplió todas las metas que aplicaron hoy. "
    "'No' ES válido y puede indicar cuáles no cumplió "
    "(ej. 'No, llegó tarde' / 'No, se pasaron en envasado'). "
    "'No vino' / 'No trabajó' / 'N/A' / 'No aplica' ES válido si no correspondía el día "
    "o no hubo producción en su turno. "
    "Detalle es bienvenido pero no obligatorio si dice sí o no con claridad."
)

# Pregunta pedida por Ronald. No es inventario de envases.
PREGUNTA_RENDIMIENTO_CREMA = (
    "¿La crema preparada por el turno de la mañana rindió la cantidad de vasitos estipulada?"
)
TIPO_RENDIMIENTO_CREMA = "rendimiento_crema"
POLARIDADES = ("cumple", "incumple", "pendiente")

REGLAS_RENDIMIENTO_CREMA = (
    "Rendimiento de la crema del turno de mañana, no disponibilidad de vasitos ni envases. "
    "No inventes un número: la cantidad estipulada es la vigente, no una fórmula nueva. "
    "Sí = cumple. "
    "No solo es incumplimiento (afecta extras) si el rendimiento bajo se debe a manejo "
    "incorrecto o a endurecimiento de la crema atribuible al turno de la mañana. "
    "Sin respuesta, evidencia insuficiente, o rendimiento bajo por otra causa "
    "(incluida falta de vasitos o envases, luz, máquina u otro turno) = pendiente; "
    "no atribuyas culpa automática."
)


def _pregunta_cumplimiento(nombre: str, metas: tuple[str, ...] | list[str]) -> str:
    bullets = "\n".join(f"• {m}" for m in metas)
    return (
        f"**Metas de {nombre} hoy:**\n"
        f"{bullets}\n\n"
        f"¿{nombre} cumplió **todas** estas metas hoy?"
    )


def _persona(key: str, nombre: str, metas: tuple[str, ...]) -> dict:
    return {"key": key, "nombre": nombre, "metas": metas, "activa": True}


# Orden de quienes ya estaban: Karina se agrega al final para no reordenar
# al resto. Yuselis no está en esta lista.
TRABAJADORES_PRODUCCION_ACTIVOS = (
    _persona(
        "adrian_l",
        "Adrián L.",
        (
            META_ASISTENCIA_ENVASADO,
            META_TIEMPO_BATIDA,
            META_PROTOCOLO_BATIDORAS,
            META_AGUA_SAL,
            META_ENVASADO,
            META_ALISTAMIENTO_TARDE,
            META_CIERRE,
        ),
    ),
    _persona(
        "angel_l",
        "Ángel L.",
        (
            META_ASISTENCIA_ENVASADO,
            META_ENVASADO,
            META_ALISTAMIENTO_TARDE,
            META_CIERRE,
        ),
    ),
    _persona(
        "jose_m_p",
        "José M. P.",
        (
            META_ASISTENCIA_ENVASADO,
            META_ENVASADO,
            META_ALISTAMIENTO_TARDE,
            META_CIERRE,
        ),
    ),
    _persona(
        "luis_p",
        "Luis P.",
        (
            META_ASISTENCIA_ENVASADO,
            META_TIEMPO_BATIDA,
            META_ENVASADO,
            META_ALISTAMIENTO_TARDE,
            META_CIERRE,
        ),
    ),
    _persona("maria_r", "María R.", METAS_MARIA_Y_KARINA),
    _persona(
        "margaret_m",
        "Margaret M.",
        (
            META_ASISTENCIA,
            META_IMPLEMENTOS,
            META_REPORTE_MATERIA,
        ),
    ),
    _persona("karina_r", "Karina R.", METAS_MARIA_Y_KARINA),
)

# Fuera del formulario nuevo. Se conserva el texto de sus metas para leer
# respuestas históricas; no se usa al armar preguntas ni al calcular extras nuevos.
YUSELIS_HISTORICA = {
    "key": "yuselis_m",
    "nombre": "Yuselis M.",
    "activa": False,
    "metas": (
        META_ASISTENCIA_ENVASADO,
        META_PROTOCOLO_BATIDORAS,
        META_AGUA_SAL,
        META_ENVASADO,
        META_ALISTAMIENTO_TARDE,
        META_CIERRE,
    ),
}

CLAVES_RENDIMIENTO_CREMA = (
    "rendimiento_crema_maria_r",
    "rendimiento_crema_karina_r",
)


def trabajadores_produccion_activos() -> tuple[dict, ...]:
    activos = tuple(TRABAJADORES_PRODUCCION_ACTIVOS)
    claves = [t["key"] for t in activos]
    if YUSELIS_HISTORICA["key"] in claves:
        raise RuntimeError("Yuselis no puede entrar en reportes nuevos")
    if claves.count("karina_r") != 1 or claves.count("maria_r") != 1:
        raise RuntimeError("María y Karina deben aparecer una vez en reportes nuevos")
    return activos


def metas_de(key: str) -> tuple[str, ...]:
    for trabajador in trabajadores_produccion_activos():
        if trabajador["key"] == key:
            return trabajador["metas"]
    if key == YUSELIS_HISTORICA["key"]:
        return YUSELIS_HISTORICA["metas"]
    raise KeyError(key)


def _item_cumplimiento(trabajador: dict) -> dict:
    return {
        "key": trabajador["key"],
        "texto": _pregunta_cumplimiento(trabajador["nombre"], trabajador["metas"]),
        "tipo": "si_no_detalle",
        "reglas": REGLAS_CUMPLIMIENTO_TRABAJADOR,
        "trabajador": trabajador["nombre"],
        "trabajador_key": trabajador["key"],
    }


def _item_rendimiento_crema(trabajador: dict) -> dict:
    nombre = trabajador["nombre"]
    return {
        "key": f"rendimiento_crema_{trabajador['key']}",
        "texto": (
            f"**Rendimiento de crema — {nombre}**\n"
            f"{PREGUNTA_RENDIMIENTO_CREMA}\n\n"
            "Evalúa el rendimiento de la crema que preparó el turno de la mañana "
            f"(cómo se sacó y se manejó), no si había vasitos o envases. "
            f"Responde por **{nombre}**. "
            "No inventes una cifra: compara contra la cantidad de vasitos estipulada vigente. "
            "**Sí** = cumplió. "
            "**No** cuenta como incumplimiento que afecta extras solo cuando el rendimiento "
            "bajo se debe a manejo incorrecto o a que la crema se endureció por el turno "
            "de la mañana. "
            "Si no respondes con claridad, falta evidencia, o el rendimiento bajo tuvo otra causa, "
            "dilo: queda pendiente y no se atribuye culpa."
        ),
        "tipo": TIPO_RENDIMIENTO_CREMA,
        "reglas": REGLAS_RENDIMIENTO_CREMA,
        "trabajador": nombre,
        "trabajador_key": trabajador["key"],
    }


def items_personas_tania() -> list[dict]:
    """Preguntas por persona de un reporte nuevo. Yuselis no entra."""
    por_clave = {t["key"]: t for t in trabajadores_produccion_activos()}
    items: list[dict] = []
    for trabajador in trabajadores_produccion_activos():
        items.append(_item_cumplimiento(trabajador))
        if trabajador["key"] in {"maria_r", "karina_r"}:
            items.append(_item_rendimiento_crema(por_clave[trabajador["key"]]))
    claves = [item["key"] for item in items]
    if YUSELIS_HISTORICA["key"] in claves:
        raise RuntimeError("El flujo nuevo no puede preguntar por Yuselis")
    if claves.count("rendimiento_crema_maria_r") != 1:
        raise RuntimeError("Falta la pregunta de rendimiento de María")
    if claves.count("rendimiento_crema_karina_r") != 1:
        raise RuntimeError("Falta la pregunta de rendimiento de Karina")
    return items


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", (texto or "").strip().lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("¿", " ").replace("¡", " ")
    t = re.sub(r"[!?.,;:()\"']+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _no_aplica(t: str) -> bool:
    return bool(
        re.match(
            r"^(n/?a|no aplica|no vino|no trabajo|no le toco|no correspondio)\b",
            t,
        )
    )


def _evidencia_insuficiente(t: str) -> bool:
    # «no sé» no debe tragarse «No, se endureció» (la coma ya se volvió espacio).
    if t == "no se" or re.search(r"(^| )no se si\b|(^| )no se$", t):
        return True
    return bool(
        re.search(
            r"no estoy segur|no recuerdo|sin evidencia|no hay evidencia|"
            r"falta evidencia|evidencia insuficiente|no se sabe|por confirmar|"
            r"(^| )pendiente\b|no tengo (el )?dato|no me consta|no esta claro|"
            r"no hay forma de saber",
            t,
        )
    )


def _menciona_falla_manejo(t: str) -> bool:
    return bool(
        re.search(
            r"manejo incorrecto|mal manejo|manej(o|aron) mal|"
            r"sac(o|aron) (la crema )?mal|"
            r"dej(o|aron) endurecer|se dejo endurecer|"
            r"se endureci|endurecimiento|"
            r"se puso dura|quedo dura|crema dura|estaba dura",
            t,
        )
    )


def _explicita_otro_turno(t: str) -> bool:
    return bool(
        re.search(
            r"turno de la tarde|en la tarde|por la tarde|turno de la noche|"
            r"no fue (el |la |del )?turno de la manana|no fue la manana|"
            r"no es culpa de la manana|no atribu",
            t,
        )
    )


def _otra_causa(t: str) -> bool:
    """Causas que no son el manejo de la crema del turno de mañana."""
    return bool(
        re.search(
            r"faltaron (los )?vasitos|no habian vasitos|no habia vasitos|sin vasitos|"
            r"se acabaron los vasitos|faltaron envases|no habian envases|sin envases|"
            r"disponibilidad de envases|inventario de (vasitos|envases)|"
            r"no habian (los )?envases|"
            r"se fue la luz|corte de luz|corte de energia|sin luz|"
            r"se dano la batidora|batidora danada|se dano la maquina|maquina danada|"
            r"faltaron insumos|falta de insumo|no habia mezcla|no hubo produccion|"
            r"proveedor|se dano la nevera|congelador",
            t,
        )
    )


def _falla_atribuible_manana(t: str) -> bool:
    if not _menciona_falla_manejo(t):
        return False
    # Otra causa o otro turno impiden la culpa automática.
    if _explicita_otro_turno(t) or _otra_causa(t):
        return False
    return True


def _afirma_rendimiento(t: str) -> bool:
    if re.match(r"^si no\b", t):
        return False
    if re.search(
        r"\bno rindio\b|\bno alcanzo\b|\bno salio\b|\bsalieron menos\b|\brindio menos\b",
        t,
    ):
        return False
    if re.match(r"^(si|sip|yes|correcto|claro|afirmativo)\b", t):
        return True
    return bool(
        re.search(
            r"\b(rindio lo estipulado|rindio la cantidad|alcanzo la cantidad|"
            r"salio la cantidad|salio lo estipulado)\b",
            t,
        )
    )


def _niega_rendimiento(t: str) -> bool:
    if t == "no se" or re.match(r"^no se si\b", t):
        return False
    if re.match(
        r"^no (estoy|hay|recuerdo|aplica|vino|trabajo|le toco|correspondio)\b",
        t,
    ):
        return False
    if re.match(r"^no\b", t):
        return True
    return bool(
        re.search(
            r"\bno rindio\b|\bno alcanzo\b|\bno salio la cantidad\b|"
            r"\bsalieron menos\b|\brindio menos\b|\bno dio la cantidad\b|"
            r"\bno completo la cantidad\b",
            t,
        )
    )


def clasificar_rendimiento_crema(texto: str | None) -> str:
    """Polaridad de la meta de rendimiento. No inventa la cantidad estipulada.

    cumple: la crema rindió la cantidad estipulada vigente.
    incumple: no rindió por manejo incorrecto o endurecimiento atribuible
    al turno de la mañana. Ese resultado es el que afecta extras.
    pendiente: sin respuesta, evidencia insuficiente, o rendimiento bajo
    por otra causa. No sanciona solo.
    """
    if texto is None or not str(texto).strip():
        return "pendiente"
    t = _norm(str(texto))
    if not t or _no_aplica(t) or _evidencia_insuficiente(t):
        return "pendiente"
    afirma = _afirma_rendimiento(t)
    niega = _niega_rendimiento(t)
    falla = _falla_atribuible_manana(t)
    if afirma and not niega:
        return "cumple"
    if niega and falla:
        return "incumple"
    return "pendiente"


def afecta_extras(polaridad: str) -> bool:
    """Solo el incumplimiento confirmado de esta meta descuenta extras.

    No modifica montos ya aprobados: el flag es para reportes nuevos.
    """
    return polaridad == "incumple"


def exportar_evaluacion(answers: dict | None) -> dict:
    """Copia las respuestas y anota la polaridad solo si la pregunta nueva está.

    No elimina claves (incluida Yuselis), no reescribe textos y no inventa
    un incumplimiento cuando el reporte histórico no trae la pregunta.
    No calcula ni altera pagos.
    """
    origen = dict(answers or {})
    evaluacion: dict[str, dict] = {}
    for clave, texto in origen.items():
        if clave not in CLAVES_RENDIMIENTO_CREMA:
            continue
        polaridad = clasificar_rendimiento_crema(texto)
        persona = clave.removeprefix("rendimiento_crema_")
        evaluacion[clave] = {
            "persona": persona,
            "polaridad": polaridad,
            "afecta_extras": afecta_extras(polaridad),
        }
    return {
        "answers": origen,
        "evaluacion_rendimiento_crema": evaluacion,
    }
