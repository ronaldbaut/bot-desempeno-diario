import discord
from discord.ext import tasks, commands
from datetime import time, datetime, date
from zoneinfo import ZoneInfo
import os
import traceback
from openai import OpenAI
import json
import re
 
print(">>> Iniciando bot de desempeño diario...")
 
# ==================== CONFIGURACIÓN ====================
TOKEN = os.getenv("TOKEN")
CHANNEL_ID_STR = os.getenv("CHANNEL_ID")
 
if not TOKEN:
    raise RuntimeError("❌ ERROR: Falta la variable de entorno TOKEN en Railway")
if not CHANNEL_ID_STR:
    raise RuntimeError("❌ ERROR: Falta la variable de entorno CHANNEL_ID en Railway")
 
CHANNEL_ID = int(CHANNEL_ID_STR)
TZ = ZoneInfo("America/Caracas")
 
intents = discord.Intents.default()
intents.message_content = True
 
bot = commands.Bot(command_prefix="!", intents=intents)
 
client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)
 
# reports[user_id] = { team, date, answers, buffer, active }
reports = {}
 
 
class ReporteCancelado(Exception):
    pass
 
 
# ==================== PREGUNTAS TANIA ====================
# Cada item: key, texto, reglas para Grok, tipo
TANIA_FLOW = [
    {
        "key": "alistamiento",
        "texto": (
            "¿Las personas que alistaron los pedidos ayer en la noche para llevarlos "
            "hoy en la mañana, lo hicieron correctamente sin errores importantes?"
        ),
        "tipo": "si_no_detalle",
        "reglas": "Sí/No válido. Si hubo errores, puede explicar. 'Si' solo es válido.",
    },
    {
        "key": "produccion",
        "texto": "¿Hoy hubo producción?",
        "tipo": "si_no",
        "reglas": "Sí/No / 'hubo' / 'no hubo' son válidos. Es la pregunta de bifurcación.",
    },
    # --- Solo si hubo producción ---
    {
        "key": "licuadas",
        "texto": (
            "¿María R. logró las batidas de hoy sin errores en la fórmula "
            "ni en el alistamiento de materiales?"
        ),
        "tipo": "si_no_detalle",
        "solo_si_produccion": True,
        "reglas": "Sí/No válido. Si hubo errores, detalle es bienvenido pero no obligatorio si dice no.",
    },
    {
        "key": "protocolo_batidoras",
        "texto": "¿Se cumplió correctamente el protocolo de encendido y apagado de las batidoras hoy?",
        "tipo": "si_no_detalle",
        "solo_si_produccion": True,
        "reglas": "Sí/No válido. Puede matizar (ej. 'casi, faltó video de la 3').",
    },
    {
        "key": "cambios_agua",
        "texto": "¿Fue necesario un cambio de agua sal hoy?",
        "tipo": "si_no_detalle",
        "solo_si_produccion": True,
        "reglas": "Sí/No válido.",
    },
    {
        "key": "tiempo_produccion",
        "texto": "¿Se mantuvo el promedio de tiempo por batida en 30 minutos o menos hoy?",
        "tipo": "si_no_detalle",
        "solo_si_produccion": True,
        "reglas": "Sí/No válido. Puede dar tiempos reales si quiere.",
    },
    {
        "key": "implementos",
        "texto": (
            "¿Margaret M. dejó separados, contados y organizados todos los implementos "
            "para la jornada de hoy?"
        ),
        "tipo": "si_no_detalle",
        "solo_si_produccion": True,
        "reglas": "Sí/No válido.",
    },
    {
        "key": "envasado",
        "texto": "¿Se cumplieron las metas de tiempo de envasado por vasito hoy?",
        "tipo": "si_no_detalle",
        "solo_si_produccion": True,
        "reglas": "Sí/No válido. 'No, se demoraron en trisabor' ES válido.",
    },
    {
        "key": "asistencia",
        "texto": "¿Todo el personal llegó a tiempo, registró correctamente su huella y no faltó nadie hoy?",
        "tipo": "si_no_detalle",
        "solo_si_produccion": True,
        "reglas": (
            "Sí es válido. Si alguien llegó tarde o falló huella, la respuesta con nombres ES válida "
            "(no exijas 'sí' puro). 'Yuselis llegó tarde, Luis marcó huella y no salió' ES válido."
        ),
    },
    # --- Siempre ---
    {
        "key": "reporte_materia",
        "texto": (
            "¿Margaret M. envió correctamente el reporte diario con inventario inicial/final, "
            "consumo de adicionales y lista de insumos próximos a agotarse hoy?"
        ),
        "tipo": "si_no_detalle",
        "reglas": (
            "Sí/No válido. Si no envió o envió a medias, la explicación ES válida "
            "(ej. 'No, mandó foto de adicionales pero no el reporte porque no había luz')."
        ),
    },
    {
        "key": "protocolo_cierre",
        "texto": (
            "¿Se cumplió el 100% del protocolo diario de cierre y se envió "
            "toda la información solicitada hoy?"
        ),
        "tipo": "si_no_detalle",
        "reglas": (
            "Sí/No válido. Matiz tipo 'sí pero se equivocaron con gasolina planta roja' ES válido."
        ),
    },
    {
        "key": "incidencia",
        "texto": "¿Hubo alguna incidencia, problema o área de mejora hoy?",
        "tipo": "abierta",
        "reglas": (
            "'No' / 'Ninguna' ES válido. Si hay incidencia, cualquier descripción clara ES válida. "
            "NO exijas formato especial."
        ),
    },
    {
        "key": "notas",
        "texto": "¿Comentarios finales del día?",
        "tipo": "abierta",
        "reglas": "'No' / 'Ninguno' / 'Nada' ES válido. Comentario libre también.",
    },
]
 
# ==================== PREGUNTAS RONALD ====================
RONALD_FLOW = [
    {
        "key": "q1",
        "texto": (
            "¿Se verificó hoy el inventario de los productos de mayor consumo y se dejó registro "
            "del conteo? ¿El registro cuadra? Si no cuadra, ¿se intentó aclarar con la jefe de producción?"
        ),
        "tipo": "compuesta",
        "reglas": (
            "Válido si cubre: si se verificó / si cuadra / qué se hizo si no cuadra. "
            "'Sí, cuadra' es válido. 'Sí, no cuadró, se habló con Tania' es válido. "
            "No exijas copiar las 3 subpreguntas al pie de la letra si la idea está."
        ),
    },
    {
        "key": "q2",
        "texto": "¿Se registraron correctamente todas las compras y asientos?",
        "tipo": "si_no_detalle",
        "reglas": "Sí/No válido. Puede detallar pendientes.",
    },
    {
        "key": "q3",
        "texto": "¿Los contratos están ordenados, completos y accesibles?",
        "tipo": "si_no_detalle",
        "reglas": "Sí/No válido.",
    },
    {
        "key": "q4",
        "texto": (
            "¿Se envió el reporte semanal con la cartelera fiscal, la situación de los contratos "
            "pendientes (no emitidos, no firmados o no guardados) y el listado de contratos vigentes "
            "de los trabajadores?"
        ),
        "tipo": "si_no_detalle",
        "reglas": (
            "Sí/No válido. Si no toca hoy (no es día de reporte semanal), "
            "'No aplica hoy / no es día de reporte semanal' ES válido."
        ),
    },
    {
        "key": "q5",
        "texto": (
            "¿Se llamó a los clientes visitados por José hace 7 días para ofrecerles el 15% "
            "de descuento o preguntar por qué no compraron?"
        ),
        "tipo": "si_no_detalle",
        "reglas": "Sí/No válido. Puede decir cuántos llamó o si no había a quien llamar.",
    },
    {
        "key": "q6",
        "texto": "¿Se enviaron al equipo de marketing las fotos solicitadas para las campañas en redes sociales?",
        "tipo": "si_no_detalle",
        "reglas": "Sí/No / no había solicitud hoy ES válido.",
    },
    {
        "key": "q7",
        "texto": (
            "¿Se enviaron las alertas a gerencia sobre: pedidos bajo el mínimo, viajes solo para cobrar, "
            "clientes fuera de zona, clientes sin pedido o con deudas vencidas, y quejas de los clientes?"
        ),
        "tipo": "si_no_detalle",
        "reglas": (
            "Sí/No válido. 'No hubo alertas que reportar' ES válido. "
            "No exijas listar cada tipo de alerta si dice que no aplicó o que sí se enviaron."
        ),
    },
    {
        "key": "q8",
        "texto": "¿Se respondieron todos los mensajes de redes sociales y WhatsApp antes de las 5:55 pm?",
        "tipo": "si_no_detalle",
        "reglas": "Sí/No válido.",
    },
    {
        "key": "q9",
        "texto": "¿Se atendió con buena actitud y amabilidad a todos los clientes (incluyendo carritos heladeros)?",
        "tipo": "si_no_detalle",
        "reglas": "Sí/No válido.",
    },
    {
        "key": "q10",
        "texto": (
            "(Solo si es fin de semana o día festivo) ¿Se revisó al entrar y al salir que todos "
            "los congeladores estuvieran encendidos y funcionando correctamente?"
        ),
        "tipo": "si_no_detalle",
        "solo_finde_o_festivo": True,
        "reglas": "Sí/No válido. Si el bot no debió preguntar, 'No aplica' también válido.",
    },
    {
        "key": "q11",
        "texto": "¿Cuántos prospectos se visitaron hoy?",
        "tipo": "numero",
        "reglas": (
            "Válido: un número (0, 3, 'ninguno'=0, 'dos'). "
            "Inválido: solo 'sí' sin cantidad."
        ),
    },
    {
        "key": "q12",
        "texto": "¿El recorrido del vehículo coincide con el recorrido reportado?",
        "tipo": "si_no_detalle",
        "reglas": "Sí/No válido. Si no hubo recorrido, 'No hubo recorrido / N/A' ES válido.",
    },
    {
        "key": "incidencia",
        "texto": "¿Hubo alguna incidencia, problema o área de mejora hoy?",
        "tipo": "abierta",
        "reglas": "'No' / 'Ninguna' ES válido. Descripción libre también.",
    },
    {
        "key": "notas",
        "texto": "¿Comentarios finales del día?",
        "tipo": "abierta",
        "reglas": "'No' / 'Ninguno' ES válido.",
    },
]
 
 
# ==================== HELPERS ====================
def _vacio_o_basura(texto: str) -> bool:
    t = (texto or "").strip()
    if not t:
        return True
    return t.lower() in {".", "..", "...", "ok", "vale", "listo", "k", "ya", "-", "—"}
 
 
def _parece_cancelar(content_lower: str) -> bool:
    patrones = [
        r"^cancelar(\s+reporte)?$",
        r"^cancel(\s+report)?$",
        r"^cancela(r)?$",
        r"^canelar(\s+reporte)?$",
        r"^detener(\s+reporte)?$",
        r"^parar$",
        r"^abortar$",
        r"^reporte\s+cancelado$",
    ]
    return any(re.match(p, content_lower) for p in patrones)
 
 
def _es_respuesta_si(texto: str) -> bool | None:
    """True=sí, False=no, None=no claro."""
    t = (texto or "").strip().lower()
    t = re.sub(r"[¡!?.]", "", t).strip()
    if not t:
        return None
    # Respuestas cortas puras
    if t in {"si", "sí", "yes", "s", "1", "afirmativo", "correcto", "claro"}:
        return True
    if t in {"no", "n", "0", "nop", "nel", "negativo", "ninguno", "ninguna", "nada"}:
        return False
    # Frases comunes
    if re.match(r"^(si|sí)\b", t) and not re.search(r"\bno\b", t[:12]):
        # "si, pero..." cuenta como sí matizado
        if re.match(r"^(si|sí)\s*,?\s*(pero|aunque|salvo|excepto)", t):
            return True
        if len(t) <= 40:
            return True
    if re.match(r"^no\b", t):
        return False
    if re.search(r"\bno\s+hubo\b|\bno\s+hubo\s+producci", t):
        return False
    if re.search(r"\bhubo\s+producci|\bs[ií]\s+hubo\b", t):
        return True
    return None
 
 
def _es_finde_o_festivo(d: date | None = None) -> bool:
    """Fin de semana. (Festivos locales: ampliar lista si quieres.)"""
    d = d or datetime.now(TZ).date()
    if d.weekday() >= 5:  # 5=sáb, 6=dom
        return True
    # Festivos VE aproximados / fijos frecuentes — editar según necesiten
    festivos_fijos = {
        (1, 1),
        (4, 19),
        (5, 1),
        (6, 24),
        (7, 5),
        (7, 24),
        (10, 12),
        (12, 24),
        (12, 25),
        (12, 31),
    }
    return (d.month, d.day) in festivos_fijos
 
 
# ==================== VISTA DE BOTONES ====================
class DailyReportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
 
    @discord.ui.button(
        label="Iniciar Reporte Tania",
        style=discord.ButtonStyle.primary,
        custom_id="daily_tania_v2",
    )
    async def tania_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_report(interaction, "tania")
 
    @discord.ui.button(
        label="Iniciar Reporte Ronald",
        style=discord.ButtonStyle.primary,
        custom_id="daily_ronald_v2",
    )
    async def ronald_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_report(interaction, "ronald")
 
 
# ==================== GROK ====================
async def consultar_grok(
    pregunta_item: dict,
    respuesta_nueva: str,
    buffer: str,
) -> dict:
    system_prompt = """
Eres validador de un reporte diario de desempeño (fábrica de helados / oficina).
Responde ÚNICAMENTE JSON:
{
  "respuesta_valida": true o false,
  "mensaje": null o "texto corto pidiendo SOLO lo que falta",
  "interpretacion_si_no": "si" | "no" | "na" | null
}
 
Principios:
1. Sé RAZONABLE. Muchas preguntas son de sí/no: "Si", "No", "Sí", "si" SON válidas.
2. "No" / "Ninguna" / "Nada" en incidencias o comentarios finales ES válido.
3. Respuestas matizadas ("Sí, pero Yuselis llegó tarde") SON válidas.
4. NO exijas copiar la pregunta ni un ensayo. Un dato claro basta.
5. Evalúa BUFFER + respuesta nueva juntos (no pidas de nuevo lo ya dicho).
6. Español informal y typos OK.
7. Nunca uses solo "Responde completo lo que se te preguntó" sin decir qué falta.
8. Punto "." o vacío → inválido.
9. interpretacion_si_no: rellena "si"/"no" cuando la pregunta es de ese tipo y se entiende; "na" si no aplica; null si no es sí/no.
 
Errores a evitar:
- Rechazar un "Si" o "No" claro en preguntas de cumplimiento.
- Rechazar "No" en comentarios finales.
- Pedir detalles obligatorios cuando la persona ya contestó no/sí con claridad.
"""
 
    user_content = f"""
Pregunta:
{pregunta_item["texto"]}
 
Tipo: {pregunta_item.get("tipo")}
Reglas de esta pregunta:
{pregunta_item.get("reglas", "")}
 
BUFFER (intentos previos misma pregunta):
\"\"\"{buffer or "(vacío)"}\"\"\"
 
Respuesta NUEVA:
\"\"\"{respuesta_nueva}\"\"\"
"""
 
    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return {
            "respuesta_valida": bool(data.get("respuesta_valida", False)),
            "mensaje": data.get("mensaje"),
            "interpretacion_si_no": data.get("interpretacion_si_no"),
        }
    except Exception as e:
        print(f"Error al consultar Grok: {e}")
        traceback.print_exc()
        if _vacio_o_basura(respuesta_nueva):
            return {
                "respuesta_valida": False,
                "mensaje": "Escribe la respuesta (no uses solo un punto).",
                "interpretacion_si_no": None,
            }
        # Fail-open: texto real
        sn = _es_respuesta_si(respuesta_nueva)
        return {
            "respuesta_valida": True,
            "mensaje": None,
            "interpretacion_si_no": "si" if sn is True else ("no" if sn is False else None),
        }
 
 
# ==================== OBTENER RESPUESTA ====================
async def obtener_respuesta(channel, user, pregunta_item: dict) -> tuple[str, dict]:
    """
    Espera mensajes del usuario hasta validar.
    Devuelve (texto_final, decision_grok).
    """
    buffer = ""
    pregunta_txt = pregunta_item["texto"]
 
    while True:
        msg = await bot.wait_for(
            "message",
            check=lambda m: m.author.id == user.id and m.channel.id == channel.id,
        )
        contenido = (msg.content or "").strip()
        contenido_lower = contenido.lower()
 
        if _parece_cancelar(contenido_lower):
            await channel.send(
                "✅ **Reporte cancelado.**\n"
                "Puedes iniciar uno nuevo con los botones o `/reporte-tania` / `/reporte-ronald`."
            )
            if user.id in reports:
                del reports[user.id]
            raise ReporteCancelado()
 
        if _vacio_o_basura(contenido) and not msg.attachments:
            await channel.send(
                "Escribe la respuesta con datos (no uses solo un punto). "
                "En preguntas de sí/no basta con **Sí** o **No**."
            )
            continue
 
        # Atajo local para sí/no claros (ahorra tokens y evita rechazos absurdos)
        tipo = pregunta_item.get("tipo")
        sn_local = _es_respuesta_si(contenido)
        if tipo in {"si_no", "si_no_detalle"} and sn_local is not None and len(contenido) <= 80:
            # Si es matiz largo con "si pero..." de más de 80 chars, deja que Grok mire
            try:
                await msg.add_reaction("✅")
            except Exception:
                pass
            decision = {
                "respuesta_valida": True,
                "mensaje": None,
                "interpretacion_si_no": "si" if sn_local else "no",
            }
            final = (buffer + "\n" + contenido).strip() if buffer else contenido
            return final, decision
 
        if tipo == "abierta" and sn_local is False:
            # "No" / "Ninguna" en incidencia o notas
            try:
                await msg.add_reaction("✅")
            except Exception:
                pass
            return contenido, {
                "respuesta_valida": True,
                "mensaje": None,
                "interpretacion_si_no": "no",
            }
 
        decision = await consultar_grok(pregunta_item, contenido, buffer)
 
        if not decision.get("respuesta_valida", False):
            buffer = (buffer + "\n" + contenido).strip() if buffer else contenido
            mensaje = decision.get("mensaje") or "Falta un dato. Completa solo lo que falta."
            if mensaje.strip().lower() in {
                "responde completo lo que se te preguntó.",
                "responde completo lo que se te preguntó",
                "tu respuesta está incompleta. responde correctamente.",
            }:
                mensaje = "Me falta un dato concreto de la pregunta. Complétalo en un mensaje más."
            await channel.send(mensaje)
            continue
 
        try:
            await msg.add_reaction("✅")
        except Exception:
            pass
 
        final = (buffer + "\n" + contenido).strip() if buffer else contenido
        return final, decision
 
 
# ==================== FLUJOS ====================
async def ask_flow(channel, user, flow: list, hubo_produccion: bool | None = None):
    data = reports[user.id]
    num = 0
 
    for item in flow:
        if item.get("solo_si_produccion") and not hubo_produccion:
            data["answers"][item["key"]] = "N/A — no hubo producción"
            continue
 
        if item.get("solo_finde_o_festivo") and not _es_finde_o_festivo():
            data["answers"][item["key"]] = "N/A — no es fin de semana ni festivo"
            continue
 
        num += 1
        etiqueta = item["key"]
        if etiqueta == "incidencia":
            await channel.send(f"**Incidencia:** {item['texto']}")
        elif etiqueta == "notas":
            await channel.send(f"**Notas adicionales:** {item['texto']}")
        else:
            await channel.send(f"**{num}.** {item['texto']}")
 
        texto, decision = await obtener_respuesta(channel, user, item)
        data["answers"][item["key"]] = texto
 
        # Bifurcación producción (pregunta 2 de Tania)
        if item["key"] == "produccion":
            interp = decision.get("interpretacion_si_no")
            if interp == "si":
                hubo_produccion = True
            elif interp == "no":
                hubo_produccion = False
            else:
                sn = _es_respuesta_si(texto)
                hubo_produccion = True if sn is True else (False if sn is False else True)
                # Si no se entiende, asumimos que SÍ hubo para no saltar preguntas de ops
            data["hubo_produccion"] = hubo_produccion
            if not hubo_produccion:
                await channel.send(
                    "_No hubo producción: salto las preguntas de batidas, batidoras, "
                    "envasado e implementos de producción._"
                )
 
    await channel.send(f"✅ **Reporte {data['team'].upper()} completado. ¡Gracias!**")
    print(
        f"[DESEMPEÑO OK] team={data['team']} user={user.id} "
        f"answers={json.dumps(data['answers'], ensure_ascii=False)}"
    )
    if user.id in reports:
        del reports[user.id]
 
 
async def ask_tania_questions(channel, user):
    await ask_flow(channel, user, TANIA_FLOW, hubo_produccion=None)
 
 
async def ask_ronald_questions(channel, user):
    await ask_flow(channel, user, RONALD_FLOW, hubo_produccion=None)
 
 
# ==================== TAREA DIARIA ====================
@tasks.loop(time=time(hour=20, minute=0, tzinfo=TZ))
async def daily_report():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("⚠️ Canal no encontrado en daily_report")
        return
    view = DailyReportView()
    await channel.send(
        "🕒 **Hora del Reporte Diario (20:00)**\n¿Comenzamos?",
        view=view,
    )
    print("✅ Mensaje de reporte diario enviado con botones")
 
 
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    # Vista persistente para que los botones sigan vivos tras reinicios
    bot.add_view(DailyReportView())
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash commands sincronizados")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")
        traceback.print_exc()
 
    if not daily_report.is_running():
        daily_report.start()
    print("✅ Tarea diaria iniciada (20:00 America/Caracas)")
 
 
async def start_report(interaction: discord.Interaction, team: str):
    user = interaction.user
 
    if user.id in reports:
        try:
            await interaction.response.send_message(
                "Ya tienes un reporte en curso. Escribe **cancelar reporte** para detenerlo "
                "o termínalo primero.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Ya tienes un reporte en curso. Escribe **cancelar reporte** o termínalo.",
                ephemeral=True,
            )
        return
 
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.InteractionResponded:
        pass
 
    reports[user.id] = {
        "team": team,
        "date": datetime.now(TZ).strftime("%Y-%m-%d"),
        "answers": {},
        "active": True,
    }
 
    try:
        await interaction.followup.send(
            f"📋 **Reporte {team.upper()} iniciado** por {user.mention}\n\n"
            f"_Escribe **cancelar reporte** en cualquier momento para detenerlo._\n"
            f"_En preguntas de sí/no basta con **Sí** o **No** (puedes matizar si quieres)._",
        )
    except Exception:
        # Si el followup falla, igual arrancamos en el canal
        await interaction.channel.send(
            f"📋 **Reporte {team.upper()} iniciado** por {user.mention}\n\n"
            f"_Escribe **cancelar reporte** para detenerlo._"
        )
 
    channel = interaction.channel
    try:
        if team == "tania":
            await ask_tania_questions(channel, user)
        else:
            await ask_ronald_questions(channel, user)
    except ReporteCancelado:
        return
    except Exception as e:
        print(f"❌ Error en reporte {team}: {e}")
        traceback.print_exc()
        if user.id in reports:
            del reports[user.id]
        try:
            await channel.send(
                "⚠️ Hubo un error en el reporte y se detuvo. "
                "Puedes iniciarlo de nuevo con el botón o el slash command."
            )
        except Exception:
            pass
 
 
# ==================== SLASH ====================
@bot.tree.command(name="reporte-tania", description="Inicia reporte manual Tania")
async def reporte_tania(interaction: discord.Interaction):
    await start_report(interaction, "tania")
 
 
@bot.tree.command(name="reporte-ronald", description="Inicia reporte manual Ronald")
async def reporte_ronald(interaction: discord.Interaction):
    await start_report(interaction, "ronald")
 
 
# ==================== INICIO ====================
bot.run(TOKEN)
