import discord
from discord.ext import commands
from uploader import handle_upload
from keep_alive import keep_alive  # 👈 activa el servidor keep-alive
import os

intents = discord.Intents.default()
intents.message_content = True  # Necesario para leer comandos
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

@bot.command(name="upload")
async def upload(ctx, *, nombre_topico):
    # Verifica si el usuario tiene el rol "Faculty"
    tiene_rol = any(rol.name.lower() == "faculty" for rol in ctx.author.roles)

    if not tiene_rol:
        await ctx.send("🚫 Este comando es solo para usuarios con el rol Faculty.")
        return

    await handle_upload(ctx, nombre_topico)

# Activa el servidor web para mantener el Repl despierto
keep_alive()

# Ejecuta el bot con el token desde las variables de entorno
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
