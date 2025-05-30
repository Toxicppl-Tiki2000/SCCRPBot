import discord
from discord import app_commands
from discord.ext import commands
from config import SERVER_COLUMN_MAP
from db import db
from utils.logger import log_to_database, log_to_discord
from typing import Optional


class AusweisSelect(discord.ui.Select):
    def __init__(self, options, parent_view):
        super().__init__(placeholder="Wähle einen Ausweis...", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        ausweis_id = int(self.values[0])
        cursor = db.cursor()

        if self.parent_view.is_admin:
            cursor.execute("DELETE FROM ausweise WHERE id = %s", (ausweis_id,))
        else:
            cursor.execute(
                "DELETE FROM ausweise WHERE id = %s AND user_id = %s",
                (ausweis_id, self.parent_view.executor_user.id)
            )

        db.commit()
        cursor.close()

        # Log in Datenbank
        log_to_database(
            action_type="ausweis_geloescht",
            user=self.parent_view.executor_user,
            guild_name=self.parent_view.guild_name,
            ausweis_id=ausweis_id
        )

        # Log in Discord
        log_message = (
            f"🗑️ **Ausweis gelöscht**\n"
            f"👤 User: `{self.parent_view.executor_user}` (`{self.parent_view.executor_user.id}`)\n"
            f"🆔 Ausweis-ID: `{ausweis_id}`\n"
            f"🌐 Server: `{self.parent_view.guild_name}`"
        )
        await log_to_discord(self.parent_view.bot, log_message)

        await interaction.response.edit_message(
            content=f"✅ Ausweis mit ID `{ausweis_id}` wurde gelöscht.",
            view=None
        )


class AusweisLoeschenView(discord.ui.View):
    def __init__(self, bot, ausweise, is_admin, target_user_id, executor_user, guild_name):
        super().__init__(timeout=60)
        self.bot = bot
        self.ausweise = ausweise
        self.is_admin = is_admin
        self.target_user_id = target_user_id
        self.executor_user = executor_user
        self.guild_name = guild_name

        options = [
            discord.SelectOption(
                label=f"{a['vorname']} {a['name']}", description=f"ID: {a['id']}", value=str(a['id'])
            )
            for a in ausweise
        ]
        self.add_item(AusweisSelect(options, self))


class AusweisLoeschen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ausweis_loeschen", description="Löscht einen deiner Ausweise (Admins können alle löschen).")
    @app_commands.describe(user="Optional: Ausweise dieses Benutzers löschen (nur für Admins)")
    async def ausweis_loeschen(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        guild_id = interaction.guild.id
        server_column = SERVER_COLUMN_MAP.get(guild_id)

        if not server_column:
            await interaction.followup.send("❌ Dieser Server ist nicht konfiguriert.", ephemeral=True)
            return

        cursor = db.cursor(dictionary=True)

        # Admin prüfen
        cursor.execute("SELECT * FROM bot_admins WHERE user_id = %s", (user_id,))
        is_admin = cursor.fetchone() is not None

        # Ziel-User bestimmen
        target_user_id = user.id if (is_admin and user) else user_id

        cursor.execute(
            f"SELECT id, name, vorname FROM ausweise WHERE user_id = %s AND {server_column} = %s",
            (target_user_id, True)
        )
        ausweise = cursor.fetchall()
        cursor.close()

        if not ausweise:
            await interaction.followup.send("⚠️ Keine Ausweise gefunden.", ephemeral=True)
            return

        view = AusweisLoeschenView(self.bot, ausweise, is_admin, target_user_id, interaction.user, interaction.guild.name)
        await interaction.followup.send("Wähle den Ausweis, den du löschen möchtest:", view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AusweisLoeschen(bot))
