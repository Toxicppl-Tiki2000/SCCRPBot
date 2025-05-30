import discord
from discord import app_commands
from discord.ext import commands
from config import BOT_OWNER_ID
from db import db


class AddAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addadmin", description="Fügt einen Benutzer als Bot-Admin hinzu (nur Owner).")
    @app_commands.describe(user="Der Benutzer, der Admin werden soll")
    async def addadmin(self, interaction: discord.Interaction, user: discord.User):
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message("❌ Nur der Bot-Owner kann Admins hinzufügen.", ephemeral=True)
            return

        cursor = db.cursor()
        cursor.execute("""
            INSERT IGNORE INTO bot_admins (user_id, username) VALUES (%s, %s)
        """, (user.id, str(user)))
        db.commit()
        cursor.close()

        await interaction.response.send_message(f"✅ {user.mention} wurde als Admin hinzugefügt.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AddAdmin(bot))