import psycopg2
import os
from psycopg2 import sql

def get_connection():
    try:
        connexion = psycopg2.connect(
            host="localhost",
            database="real_estate_db",
            user="lamloum",
            password="lamloum123" 
        )
        return connexion
    except Exception as e:
        print(f"Erreur de connexion : {e}")
        return None