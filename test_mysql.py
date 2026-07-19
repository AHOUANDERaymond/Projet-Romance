import pymysql
from config import Config

try:
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE
    )
    print("✅ Connexion MySQL réussie !")
    conn.close()
except Exception as e:
    print(f"❌ Erreur de connexion : {e}")