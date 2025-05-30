import os
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
from discord import app_commands, Interaction, Member
from dotenv import load_dotenv
from typing import Optional
import mysql.connector

# Lade .env
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# MySQL-Verbindung
db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)

MAIN_GUILD_ID = 1376126506090102956
SUB_GUILD_IDS = [1376126506090102956]

SERVER_COLUMN_MAP = {
    1376126506090102956: "SCCRP",
    #1234567890123456789: "ger_server2",
    # usw.
}

def log_to_database(action_type, user, guild_name, ausweis_id=None, log_level="INFO"):
    try:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO ausweis_logs (action_type, user_id, username, guild_name, ausweis_id, log_level)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (action_type, user.id, str(user), guild_name, ausweis_id, log_level))
        db.commit()
        cursor.close()
    except Exception as e:
        print(f"[ERROR] Fehler beim Loggen in die Datenbank: {e}")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

AUSWEIS_CHANNEL_ID = 1377300461501153310
LOG_CHANNEL_ID = 1377300324519510067

def is_admin(user_id: int) -> bool:
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM bot_admins WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None


async def log_to_discord(message: str):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)


class AusweisModal(Modal, title="Charakter-Ausweis erstellen"):
    def __init__(self, interaction: discord.Interaction):
        super().__init__()
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

            # Geburtsdatum validieren (Format: TT.MM.JJJJ)
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

            channel = bot.get_channel(AUSWEIS_CHANNEL_ID)
            msg = await channel.send(embed=embed)
            view = AusweisView(ausweis_id, msg)
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
    def __init__(self, ausweis_id, message):
        super().__init__(timeout=None)
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
            user = await bot.fetch_user(user_id)

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
        await interaction.followup.send("Ausweis bestätigt.", ephemeral=True)  # Folg der Bestätigung



    @discord.ui.button(label="❌", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # Sofortige Bestätigung

        cursor = db.cursor()
        cursor.execute("""
            SELECT user_id, name, vorname
            FROM ausweise WHERE id = %s
        """, (self.ausweis_id,))
        result = cursor.fetchone()

        if result:
            user_id, name, vorname = result
            user = await bot.fetch_user(user_id)

            embed = discord.Embed(
                title="❌ Dein Ausweis wurde abgelehnt",
                description="Dein Charakter-Ausweis wurde leider abgelehnt. Du kannst es erneut versuchen.",
                color=discord.Color.red()
            )
            embed.add_field(name="Name", value=name, inline=True)
            embed.add_field(name="Vorname", value=vorname, inline=True)

            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                print(f"[WARN] Konnte {user} keine DM senden.")

        cursor.execute("DELETE FROM ausweise WHERE id = %s", (self.ausweis_id,))
        db.commit()
        cursor.close()

        try:
            await self.message.delete()
        except discord.NotFound:
            print("[WARN] Nachricht bereits gelöscht.")



@tree.command(name="ausweis", description="Erstelle einen Charakter-Ausweis")
async def ausweis_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(AusweisModal(interaction))

@tree.command(name="identifizieren", description="Identifiziere einen Spieler anhand von Name oder Vorname")
async def identifizieren(interaction: discord.Interaction, name: str):
    guild_id = interaction.guild.id

    server_column = SERVER_COLUMN_MAP.get(guild_id)

    if not server_column:
        await interaction.response.send_message("Dieser Server ist nicht registriert.", ephemeral=True)
        return

    # Name-Filter für Nachname, Vorname oder Kombination
    name_parts = name.split()
    like_pattern = f"%{name}%"

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

    cursor = db.cursor()
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


BOT_OWNER_ID = 841635692035047475  # Deine eigene Discord-User-ID

@tree.command(name="addadmin", description="Fügt einen Benutzer als Bot-Admin hinzu (nur Owner).")
@app_commands.describe(user="Der Benutzer, der Admin werden soll")
async def addadmin(interaction: discord.Interaction, user: discord.User):
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

@tree.command(name="removeadmin", description="Entfernt einen Benutzer als Bot-Admin (nur Owner).")
@app_commands.describe(user="Der Benutzer, dessen Adminrechte entfernt werden sollen")
async def removeadmin(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message("❌ Nur der Bot-Owner kann Admins entfernen.", ephemeral=True)
        return

    cursor = db.cursor()
    cursor.execute("DELETE FROM bot_admins WHERE user_id = %s", (user.id,))
    db.commit()
    cursor.close()

    await interaction.response.send_message(f"🚫 {user.mention} wurde als Admin entfernt.", ephemeral=True)


@tree.command(name="clear", description="Löscht Nachrichten im aktuellen Channel.")
@app_commands.describe(anzahl="Anzahl der zu löschenden Nachrichten")
async def clear(interaction: discord.Interaction, anzahl: int):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Du hast keine Berechtigung für diesen Befehl.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(limit=anzahl)
    await interaction.followup.send(f"✅ {len(deleted)} Nachrichten wurden gelöscht.", ephemeral=True)

@bot.tree.command(name="meine_ausweise", description="Zeigt deine eigenen Ausweise oder alle (wenn Admin).")
async def meine_ausweise(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    server_column = SERVER_COLUMN_MAP.get(guild_id)

    cursor = db.cursor(dictionary=True)

    # Check Admin
    cursor.execute("SELECT * FROM bot_admins WHERE user_id = %s", (user_id,))

    is_admin = cursor.fetchone() is not None

    if is_admin:
        cursor.execute(f"SELECT id, name, vorname, user_id FROM ausweise WHERE {server_column} = %s", (True,))
    else:
        cursor.execute(f"SELECT id, name, vorname FROM ausweise WHERE user_id = %s AND {server_column} = %s", (user_id, True))

    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        await interaction.followup.send("Du hast keine Ausweise gefunden." if not is_admin else "Es wurden keine Ausweise gefunden.", ephemeral=True)
        return

    embed = discord.Embed(title="🪪 Gefundene Ausweise", color=discord.Color.green())
    for row in rows:
        text = f"Name: **{row['vorname']} {row['name']}**"
        if is_admin:
            text += f" | User ID: `{row['user_id']}`"
        embed.add_field(name=f"ID: {row['id']}", value=text, inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

class AusweisLoeschenView(discord.ui.View):
    def __init__(self, ausweise, is_admin, target_user_id):
        super().__init__(timeout=60)
        self.add_item(AusweisDropdown(ausweise, is_admin, target_user_id))


class AusweisDropdown(discord.ui.Select):
    def __init__(self, ausweise, is_admin, target_user_id):
        options = [
            discord.SelectOption(label=f"{a['vorname']} {a['name']}", description=f"ID: {a['id']}", value=str(a['id']))
            for a in ausweise
        ]
        super().__init__(placeholder="Wähle einen Ausweis zum Löschen", min_values=1, max_values=1, options=options)
        self.ausweise = ausweise
        self.is_admin = is_admin
        self.target_user_id = target_user_id

    async def callback(self, interaction: discord.Interaction):
        ausweis_id = int(self.values[0])
        cursor = db.cursor()
        if self.is_admin:
            cursor.execute("DELETE FROM ausweise WHERE id = %s", (ausweis_id,))
        else:
            cursor.execute("DELETE FROM ausweise WHERE id = %s AND user_id = %s", (ausweis_id, interaction.user.id))
        db.commit()
        cursor.close()

        await interaction.response.edit_message(content=f"✅ Ausweis mit ID `{ausweis_id}` wurde gelöscht.", view=None)

@bot.tree.command(name="ausweis_loeschen", description="Löscht einen deiner Ausweise (Admins können alle löschen).")
async def ausweis_loeschen(interaction: discord.Interaction, user: Optional[discord.User] = None):
    await interaction.response.defer(ephemeral=True)
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    server_column = SERVER_COLUMN_MAP.get(guild_id)

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

    view = AusweisLoeschenView(ausweise, is_admin, target_user_id, interaction.user, interaction.guild.name)
    await interaction.followup.send("Wähle den Ausweis, den du löschen möchtest:", view=view, ephemeral=True)


class AusweisLoeschenView(discord.ui.View):
    def __init__(self, ausweise, is_admin, target_user_id, executor_user, guild_name):
        super().__init__()
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


class AusweisSelect(discord.ui.Select):
    def __init__(self, options, parent_view):
        super().__init__(placeholder="Wähle einen Ausweis...", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        ausweis_id = int(self.values[0])
        cursor = db.cursor()

        cursor.execute("DELETE FROM ausweise WHERE id = %s", (ausweis_id,))
        db.commit()
        cursor.close()

        # Loggen
        log_to_database(
            action_type="ausweis_geloescht",
            user=self.parent_view.executor_user,
            guild_name=self.parent_view.guild_name,
            ausweis_id=ausweis_id
        )

        await interaction.response.edit_message(
            content=f"✅ Ausweis mit ID `{ausweis_id}` wurde gelöscht.",
            view=None
        )

@tree.command(name="help", description="Zeigt eine Übersicht aller verfügbaren Befehle.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🆘 Hilfe & Befehlsübersicht", color=discord.Color.blurple())
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else discord.Embed.Empty)
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


@bot.event
async def on_ready():
    synced = await tree.sync()
    print(f"✅ Bot ist online als {bot.user.name} (ID: {bot.user.id})")
    print(f"🔁 {len(synced)} Slash Command(s) synchronisiert:")
    for command in synced:
        print(f" - /{command.name}: {command.description}")


bot.run(DISCORD_TOKEN)