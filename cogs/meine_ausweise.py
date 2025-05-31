import discord
from discord import app_commands
from discord.ext import commands
from config import SERVER_COLUMN_MAP
from db import db

# Haupt-Cog
class Meine_Ausweise(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash-Command
    @app_commands.command(name="meine_ausweise", description="Zeigt deine eigenen Ausweise oder alle (wenn Admin).")
    async def meine_ausweise(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        server_column = SERVER_COLUMN_MAP.get(guild_id)

        if not server_column:
            await interaction.followup.send("❌ Dieser Server ist nicht registriert.", ephemeral=True)
            return

        cursor = db.cursor(dictionary=True)

        # Admin prüfen
        cursor.execute("SELECT * FROM bot_admins WHERE user_id = %s", (user_id,))
        is_admin = cursor.fetchone() is not None

        if is_admin:
            cursor.execute(f"SELECT id, name, vorname, user_id FROM ausweise WHERE {server_column} = %s", (True,))
        else:
            cursor.execute(f"SELECT id, name, vorname FROM ausweise WHERE user_id = %s AND {server_column} = %s", (user_id, True))

        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            message = "Du hast keine Ausweise gefunden." if not is_admin else "Es wurden keine Ausweise gefunden."
            await interaction.followup.send(message, ephemeral=True)
            return

        embed = discord.Embed(title="🪪 Gefundene Ausweise", color=discord.Color.green())
        for row in rows:
            text = f"Name: **{row['vorname']} {row['name']}**"
            if is_admin:
                text += f" | User ID: `{row['user_id']}`"
            embed.add_field(name=f"ID: {row['id']}", value=text, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

# Setup-Funktion
async def setup(bot):
    await bot.add_cog(Meine_Ausweise(bot))
