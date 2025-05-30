import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
from config import SERVER_COLUMN_MAP, AUSWEIS_CHANNEL_ID
import mysql.connector
from utils.logger import log_to_database, log_to_discord
import datetime
from db import db

# --- Classes -----------------------------------------

class AusweisModal(Modal, title="Charakter-Ausweis erstellen"):
    def __init__(self, bot, interaction: discord.Interaction):
        super().__init__()
        self.bot = bot
        self.interaction = interaction

        self.name = TextInput(label="Name", placeholder="Mustermann", max_length=100)
        self.vorname = TextInput(label="Vorname", placeholder="Max", max_length=100)
        self.geburtsdatum = TextInput(label="Geburtsdatum (YYYY-MM-DD)", placeholder="2000-01-01")
        self.geschlecht = TextInput(label="Geschlecht", placeholder="männlich / weiblich / divers")
        self.unterschrift = TextInput(label="Unterschrift", placeholder="Max Mustermann")

        self.add_item(self.name)
        self.add_item(self.vorname)
        self.add_item(self.geburtsdatum)
        self.add_item(self.geschlecht)
        self.add_item(self.unterschrift)

    async def on_submit(self, interaction: discord.Interaction):
        guild_name = interaction.guild.name.lower() if interaction.guild else "Unbekannt"
        guild_id = interaction.guild.id if interaction.guild else 0
        server_column = SERVER_COLUMN_MAP.get(guild_id)

        try:
            # === Manuelle Validierungen ===
            if not self.name.value or len(self.name.value) < 2:
                raise ValueError("Name ist zu kurz oder fehlt.")
            if not self.vorname.value or len(self.vorname.value) < 2:
                raise ValueError("Vorname ist zu kurz oder fehlt.")
            if not self.geschlecht.value:
                raise ValueError("Geschlecht darf nicht leer sein.")
            if not self.unterschrift.value or len(self.unterschrift.value) < 2:
                raise ValueError("Unterschrift ist zu kurz oder fehlt.")

            # Geburtsdatum validieren (Format: YYYY-MM-DD)
            try:
                datetime.datetime.strptime(self.geburtsdatum.value, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Geburtsdatum hat ein ungültiges Format. Bitte JJJJ-MM-TT verwenden.")

            # === Datenbankeintrag ===
            cursor = db.cursor()
            cursor.execute(f"""
                INSERT INTO ausweise (name, vorname, geburtsdatum, geschlecht, unterschrift, {server_column}, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                self.name.value,
                self.vorname.value,
                self.geburtsdatum.value,
                self.geschlecht.value,
                self.unterschrift.value,
                True,
                interaction.user.id
            ))
            db.commit()
            ausweis_id = cursor.lastrowid
            cursor.close()

            # === Embed + Button ===
            embed = discord.Embed(title="🪪 Charakter-Ausweis", color=discord.Color.blue())
            embed.add_field(name="Name", value=self.name.value, inline=True)
            embed.add_field(name="Vorname", value=self.vorname.value, inline=True)
            embed.add_field(name="Geburtsdatum", value=self.geburtsdatum.value, inline=True)
            embed.add_field(name="Geschlecht", value=self.geschlecht.value, inline=True)
            embed.add_field(name="Unterschrift", value=self.unterschrift.value, inline=False)

            channel = self.bot.get_channel(AUSWEIS_CHANNEL_ID)
            msg = await channel.send(embed=embed)
            view = AusweisView(self.bot, ausweis_id, msg)
            await msg.edit(view=view)

            await interaction.response.send_message("✅ Ausweis wurde zur Überprüfung eingereicht.", ephemeral=True)

            # === Logging ===
            log_to_database("erstellt", interaction.user, guild_name, ausweis_id)
            await log_to_discord(f"📥 Neuer Ausweis eingereicht von `{interaction.user}` auf **{guild_name}** (ID: `{ausweis_id}`)")

        except ValueError as ve:
            await interaction.response.send_message(f"❌ Fehler im Formular: {ve}", ephemeral=True)

        except mysql.connector.Error as sql_err:
            await interaction.response.send_message("❌ Es gab ein Problem mit der Datenbank. Bitte versuche es später erneut.", ephemeral=True)
            print("SQL Fehler:", sql_err)

        except Exception as e:
            await interaction.response.send_message("❌ Ein unerwarteter Fehler ist aufgetreten. Bitte melde dich ggf. beim Admin.", ephemeral=True)
            print("Allgemeiner Fehler im Ausweis-Modal:", e)


class AusweisView(View):
    def __init__(self, bot, ausweis_id, message):
        super().__init__(timeout=None)
        self.bot = bot
        self.ausweis_id = ausweis_id
        self.message = message

    @discord.ui.button(label="✅", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # Sofortige Bestätigung

        # Nutzerdaten holen
        cursor = db.cursor()
        cursor.execute("""
            SELECT user_id, name, vorname, geburtsdatum, geschlecht, unterschrift
            FROM ausweise WHERE id = %s
        """, (self.ausweis_id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            user_id, name, vorname, geburtsdatum, geschlecht, unterschrift = result
            user = await self.bot.fetch_user(user_id)

            embed = discord.Embed(
                title="✅ Dein Ausweis wurde bestätigt",
                description="Herzlichen Glückwunsch! Dein Charakter-Ausweis wurde angenommen.",
                color=discord.Color.green()
            )
            embed.add_field(name="Name", value=name, inline=True)
            embed.add_field(name="Vorname", value=vorname, inline=True)
            embed.add_field(name="Geburtsdatum", value=geburtsdatum, inline=True)
            embed.add_field(name="Geschlecht", value=geschlecht, inline=True)
            embed.add_field(name="Unterschrift", value=unterschrift, inline=False)

            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                print(f"[WARN] Konnte {user} keine DM senden.")

        await self.message.delete()  # Lösche die Nachricht
        await interaction.followup.send("Ausweis bestätigt.", ephemeral=True)


# --- Cog + Command ----------------------------------

class Ausweis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="ausweis", description="Erstelle einen Charakter-Ausweis")
    async def ausweis_slash(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AusweisModal(self.bot, interaction))


async def setup(bot):
    await bot.add_cog(Ausweis(bot))
