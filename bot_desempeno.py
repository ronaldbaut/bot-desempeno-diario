import discord
from discord.ext import tasks, commands
from discord.ui import Button, View
from datetime import time
from zoneinfo import ZoneInfo
from datetime import datetime
import os
import traceback
from openai import OpenAI
import json

print(">>> Iniciando bot de desempeño diario...")

# ==================== CONFIGURACIÓN SEGURA ====================
TOKEN = os.getenv("TOKEN")
CHANNEL_ID_STR = os.getenv("CHANNEL_ID")

if not TOKEN:
    raise RuntimeError("❌ ERROR: Falta la variable de entorno TOKEN en Railway")
if not CHANNEL_ID_STR:
    raise RuntimeError("❌ ERROR: Falta la variable de entorno CHANNEL_ID en Railway")

CHANNEL_ID = int(CHANNEL_ID_STR)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Cliente de xAI (Grok)
client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)

reports = {}

CANCEL_PHRASES = {"cancelar reporte", "cancelar", "cancel", "detener", "parar", "abortar", "cancelarreporte", "canelar"}

class ReporteCancelado(Exception):
    pass

# ==================== PREGUNTAS TANIA ====================
TANIA_QUESTIONS = {
    "alistamiento": "¿Las personas que alistaron los pedidos ayer en la noche para llevarlos hoy en la mañana, lo hicieron correctamente sin errores importantes?",
    "produccion": "¿Hoy hubo producción?",
    "licuadas": "¿María R. logró las batidas de hoy sin errores en la fórmula ni en el alistamiento de materiales?",
    "protocolo_batidoras": "¿Se cumplió correctamente el protocolo de encendido y apagado de las batidoras hoy?",
    "cambios_agua": "¿Fue necesario un cambio de agua sal hoy?",
    "tiempo_produccion": "¿Se mantuvo el promedio de tiempo por batida en 30 minutos o menos hoy?",
    "implementos": "¿Margaret M. dejó separados, contados y organizados todos los implementos para la jornada de hoy?",
    "envasado": "¿Se cumplieron las metas de tiempo de envasado por vasito hoy?",
    "asistencia": "¿Todo el personal llegó a tiempo, registró correctamente su huella y no faltó nadie hoy?",
    "reporte_materia": "¿Margaret M. envió correctamente el reporte diario con inventario inicial/final, consumo de adicionales y lista de insumos próximos a agotarse hoy?",
    "protocolo_cierre": "¿Se cumplió el 100% del protocolo diario de cierre y se envió toda la información solicitada hoy?"
}

# ==================== PREGUNTAS RONALD (ACTUALIZADAS) ====================
RONALD_QUESTIONS = [
    "1. ¿Se verificó hoy el inventario de los productos de mayor consumo y se dejó registro del conteo? ¿El registro cuadra? Si no cuadra, ¿se intentó aclarar con la jefe de producción?",
    "2. ¿Se registraron correctamente todas las compras y asientos?",
    "3. ¿Los contratos están ordenados, completos y accesibles?",
    "4. ¿Se envió el reporte semanal con la cartelera fiscal, la situación de los contratos pendientes (no emitidos, no firmados o no guardados) y el listado de contratos vigentes de los trabajadores?",
    "5. ¿Se llamó a los clientes visitados por José hace 7 días para ofrecerles el 15% de descuento o preguntar por qué no compraron?",
    "6. ¿Se enviaron al equipo de marketing las fotos solicitadas para las campañas en redes sociales?",
    "7. ¿Se enviaron las alertas a gerencia sobre: pedidos bajo el mínimo, viajes solo para cobrar, clientes fuera de zona, clientes sin pedido o con deudas vencidas, y quejas de los clientes?",
    "8. ¿Se respondieron todos los mensajes de redes sociales y WhatsApp antes de las 5:55 pm?",
    "9. ¿Se atendió con buena actitud y amabilidad a todos los clientes (incluyendo carritos heladeros)?",
    "10. (Solo si es fin de semana o día festivo) ¿Se revisó al entrar y al salir que todos los congeladores estuvieran encendidos y funcionando correctamente?",
    "11. ¿Cuántos prospectos se visitaron hoy?",
    "12. ¿El recorrido del vehículo coincide con el recorrido reportado?"
]

# ==================== VISTA DE BOTONES ====================
class DailyReportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Iniciar Reporte Tania", style=discord.ButtonStyle.primary, custom_id="daily_tania_v1")
    async def tania_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_report(interaction, "tania")

    @discord.ui.button(label="Iniciar Reporte Ronald", style=discord.ButtonStyle.primary, custom_id="daily_ronald_v1")
    async def ronald_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_report(interaction, "ronald")

# ==================== FUNCIÓN QUE CONSULTA A GROK ====================
async def consultar_grok(pregunta: str, respuesta_usuario: str) -> dict:
    system_prompt = """
Eres un supervisor estricto de reportes diarios de desempeño en una fábrica de helados.

Responde ÚNICAMENTE con un JSON válido:

{
  "respuesta_valida": true o false,
  "mensaje": null o "texto"
}

Reglas:
- Si la respuesta es muy corta, vacía, irrelevante o no responde claramente la pregunta → respuesta_valida = false
- Cuando sea inválida, el campo "mensaje" debe decir de forma clara, simple y contundente qué falta.
- Sé directo y corto.
- Si la respuesta es válida, pon "mensaje": null
"""

    user_content = f"""
Pregunta actual:
{pregunta}

Respuesta del trabajador:
"{respuesta_usuario}"
"""

    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error al consultar Grok: {e}")
        return {
            "respuesta_valida": True,
            "mensaje": None
        }

# ==================== HELPER PARA ESPERAR RESPUESTA ====================
async def obtener_respuesta(channel, user, pregunta: str):
    while True:
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
        contenido = msg.content.strip().lower()

        if any(phrase in contenido for phrase in CANCEL_PHRASES) or "cancelar" in contenido:
            await channel.send("✅ **Reporte cancelado.**\nPuedes iniciar uno nuevo cuando quieras usando los botones o los comandos `/reporte-tania` y `/reporte-ronald`.")
            if user.id in reports:
                del reports[user.id]
            raise ReporteCancelado()

        try:
            await msg.add_reaction("✅")
        except:
            pass

        decision = await consultar_grok(pregunta, msg.content)

        if decision.get("respuesta_valida", True):
            return msg
        else:
            mensaje = decision.get("mensaje") or "Tu respuesta está incompleta. Responde correctamente."
            await channel.send(mensaje)

# ==================== TAREA DIARIA ====================
@tasks.loop(time=time(hour=20, minute=0, tzinfo=ZoneInfo("America/Caracas")))
async def daily_report():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("⚠️ Canal no encontrado en daily_report")
        return
    view = DailyReportView()
    await channel.send("🕒 **Hora del Reporte Diario (20:00)**\n¿Comenzamos?", view=view)
    print("✅ Mensaje de reporte diario enviado con botones")

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash commands sincronizados correctamente")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")
        traceback.print_exc()
    daily_report.start()
    print("✅ Tarea diaria iniciada (20:00 America/Caracas - Venezuela)")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    try:
        custom_id = interaction.data.get("custom_id")
        if custom_id in ("daily_tania_v1", "tania"):
            await start_report(interaction, "tania")
        elif custom_id in ("daily_ronald_v1", "ronald"):
            await start_report(interaction, "ronald")
    except Exception as e:
        print(f"❌ Error en on_interaction: {e}")
        traceback.print_exc()

async def start_report(interaction, team):
    await interaction.response.defer()
    user = interaction.user
    report_data = {"team": team, "date": datetime.now().strftime("%Y-%m-%d"), "answers": {}}
    reports[user.id] = report_data

    try:
        await interaction.followup.send(f"📋 **Reporte {team.upper()} iniciado** por {user.mention}\n\n_Escribe **cancelar reporte** en cualquier momento para detenerlo._")
    except:
        pass

    channel = interaction.channel

    try:
        if team == "tania":
            await ask_tania_questions(channel, user)
        else:
            await ask_ronald_questions(channel, user)
    except ReporteCancelado:
        return

async def ask_tania_questions(channel, user):
    data = reports[user.id]

    pregunta = TANIA_QUESTIONS['alistamiento']
    await channel.send(f"**1.** {pregunta}")
    msg = await obtener_respuesta(channel, user, pregunta)
    data["answers"]["alistamiento"] = msg.content

    pregunta = TANIA_QUESTIONS['produccion']
    await channel.send(f"**2.** {pregunta}")
    msg = await obtener_respuesta(channel, user, pregunta)
    hubo_produccion = msg.content.lower() in ["sí", "si", "yes", "1"]

    if hubo_produccion:
        keys = ["licuadas", "protocolo_batidoras", "cambios_agua", "tiempo_produccion", "implementos", "envasado", "asistencia"]
        for i, key in enumerate(keys, 3):
            pregunta = TANIA_QUESTIONS[key]
            await channel.send(f"**{i}.** {pregunta}")
            msg = await obtener_respuesta(channel, user, pregunta)
            data["answers"][key] = msg.content

    pregunta = TANIA_QUESTIONS['reporte_materia']
    await channel.send(f"**10.** {pregunta}")
    msg = await obtener_respuesta(channel, user, pregunta)
    data["answers"]["reporte_materia"] = msg.content

    pregunta = TANIA_QUESTIONS['protocolo_cierre']
    await channel.send(f"**11.** {pregunta}")
    msg = await obtener_respuesta(channel, user, pregunta)
    data["answers"]["protocolo_cierre"] = msg.content

    await ask_final_questions(channel, user, data)

async def ask_ronald_questions(channel, user):
    data = reports[user.id]

    for i, pregunta in enumerate(RONALD_QUESTIONS, 1):
        await channel.send(f"**{i}.** {pregunta}")
        msg = await obtener_respuesta(channel, user, pregunta)
        data["answers"][f"q{i}"] = msg.content

    await ask_final_questions(channel, user, data)

async def ask_final_questions(channel, user, data):
    pregunta = "¿Hubo alguna incidencia, problema o área de mejora hoy?"
    await channel.send(f"**Incidencia:** {pregunta}")
    msg = await obtener_respuesta(channel, user, pregunta)
    data["answers"]["incidencia"] = msg.content

    pregunta = "¿Comentarios finales del día?"
    await channel.send(f"**Notas adicionales:** {pregunta}")
    msg = await obtener_respuesta(channel, user, pregunta)
    data["answers"]["notas"] = msg.content

    await channel.send(f"✅ **Reporte {data['team'].upper()} completado. ¡Gracias!**")
    if user.id in reports:
        del reports[user.id]

# ==================== COMANDOS SLASH ====================
@bot.tree.command(name="reporte-tania", description="Inicia reporte manual Tania")
async def reporte_tania(interaction: discord.Interaction):
    await start_report(interaction, "tania")

@bot.tree.command(name="reporte-ronald", description="Inicia reporte manual Ronald")
async def reporte_ronald(interaction: discord.Interaction):
    await start_report(interaction, "ronald")

# ==================== INICIO DEL BOT ====================
bot.run(TOKEN)
