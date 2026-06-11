import discord
from discord.ext import tasks, commands
from discord.ui import Button, View
from datetime import time
from zoneinfo import ZoneInfo
import json
from datetime import datetime
import os

print(">>> Iniciando bot...")

# ==================== CONFIGURACIÓN ====================
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

reports = {}

# ==================== PREGUNTAS TANIA ====================
TANIA_QUESTIONS = { ... }  # (mantén todo el diccionario igual)

# ==================== PREGUNTAS RONALD ====================
RONALD_QUESTIONS = [ ... ]  # (mantén la lista igual)

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
    await bot.tree.sync()           # ← Esta es la línea importante
    print("✅ Slash commands sincronizados")
    daily_report.start()

# (el resto del código se mantiene igual: on_interaction, start_report, ask_tania_questions, etc.)

bot.run(TOKEN)
