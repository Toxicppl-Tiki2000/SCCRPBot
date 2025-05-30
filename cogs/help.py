import discord
from discord import app_commands
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Zeigt eine Übersicht aller verfügbaren Befehle.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🆘 Hilfe & Befehlsübersicht", color=discord.Color.blurple())
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.description = "Hier ist eine Liste der verfügbaren Slash-Befehle für den Bot:"

        embed.add_field(
            name="/ausweis",
            value="Erstellt einen Charakter-Ausweis.",
            inline=False
        )
        embed.add_field(
            name="/identifizieren <name>",
            value="Sucht nach einem Spieler anhand von Vor- oder Nachname.",
            inline=False
        )
        embed.add_field(
            name="/meine_ausweise",
            value="Zeigt deine gespeicherten Ausweise an (Admins sehen alle).",
            inline=False
        )
        embed.add_field(
            name="/ausweis_loeschen",
            value="Löscht einen deiner Ausweise (Admins können alle löschen).",
            inline=False
        )
        embed.add_field(
            name="/clear <anzahl>",
            value="Löscht eine bestimmte Anzahl von Nachrichten im Channel (Admin).",
            inline=False
        )
        embed.add_field(
            name="/addadmin <user>\n/removeadmin <user>",
            value="Verwaltet die Bot-Admins (nur Bot-Owner).",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))
