from db import get_cursor

def is_admin(user_id: int) -> bool:
    cursor = get_cursor()
    cursor.execute("SELECT 1 FROM bot_admins WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None
