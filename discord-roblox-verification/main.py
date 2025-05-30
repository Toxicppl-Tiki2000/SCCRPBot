from flask import Flask, request, jsonify
import os
import mysql.connector
from datetime import datetime

app = Flask(__name__)

db = None
try:
    db = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
except:
    print("⚠️ Keine Datenbankverbindung – lokal oder beim ersten Upload OK.")

@app.route("/verify", methods=["POST"])
def verify():
    data = request.json
    code = data.get("code")
    roblox_user_id = data.get("roblox_user_id")
    roblox_username = data.get("roblox_username")

    if not code or not roblox_user_id:
        return jsonify({"error": "Fehlende Daten"}), 400

    cursor = db.cursor(dictionary=True)
    
    # Code prüfen
    cursor.execute("SELECT * FROM discord_roblox_links WHERE code = %s AND expires_at > NOW()", (code,))
    result = cursor.fetchone()

    if not result:
        return jsonify({"error": "Ungültiger oder abgelaufener Code"}), 400

    discord_id = result["discord_id"]

    # Roblox-Daten in DB schreiben
    cursor.execute("""
        UPDATE discord_roblox_links
        SET roblox_user_id = %s, roblox_username = %s, code = NULL, expires_at = NULL
        WHERE discord_id = %s
    """, (roblox_user_id, roblox_username, discord_id))
    
    db.commit()
    cursor.close()

    return jsonify({"message": "Verknüpfung erfolgreich"}), 200

if __name__ == "__main__":
    app.run()
