import os
import asyncio
import uuid
import random
import datetime
import re
import gc
from io import BytesIO
from typing import List, Dict, Optional
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput
from aiohttp import web
from collections import defaultdict
from dotenv import load_dotenv
import psycopg2
import sqlite3

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """Retorna conexão com PostgreSQL se DATABASE_URL existir, senão SQLite"""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect("bot_zeus.db", timeout=1.0)

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
BOT_PREFIX = "!"
DB_FILE = "bot_zeus.db"

VALORES_FILAS_1V1 = [100.00, 50.00, 40.00, 30.00, 20.00, 10.00, 5.00, 3.00, 2.00, 1.00, 0.80, 0.40]
TAXA_POR_JOGADOR = 0.10
COIN_POR_VITORIA = 1
BOT_OWNER_USERNAME = "emanoel7269"
BOT_OWNER_ID = None

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=INTENTS)
tree = bot.tree

# Error handler global para comandos slash
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handler global para erros em comandos slash"""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏰ Comando em cooldown! Tente novamente em {error.retry_after:.1f}s",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando!",
            ephemeral=True
        )
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message(
            "❌ Comando não encontrado! Use `/manual` para ver comandos disponíveis.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "❌ Você não atende aos requisitos para usar este comando!",
            ephemeral=True
        )
    else:
        print(f"❌ Erro não tratado no comando {interaction.command.name if interaction.command else 'unknown'}: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Ocorreu um erro ao executar o comando. Tente novamente.\n\n"
                    f"Se o erro persistir, contate o suporte.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Ocorreu um erro ao executar o comando. Tente novamente.",
                    ephemeral=True
                )
        except:
            pass

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS config (
        k TEXT PRIMARY KEY, 
        v TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS filas (
        guild_id INTEGER,
        valor REAL,
        modo TEXT,
        tipo_jogo TEXT DEFAULT 'mob',
        jogadores TEXT,
        msg_id INTEGER,
        criado_em TEXT,
        PRIMARY KEY (guild_id, valor, modo, tipo_jogo)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS fila_mediadores (
        guild_id INTEGER,
        user_id INTEGER,
        adicionado_em TEXT,
        PRIMARY KEY (guild_id, user_id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS partidas (
        id TEXT PRIMARY KEY,
        guild_id INTEGER,
        canal_id INTEGER,
        thread_id INTEGER,
        valor REAL,
        jogador1 INTEGER,
        jogador2 INTEGER,
        mediador INTEGER,
        status TEXT,
        vencedor INTEGER,
        confirmacao_j1 INTEGER DEFAULT 0,
        confirmacao_j2 INTEGER DEFAULT 0,
        sala_id TEXT,
        sala_senha TEXT,
        criado_em TEXT
    )""")