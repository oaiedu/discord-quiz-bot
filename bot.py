import discord
from discord.ext import commands
from uploader import handle_upload

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

@bot.command(name="upload")
async def upload(ctx, *, nombre_topico):
    # Verificar si el autor tiene el rol "Faculty"
    tiene_rol = any(rol.name.lower() == "faculty" for rol in ctx.author.roles)

    if not tiene_rol:
        await ctx.send("🚫 Este comando solo está disponible para usuarios con el rol **Faculty**.")
        return

    await handle_upload(ctx, nombre_topico)
    
bot.run("TU_TOKEN_AQUI")
