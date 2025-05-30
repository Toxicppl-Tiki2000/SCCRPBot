import discord
from discord import app_commands
from discord.ext import commands
from utils.helpers import is_admin
from utils.logger import log_to_database, log_to_discord

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Löscht Nachrichten im aktuellen Channel.")
    @app_commands.describe(anzahl="Anzahl der zu löschenden Nachrichten")
    async def clear(self, interaction: discord.Interaction, anzahl: int):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Du hast keine Berechtigung für diesen Befehl.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.followup.send("Dieser Befehl kann nur in Text-Channels verwendet werden.", ephemeral=True)
            return

        deleted = await interaction.channel.purge(limit=anzahl)
        await interaction.followup.send(f"✅ {len(deleted)} Nachrichten wurden gelöscht.", ephemeral=True)

        # Logging mit bereits definierten Funktionen aus utils.helpers
        details = f"Anzahl gelöschter Nachrichten: {len(deleted)} in Kanal #{interaction.channel.name} (ID: {interaction.channel.id})"
        log_to_database("clear_command", interaction.user, interaction.guild.name if interaction.guild else "DM", details)
        await log_to_discord(self.bot, f"🧹 `{interaction.user}` hat {len(deleted)} Nachrichten in #{interaction.channel.name} gelöscht.")

async def setup(bot):
    await bot.add_cog(Clear(bot))
