import discord
from discord.ext import tasks, commands
from discord.ui import Button, View
from datetime import time
from zoneinfo import ZoneInfo
import json
from datetime import datetime
import os

print(">>> Iniciando bot...")

# ==================== DEBUG DE VARIABLES ====================
print("DEBUG: TOKEN existe?", "SÍ" if os.getenv("TOKEN") else "NO")
print("DEBUG: CHANNEL_ID raw =", os.getenv("CHANNEL_ID"))
print("DEBUG: Todas las variables:", dict(os.environ))

# ==================== CONFIGURACIÓN ====================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("ERROR: No se encontró la variable TOKEN")
    exit(1)

try:
    CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
except (TypeError, ValueError):
    print("ERROR: CHANNEL_ID no es un número válido o está vacío")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

reports = {}

# (el resto del código es igual)

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

# ==================== TAREA DIARIA ====================
@tasks.loop(time=time(hour=20, minute=0, tzinfo=ZoneInfo("Europe/Madrid")))
async def daily_report():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    view = View()
    view.add_item(Button(label="Iniciar Reporte Tania", style=discord.ButtonStyle.primary, custom_id="tania"))
    view.add_item(Button(label="Iniciar Reporte Ronald", style=discord.ButtonStyle.primary, custom_id="ronald"))

    await channel.send("🕒 **Hora del Reporte Diario (20:00)**\n¿Comenzamos?", view=view)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    daily_report.start()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data["custom_id"] == "tania":
        await start_report(interaction, "tania")
    elif interaction.data["custom_id"] == "ronald":
        await start_report(interaction, "ronald")

async def start_report(interaction, team):
    await interaction.response.defer()
    channel = interaction.channel
    user = interaction.user

    report_data = {"team": team, "date": datetime.now().strftime("%Y-%m-%d"), "answers": {}}
    reports[user.id] = report_data

    await channel.send(f"📋 **Reporte {team.upper()} iniciado** por {user.mention}")

    if team == "tania":
        await ask_tania_questions(channel, user)
    else:
        await ask_ronald_questions(channel, user)

async def ask_tania_questions(channel, user):
    data = reports[user.id]

    await channel.send(f"**1.** {TANIA_QUESTIONS['alistamiento']}")
    msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
    data["answers"]["alistamiento"] = msg.content

    await channel.send(f"**2.** {TANIA_QUESTIONS['produccion']}")
    msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
    hubo_produccion = msg.content.lower() in ["sí", "si", "yes", "1"]

    if hubo_produccion:
        keys = ["licuadas", "protocolo_batidoras", "cambios_agua", "tiempo_produccion", "implementos", "envasado", "asistencia"]
        for i, key in enumerate(keys, 3):
            await channel.send(f"**{i}.** {TANIA_QUESTIONS[key]}")
            msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
            data["answers"][key] = msg.content

    await channel.send(f"**10.** {TANIA_QUESTIONS['reporte_materia']}")
    msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
    data["answers"]["reporte_materia"] = msg.content

    await channel.send(f"**11.** {TANIA_QUESTIONS['protocolo_cierre']}")
    msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
    data["answers"]["protocolo_cierre"] = msg.content

    await ask_final_questions(channel, user, data)

async def ask_ronald_questions(channel, user):
    data = reports[user.id]

    for i, question in enumerate(RONALD_QUESTIONS, 1):
        await channel.send(f"**{i}.** {question}")
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
        data["answers"][f"q{i}"] = msg.content

    await ask_final_questions(channel, user, data)

async def ask_final_questions(channel, user, data):
    await channel.send("**Incidencia:** ¿Hubo alguna incidencia, problema o área de mejora hoy?")
    msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
    data["answers"]["incidencia"] = msg.content

    await channel.send("**Notas adicionales:** ¿Comentarios finales del día?")
    msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel)
    data["answers"]["notas"] = msg.content

    await save_report(channel, user, data)

async def save_report(channel, user, data):
    filename = f"reporte_{data['team']}_{data['date']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    await channel.send(f"✅ **Reporte {data['team'].upper()} guardado** por {user.mention}")
    await channel.send(f"```json\n{json.dumps(data['answers'], ensure_ascii=False, indent=2)}\n```")
    await channel.send(f"Archivo guardado: `{filename}`")

# ==================== COMANDOS MANUALES ====================
@bot.tree.command(name="reporte-tania", description="Inicia reporte manual Tania")
async def reporte_tania(interaction: discord.Interaction):
    await start_report(interaction, "tania")

@bot.tree.command(name="reporte-ronald", description="Inicia reporte manual Ronald")
async def reporte_ronald(interaction: discord.Interaction):
    await start_report(interaction, "ronald")

bot.run(TOKEN)
