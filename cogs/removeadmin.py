import discord
from discord import app_commands
from discord.ext import commands
from config import BOT_OWNER_ID
from db import db


class RemoveAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="removeadmin", description="Entfernt einen Benutzer als Bot-Admin (nur Owner).")
    @app_commands.describe(user="Der Benutzer, dessen Adminrechte entfernt werden sollen")
    async def removeadmin(self, interaction: discord.Interaction, user: discord.User):
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message("❌ Nur der Bot-Owner kann Admins entfernen.", ephemeral=True)
            return

        cursor = db.cursor()
        cursor.execute("DELETE FROM bot_admins WHERE user_id = %s", (user.id,))
        db.commit()
        cursor.close()

        await interaction.response.send_message(f"🚫 {user.mention} wurde als Admin entfernt.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RemoveAdmin(bot))