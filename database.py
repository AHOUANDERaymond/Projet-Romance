import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from config import Config
import logging

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.config = {
            'host': Config.MYSQL_HOST,
            'user': Config.MYSQL_USER,
            'password': Config.MYSQL_PASSWORD,
            'database': Config.MYSQL_DATABASE,
            'charset': 'utf8mb4',
            'cursorclass': DictCursor,
            'autocommit': False
        }
        logging.info("Base de données initialisée")
    
    @contextmanager
    def get_connection(self):
        connection = None
        try:
            connection = pymysql.connect(**self.config)
            yield connection
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            logging.error(f"Erreur DB: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    @contextmanager
    def get_cursor(self, connection=None):
        if connection:
            with connection.cursor() as cursor:
                yield cursor
        else:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    yield cursor

db = Database()