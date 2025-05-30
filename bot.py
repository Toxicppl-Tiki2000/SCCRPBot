import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # Falls du User-Infos brauchst (z.B. bei /ausweis_loeschen)

bot = commands.Bot(command_prefix=None, intents=intents)  # Nur Slash Commands

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔃 Slash Commands synchronisiert ({len(synced)} Befehle)")
    except Exception as e:
        print(f"⚠️ Fehler beim Slash Sync: {e}")

# Automatisch alle Cogs aus dem "cogs/" Ordner laden
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"📦 Geladen: {filename}")
            except Exception as e:
                print(f"❌ Fehler beim Laden von {filename}: {e}")
    print(f"📁 Vorhandene Dateien: {os.listdir('./cogs')}")


async def main():
    await load_cogs()
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
