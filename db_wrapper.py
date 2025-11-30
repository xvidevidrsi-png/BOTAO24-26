import os
import sqlite3
import psycopg2
from psycopg2 import sql
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_zeus.db")

def get_connection():
    """Retorna conexão com PostgreSQL ou SQLite baseado em DATABASE_URL"""
    if DATABASE_URL.startswith("postgres"):
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect("bot_zeus.db", timeout=1.0)

class ConnectionWrapper:
    """Wrapper para manter interface compatível entre SQLite e PostgreSQL"""
    def __init__(self, conn):
        self.conn = conn
        self.cursor_obj = None
    
    def cursor(self):
        self.cursor_obj = self.conn.cursor()
        return self.cursor_obj
    
    def commit(self):
        self.conn.commit()
    
    def close(self):
        if self.cursor_obj:
            self.cursor_obj.close()
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()

def sqlite3_connect(*args, **kwargs):
    """Drop-in replacement para sqlite3.connect()"""
    conn = get_connection()
    return ConnectionWrapper(conn)
