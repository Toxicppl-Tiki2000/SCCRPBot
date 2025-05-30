import discord
from discord import app_commands
from discord.ext import commands
from config import SERVER_COLUMN_MAP
from db import db

# View für die Dropdown-Auswahl
class AusweisLoeschenView(discord.ui.View):
    def __init__(self, ausweise, is_admin, target_user_id):
        super().__init__(timeout=60)
        self.add_item(AusweisDropdown(ausweise, is_admin, target_user_id))

# Dropdown-Menü zur Auswahl eines Ausweises
class AusweisDropdown(discord.ui.Select):
    def __init__(self, ausweise, is_admin, target_user_id):
        options = [
            discord.SelectOption(
                label=f"{a['vorname']} {a['name']}",
                description=f"ID: {a['id']}",
                value=str(a['id'])
            )
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

        await interaction.followup.send(
            embed=embed,
            view=AusweisLoeschenView(rows, is_admin, user_id),
            ephemeral=True
        )


# Setup-Funktion
async def setup(bot):
    await bot.add_cog(Meine_Ausweise(bot))
