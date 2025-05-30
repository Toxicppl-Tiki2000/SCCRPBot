import discord
from discord import app_commands
from discord.ext import commands
from config import SERVER_COLUMN_MAP
from db import db


class Identifizieren(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="identifizieren", description="Identifiziere einen Spieler anhand von Name oder Vorname")
    @app_commands.describe(name="Name oder Vorname des Spielers")
    async def identifizieren(self, interaction: discord.Interaction, name: str):
        guild_id = interaction.guild.id
        server_column = SERVER_COLUMN_MAP.get(guild_id)

        if not server_column:
            await interaction.response.send_message("Dieser Server ist nicht registriert.", ephemeral=True)
            return

        name_parts = name.split()
        cursor = db.cursor()

        if len(name_parts) == 2:
            vorname_like = f"%{name_parts[0]}%"
            nachname_like = f"%{name_parts[1]}%"
            query = f"""
                SELECT id, name, vorname, geburtsdatum, geschlecht, unterschrift
                FROM ausweise
                WHERE {server_column} = TRUE AND (
                    (vorname LIKE %s AND name LIKE %s)
                )
            """
            values = (vorname_like, nachname_like)
        else:
            like = f"%{name}%"
            query = f"""
                SELECT id, name, vorname, geburtsdatum, geschlecht, unterschrift
                FROM ausweise
                WHERE {server_column} = TRUE AND (
                    vorname LIKE %s OR name LIKE %s OR CONCAT(vorname, ' ', name) LIKE %s
                )
            """
            values = (like, like, like)

        cursor.execute(query, values)
        results = cursor.fetchall()
        cursor.close()

        if results:
            embed = discord.Embed(title="🪪 Ausweise gefunden", color=discord.Color.green())
            for result in results:
                ausweis_id, name, vorname, geburtsdatum, geschlecht, unterschrift = result
                embed.add_field(
                    name=f"{name} {vorname}",
                    value=f"Geburtsdatum: {geburtsdatum}\nGeschlecht: {geschlecht}\nUnterschrift: {unterschrift}",
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"Kein Ausweis mit dem Namen '{name}' gefunden.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Identifizieren(bot))
