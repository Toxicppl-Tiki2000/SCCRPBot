import mysql.connector
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)

def get_cursor():
    return db.cursor()

def commit():
    db.commit()
