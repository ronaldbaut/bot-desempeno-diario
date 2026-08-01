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

# Frases para cancelar
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

# ==================== PREGUNTAS RONALD ====================
RONALD_QUESTIONS = [
    "1. ¿Martha H., Josnelly B., Leomar J., Yomarlin P. y José P. llegaron a tiempo y asistieron correctamente a la jornada de hoy?",
    "2. ¿Martha H. aplicó y archivó correctamente las retenciones legales y mantuvo los contratos en orden y al día hoy?",
    "3. ¿Yomarlin y Josnelly brindaron atención amable a todos los clientes (incluyendo carritos heladeros) hoy?",
    "4. ¿Leomar J. logró la coincidencia del inventario físico de San Cristóbal con el sistema hoy?",
    "5. ¿José P. logró la coincidencia del inventario físico de San Cristóbal con el sistema hoy?",
    "6. ¿La ruta de reparto inició antes de las 9:30 a.m. hoy?",
    "7. ¿Cuántos viajes solo para cobrar se realizaron hoy?",
    "8. ¿La ruta de Leomar, según el GPS, coincide con los puntos de la ruta de ventas y los clientes nuevos visitados hoy?",
    "9. ¿La ruta de José P., según el GPS, coincide con los puntos de la ruta de ventas y los clientes nuevos visitados hoy?",
    "10. ¿Cuántos clientes nuevos visitó Leomar hoy?",
    "11. ¿Cuántos clientes nuevos visitó José P. hoy?"
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
  Ejemplos:
  - "Te falta decirme si lo hicieron correctamente o no."
  - "Responde sí o no de forma clara."
  - "No me dijiste la cantidad."
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

# ==================== HELPER PARA ESPERAR RESPUESTA (CON VALIDACIÓN) ====================
async def obtener_respuesta(channel, user, pregunta: str):
    """Espera una respuesta válida del usuario. Si es inválida, regaña y vuelve a preguntar."""
    while True:
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
        contenido = msg.content.strip().lower()

        # Detección de cancelar
        if any(phrase in contenido for phrase in CANCEL_PHRASES) or "cancelar" in contenido:
            await channel.send("✅ **Reporte cancelado.**\nPuedes iniciar uno nuevo cuando quieras usando los botones o los comandos `/reporte-tania` y `/reporte-ronald`.")
            if user.id in reports:
                del reports[user.id]
            raise ReporteCancelado()

        # Reacción
        try:
            await msg.add_reaction("✅")
        except:
            pass

        # Validar con Grok
        decision = await consultar_grok(pregunta, msg.content)

        if decision.get("respuesta_valida", True):
            return msg
        else:
            mensaje = decision.get("mensaje") or "Tu respuesta está incompleta. Responde correctamente."
            await channel.send(mensaje)
            # Vuelve a esperar otra respuesta (no avanza)

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
