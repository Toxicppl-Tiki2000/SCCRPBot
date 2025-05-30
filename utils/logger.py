from config import LOG_CHANNEL_ID
from db import get_cursor, commit
from discord import Interaction

async def log_to_discord(bot, message: str):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)

def log_to_database(action_type, user, guild_name, ausweis_id=None, log_level="INFO"):
    try:
        cursor = get_cursor()
        cursor.execute("""
            INSERT INTO ausweis_logs (action_type, user_id, username, guild_name, ausweis_id, log_level)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (action_type, user.id, str(user), guild_name, ausweis_id, log_level))
        commit()
        cursor.close()
    except Exception as e:
        print(f"[ERROR] Fehler beim Loggen: {e}")
