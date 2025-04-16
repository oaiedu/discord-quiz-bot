import discord
import os

RUTA_DOCS = "docs"

async def handle_upload(ctx, nombre_topico):
    if not ctx.message.attachments:
        await ctx.send("❌ Por favor, adjunta un archivo PDF junto con el comando.")
        return

    archivo = ctx.message.attachments[0]

    if not archivo.filename.endswith(".pdf"):
        await ctx.send("❌ Solo se permiten archivos PDF.")
        return

    await ctx.send(f"📥 Recibiendo el archivo para el tema: **{nombre_topico}**...")

    os.makedirs(RUTA_DOCS, exist_ok=True)

    ruta_pdf = os.path.join(RUTA_DOCS, f"{nombre_topico}.pdf")
    await archivo.save(ruta_pdf)

    await ctx.send(f"✅ PDF guardado como `{nombre_topico}.pdf` en la carpeta `/docs`.")
