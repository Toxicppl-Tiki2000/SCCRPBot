from discord import app_commands, Interaction, ui
from discord.ext import commands
import discord
import random
import string
from datetime import datetime, timedelta
from config import BOT_OWNER_ID
from db import db  # DB-Verbindung

class RobloxVerknuepfung(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- UI View mit Button ---
    class VerknuepfungView(ui.View):
        def __init__(self, bot):
            super().__init__(timeout=None)
            self.bot = bot

        @ui.button(label="🎮 Roblox Account verknüpfen", style=discord.ButtonStyle.blurple)
        async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            user_id = interaction.user.id

            # Generiere zufälligen Code
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            expires = datetime.utcnow() + timedelta(minutes=15)

            # DB-Eintrag (INSERT oder UPDATE)
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO discord_roblox_links (discord_user_id, pending_code, code_expires_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE pending_code = VALUES(pending_code), code_expires_at = VALUES(code_expires_at)
            """, (user_id, code, expires))
            db.commit()
            cursor.close()

            # Sende Code nur an den User
            await interaction.response.send_message(
                f"🔐 Dein persönlicher Verknüpfungscode: `{code}`\n"
                "⚠️ Gültig für 15 Minuten. Gib diesen Code im Roblox-Spiel ein.",
                ephemeral=True
            )

    # --- Slash Command ---
    @app_commands.command(name="verify", description="Sendet Embed für Roblox-Verknüpfung (nur Owner).")
    async def verknuepfen_start(self, interaction: discord.Interaction):
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message("❌ Nur der Bot-Owner kann diesen Befehl ausführen.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔗 Roblox Verknüpfung starten",
            description="Drücke auf den Button, um deinen Discord-Account mit deinem Roblox-Account zu verknüpfen.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=self.VerknuepfungView(self.bot))

async def setup(bot):
    await bot.add_cog(RobloxVerknuepfung(bot))
