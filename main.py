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
    cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        guild_id INTEGER,
        user_id INTEGER,
        coins REAL DEFAULT 0,
        vitorias INTEGER DEFAULT 0,
        derrotas INTEGER DEFAULT 0,
        PRIMARY KEY (guild_id, user_id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS mediador_pix (
        guild_id INTEGER,
        user_id INTEGER,
        nome_completo TEXT,
        chave_pix TEXT,
        criado_em TEXT,
        PRIMARY KEY (guild_id, user_id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        adicionado_em TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS historico_filas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        valor REAL,
        modo TEXT,
        tipo_jogo TEXT,
        acao TEXT,
        timestamp TEXT
    )""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS fila_participantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        user_id INTEGER,
        valor REAL,
        modo TEXT,
        tipo_jogo TEXT,
        entrada_em TEXT
    )""")
    try:
        cur.execute("""ALTER TABLE filas ADD COLUMN vagas_emu INTEGER DEFAULT 0""")
    except sqlite3.OperationalError:
        pass
    
    try:
        cur.execute("""ALTER TABLE partidas ADD COLUMN estado_sala TEXT DEFAULT NULL""")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("""ALTER TABLE partidas ADD COLUMN sala_update_count INTEGER DEFAULT 0""")
    except sqlite3.OperationalError:
        pass
    
    try:
        cur.execute("""ALTER TABLE partidas ADD COLUMN sala_paga TEXT DEFAULT NULL""")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("""ALTER TABLE logs_partidas ADD COLUMN tipo_fila TEXT DEFAULT '1x1-mob'""")
    except sqlite3.OperationalError:
        pass

    cur.execute("""CREATE TABLE IF NOT EXISTS emoji_config (
        guild_id INTEGER,
        tipo TEXT,
        emoji TEXT,
        PRIMARY KEY (guild_id, tipo)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS contras (
        id TEXT PRIMARY KEY,
        guild_id INTEGER,
        categoria TEXT,
        nome TEXT,
        desafiante_id INTEGER,
        desafiado_id INTEGER,
        valor REAL,
        status TEXT,
        canal_id INTEGER,
        thread_id INTEGER,
        mediador INTEGER,
        confirmacao_j1 INTEGER DEFAULT 0,
        confirmacao_j2 INTEGER DEFAULT 0,
        vencedor INTEGER,
        criado_em TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS servidores (
        guild_id INTEGER PRIMARY KEY,
        nome_dono TEXT,
        ativo INTEGER DEFAULT 1,
        data_registro TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS logs_partidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partida_id TEXT,
        guild_id INTEGER,
        acao TEXT,
        jogador1_id INTEGER,
        jogador2_id INTEGER,
        mediador_id INTEGER,
        valor REAL,
        tipo_fila TEXT DEFAULT '1x1-mob',
        timestamp TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS server_owner_roles (
        guild_id INTEGER PRIMARY KEY,
        role_id INTEGER NOT NULL,
        role_name TEXT,
        definido_por INTEGER,
        data_definicao TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS auto_role (
        guild_id INTEGER PRIMARY KEY,
        role_id INTEGER NOT NULL,
        role_name TEXT,
        definido_por INTEGER,
        data_definicao TEXT
    )""")

    conn.commit()
    conn.close()

def db_set_config(k, v):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO config (k,v) VALUES (?,?)", (k, v))
    conn.commit()
    conn.close()

def db_get_config(k):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT v FROM config WHERE k = ?", (k,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def registrar_log_partida(partida_id, guild_id, acao, j1_id, j2_id, mediador_id=None, valor=0.0, tipo_fila="1x1-mob"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO logs_partidas (partida_id, guild_id, acao, jogador1_id, jogador2_id, mediador_id, valor, tipo_fila, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (partida_id, guild_id, acao, j1_id, j2_id, mediador_id, valor, tipo_fila, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def obter_logs_partidas(guild_id, jogador_id=None, limite=10):
    conn = get_connection()
    cur = conn.cursor()

    if jogador_id:
        cur.execute("""SELECT partida_id, acao, jogador1_id, jogador2_id, mediador_id, valor, tipo_fila, timestamp
                       FROM logs_partidas 
                       WHERE guild_id = ? AND (jogador1_id = ? OR jogador2_id = ?)
                       ORDER BY timestamp DESC LIMIT ?""",
                    (guild_id, jogador_id, jogador_id, limite))
    else:
        cur.execute("""SELECT partida_id, acao, jogador1_id, jogador2_id, mediador_id, valor, tipo_fila, timestamp
                       FROM logs_partidas 
                       WHERE guild_id = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (guild_id, limite))

    rows = cur.fetchall()
    conn.close()
    return rows

async def enviar_log_para_canal(guild, acao, partida_id, j1_id, j2_id, mediador_id=None, valor=0.0, tipo_fila="mob"):
    categoria = None
    for cat in guild.categories:
        if "log" in cat.name.lower():
            categoria = cat
            break

    if not categoria:
        return

    canal_log = None
    mensagem_tipo_log = ""
    if acao == "partida_criada":
        canal_log = discord.utils.get(categoria.channels, name="🔥 • log-criadas")
        mensagem_tipo_log = "**Log-criada**: Salas criadas pelo administrador"
    elif acao == "partida_confirmada":
        canal_log = discord.utils.get(categoria.channels, name="✅ • log-confirmadas")
        mensagem_tipo_log = "**Log-confirmadas**: Filas aceitas por dois jogadores"
    elif acao == "partida_iniciada":
        canal_log = discord.utils.get(categoria.channels, name="🌐 • log-iniciadas")
        mensagem_tipo_log = "**Log-iniciadas**: Filas iniciadas por jogadores"
    elif acao == "partida_finalizada":
        canal_log = discord.utils.get(categoria.channels, name="🏁 • logs-finalizadas")
        mensagem_tipo_log = "**Log-finalizadas**: Salas que o administrador finalizou"
    elif acao == "partida_recusada":
        canal_log = discord.utils.get(categoria.channels, name="❌ • log-recusada")
        mensagem_tipo_log = "**Log-recusada**: Fila recusada por um dos jogadores"

    if not canal_log:
        return

    jogador1 = guild.get_member(j1_id)
    jogador2 = guild.get_member(j2_id)
    mediador = guild.get_member(mediador_id) if mediador_id else None

    nome_j1 = jogador1.display_name if jogador1 else f"Player {j1_id}"
    nome_j2 = jogador2.display_name if jogador2 else f"Player {j2_id}"
    nome_mediador = mediador.display_name if mediador else "Sem mediador"

    timestamp_str = datetime.datetime.utcnow().strftime("%d/%m/%Y %H:%M")

    embed = discord.Embed(
        title=f"📋 {acao.replace('_', ' ').title()}",
        description=f"_{mensagem_tipo_log}_",
        color=0x2f3136
    )
    embed.add_field(name="🆔 Partida", value=partida_id, inline=True)
    embed.add_field(name="💰 Valor", value=fmt_valor(valor), inline=True)
    embed.add_field(name="🎮 Tipo", value=tipo_fila.upper(), inline=True)
    embed.add_field(name="👥 Player 1", value=f"{nome_j1} (<@{j1_id}>)", inline=True)
    embed.add_field(name="👥 Player 2", value=f"{nome_j2} (<@{j2_id}>)", inline=True)
    embed.add_field(name="👨‍⚖️ Mediador", value=f"{nome_mediador}" + (f" (<@{mediador_id}>)" if mediador_id else ""), inline=True)
    embed.set_footer(text=f"Data: {timestamp_str}")

    try:
        await canal_log.send(embed=embed)
    except Exception as e:
        print(f"Erro ao enviar log para canal: {e}")

def verificar_separador_servidor(guild_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT ativo FROM servidores WHERE guild_id = ?", (guild_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None and row[0] == 1

def get_server_owner_role(guild_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT role_id FROM server_owner_roles WHERE guild_id = ?", (guild_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_server_owner_role(guild_id, role_id, role_name, definido_por):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO server_owner_roles (guild_id, role_id, role_name, definido_por, data_definicao)
                       VALUES (?, ?, ?, ?, ?)""",
                    (guild_id, role_id, role_name, definido_por, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_auto_role(guild_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT role_id FROM auto_role WHERE guild_id = ?", (guild_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_auto_role(guild_id, role_id, role_name, definido_por):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT OR REPLACE INTO auto_role (guild_id, role_id, role_name, definido_por, data_definicao)
                   VALUES (?, ?, ?, ?, ?)""",
                (guild_id, role_id, role_name, definido_por, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def remove_auto_role(guild_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM auto_role WHERE guild_id = ?", (guild_id,))
    conn.commit()
    conn.close()

def verificar_pix_mediador(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT chave_pix FROM mediador_pix WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    row = cur.fetchone()
    conn.close()
    return row is not None and row[0] is not None and row[0].strip() != ""

def get_taxa():
    taxa_str = db_get_config("taxa_por_jogador")
    if taxa_str:
        return float(taxa_str)
    return TAXA_POR_JOGADOR

def fmt_valor(v):
    return f"R$ {v:.2f}".replace(".", ",")

def usuario_ensure(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO usuarios (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
    conn.commit()
    conn.close()

def usuario_add_coins(guild_id, user_id, amount):
    usuario_ensure(guild_id, user_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET coins = coins + ? WHERE guild_id = ? AND user_id = ?", (amount, guild_id, user_id))
    conn.commit()
    conn.close()

def usuario_remove_coins(guild_id, user_id, amount):
    usuario_ensure(guild_id, user_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET coins = coins - ? WHERE guild_id = ? AND user_id = ?", (amount, guild_id, user_id))
    conn.commit()
    conn.close()

def usuario_get_coins(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM usuarios WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def usuario_add_vitoria(guild_id, user_id):
    usuario_ensure(guild_id, user_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET vitorias = vitorias + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    conn.commit()
    conn.close()

def usuario_add_derrota(guild_id, user_id):
    usuario_ensure(guild_id, user_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET derrotas = derrotas + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    conn.commit()
    conn.close()

def usuario_get_stats(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT coins, vitorias, derrotas FROM usuarios WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"coins": row[0], "vitorias": row[1], "derrotas": row[2]}
    return {"coins": 0, "vitorias": 0, "derrotas": 0}

def fila_add_jogador(guild_id, valor, modo, user_id, tipo_jogo='mob'):
    conn = sqlite3.connect(DB_FILE, timeout=1.0)
    cur = conn.cursor()
    
    try:
        cur.execute("INSERT OR IGNORE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, ?, ?, '', 0, ?)",
                    (guild_id, valor, modo, tipo_jogo, datetime.datetime.utcnow().isoformat()))
        cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", (guild_id, valor, modo, tipo_jogo))
        row = cur.fetchone()
        jogadores = []
        if row and row[0]:
            jogadores = [int(x) for x in row[0].split(",") if x.strip().isdigit()]
        
        if user_id not in jogadores:
            jogadores.append(user_id)
            cur.execute("INSERT INTO fila_participantes (guild_id, user_id, valor, modo, tipo_jogo, entrada_em) VALUES (?, ?, ?, ?, ?, ?)",
                        (guild_id, user_id, valor, modo, tipo_jogo, datetime.datetime.utcnow().isoformat()))
        
        cur.execute("UPDATE filas SET jogadores = ? WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", 
                    (",".join(str(x) for x in jogadores), guild_id, valor, modo, tipo_jogo))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro em fila_add_jogador: {e}")
    finally:
        conn.close()
    
    return jogadores

def fila_remove_jogador(guild_id, valor, modo, user_id, tipo_jogo='mob'):
    conn = sqlite3.connect(DB_FILE, timeout=1.0)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", (guild_id, valor, modo, tipo_jogo))
        row = cur.fetchone()
        jogadores = []
        if row and row[0]:
            jogadores = [int(x) for x in row[0].split(",") if x.strip().isdigit()]
        
        if user_id in jogadores:
            jogadores.remove(user_id)
        
        cur.execute("UPDATE filas SET jogadores = ? WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", 
                    (",".join(str(x) for x in jogadores) if jogadores else "", guild_id, valor, modo, tipo_jogo))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro em fila_remove_jogador: {e}")
    finally:
        conn.close()
    
    return jogadores

def fila_get_jogadores(guild_id, valor, modo, tipo_jogo='mob'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", (guild_id, valor, modo, tipo_jogo))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        return [int(x) for x in row[0].split(",")]
    return []

def fila_clear(guild_id, valor, modo, tipo_jogo='mob'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE filas SET jogadores = '' WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", (guild_id, valor, modo, tipo_jogo))
    conn.commit()
    conn.close()

def fila_remove_primeiros(guild_id, valor, modo, quantidade=2, tipo_jogo='mob'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", (guild_id, valor, modo, tipo_jogo))
    row = cur.fetchone()
    jogadores = []
    if row and row[0]:
        jogadores = [int(x) for x in row[0].split(",")]

    removidos = jogadores[:quantidade]
    restantes = jogadores[quantidade:]

    cur.execute("UPDATE filas SET jogadores = ? WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", 
                (",".join(str(x) for x in restantes) if restantes else "", guild_id, valor, modo, tipo_jogo))
    conn.commit()
    conn.close()
    return removidos, restantes

def mediador_add(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE, timeout=1.0)
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO fila_mediadores (guild_id, user_id, adicionado_em) VALUES (?, ?, ?)", 
                    (guild_id, user_id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro em mediador_add: {e}")
    finally:
        conn.close()

def mediador_remove(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM fila_mediadores WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    conn.commit()
    conn.close()

def mediador_get_all(guild_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM fila_mediadores WHERE guild_id = ? ORDER BY adicionado_em ASC", (guild_id,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def mediador_get_next(guild_id):
    mediadores = mediador_get_all(guild_id)
    if mediadores:
        return mediadores[0]
    return None

def mediador_rotacionar(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE, timeout=1.0)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE fila_mediadores SET adicionado_em = ? WHERE guild_id = ? AND user_id = ?", 
                    (datetime.datetime.utcnow().isoformat(), guild_id, user_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro em mediador_rotacionar: {e}")
    finally:
        conn.close()

def admin_add(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO admins (user_id, adicionado_em) VALUES (?, ?)", 
                (user_id, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def admin_remove(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_admin(user_id, guild=None, member=None):
    if member and member.guild:
        server_owner_role_id = get_server_owner_role(member.guild.id)
        if server_owner_role_id:
            role_ids = [r.id for r in member.roles]
            if server_owner_role_id in role_ids:
                return True

    cargo_dono_id = db_get_config("cargo_dono_id")
    if cargo_dono_id and member:
        role_ids = [r.id for r in member.roles]
        if int(cargo_dono_id) in role_ids:
            return True

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def is_aux_permitido(member):
    aux_role_id = db_get_config("aux_role_id")
    if not aux_role_id:
        return True

    if member:
        role_ids = [r.id for r in member.roles]
        if int(aux_role_id) in role_ids:
            return True

    return False

def registrar_historico_fila(guild_id, valor, modo, tipo_jogo, acao):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO historico_filas (guild_id, valor, modo, tipo_jogo, acao, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (guild_id, valor, modo, tipo_jogo, acao, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_estatisticas_filas(guild_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM historico_filas WHERE guild_id = ? AND acao = 'criada'", (guild_id,))
    total_criadas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT guild_id || valor || modo || tipo_jogo) FROM filas WHERE guild_id = ? AND jogadores != ''", (guild_id,))
    filas_ativas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM historico_filas WHERE guild_id = ? AND acao = 'finalizada'", (guild_id,))
    filas_finalizadas = cur.fetchone()[0]

    conn.close()

    return {
        "criadas": total_criadas,
        "ativas": filas_ativas,
        "finalizadas": filas_finalizadas
    }

def get_emoji_custom(guild_id, tipo):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT emoji FROM emoji_config WHERE guild_id = ? AND tipo = ?", (guild_id, tipo))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_emoji_custom(guild_id, tipo, emoji):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO emoji_config (guild_id, tipo, emoji) VALUES (?, ?, ?)", 
                (guild_id, tipo, emoji))
    conn.commit()
    conn.close()

def get_emoji_fila(guild_id, tipo_fila, tipo_botao):
    chave = f"{tipo_fila}_{tipo_botao}"
    return get_emoji_custom(guild_id, chave)

def set_emoji_fila(guild_id, tipo_fila, tipo_botao, emoji):
    chave = f"{tipo_fila}_{tipo_botao}"
    set_emoji_custom(guild_id, chave, emoji)

def requer_servidor_registrado():
    def decorator(func):
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if not verificar_separador_servidor(interaction.guild.id):
                await interaction.response.send_message(
                    "⛔ **Servidor não registrado!**\n\n"
                    "Este servidor precisa estar registrado para usar o Bot Zeus.\n"
                    "Entre em contato com o owner do bot (emanoel7269) para registrar seu servidor com o comando `/separador_de_servidor`.",
                    ephemeral=True
                )
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

class ConfirmarEntradaView(View):
    def __init__(self, guild_id: int, valor: float, modo: str, canal):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.valor = valor
        self.modo = modo
        self.canal = canal

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        jogadores = fila_add_jogador(self.guild_id, self.valor, self.modo, user_id)

        await interaction.response.edit_message(
            content=f"✅ Você entrou na fila Gel (mob1x1) {self.modo.capitalize()} de {fmt_valor(self.valor)}! ({len(jogadores)}/2 jogadores)",
            view=None
        )

        await atualizar_msg_fila(self.canal, self.valor)

        if len(jogadores) >= 2:
            fila_remove_primeiros(self.guild_id, self.valor, self.modo, 2)
            await criar_partida(interaction.guild, jogadores[0], jogadores[1], self.valor, self.modo)
            await atualizar_msg_fila(self.canal, self.valor)

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Entrada na fila cancelada!",
            view=None
        )

class FilaView(View):
    def __init__(self, valor: float, guild_id: int = None, tipo_jogo: str = 'mob'):
        super().__init__(timeout=None)
        self.valor = valor
        self.guild_id = guild_id
        self.tipo_jogo = tipo_jogo

        emoji_normal = get_emoji_custom(guild_id, "gel_normal") if guild_id else None
        emoji_infinito = get_emoji_custom(guild_id, "gel_infinito") if guild_id else None
        emoji_sair = get_emoji_custom(guild_id, "sair") if guild_id else None
        emoji_arquiteto = get_emoji_custom(guild_id, "chame_arquiteto") if guild_id else None

        self.btn_normal = Button(label="Gel Normal", style=discord.ButtonStyle.primary, custom_id="gel_normal", emoji=emoji_normal)
        self.btn_normal.callback = self.gel_normal
        self.add_item(self.btn_normal)

        self.btn_infinito = Button(label="Gel Infinito", style=discord.ButtonStyle.primary, custom_id="gel_infinito", emoji=emoji_infinito)
        self.btn_infinito.callback = self.gel_infinito
        self.add_item(self.btn_infinito)

        if emoji_arquiteto:
            self.btn_arquiteto = Button(label="Chame o Arquiteto", style=discord.ButtonStyle.secondary, custom_id="chame_arquiteto", emoji=emoji_arquiteto)
            self.btn_arquiteto.callback = self.chame_arquiteto
            self.add_item(self.btn_arquiteto)

        self.btn_sair = Button(label="Sair da fila", style=discord.ButtonStyle.danger, custom_id="sair_fila", emoji=emoji_sair)
        self.btn_sair.callback = self.sair_fila
        self.add_item(self.btn_sair)

    async def gel_normal(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.\n"
                "Entre em contato com o owner do bot (emanoel7269) para registrar seu servidor.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        mediadores = mediador_get_all(guild_id)
        if not mediadores:
            await interaction.response.send_message(
                "❌ Não há mediadores disponíveis no momento! @player",
                ephemeral=True
            )
            return
        user_id = interaction.user.id
        jogadores = fila_add_jogador(guild_id, self.valor, "normal", user_id, self.tipo_jogo)

        await interaction.response.defer()

        await atualizar_msg_fila(interaction.channel, self.valor, self.tipo_jogo)

        if len(jogadores) >= 2:
            fila_remove_primeiros(guild_id, self.valor, "normal", 2, self.tipo_jogo)
            await criar_partida_mob(interaction.guild, jogadores[0], jogadores[1], self.valor, "normal")
            await atualizar_msg_fila(interaction.channel, self.valor, self.tipo_jogo)

    async def gel_infinito(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.\n"
                "Entre em contato com o owner do bot (emanoel7269) para registrar seu servidor.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        mediadores = mediador_get_all(guild_id)
        if not mediadores:
            await interaction.response.send_message(
                "❌ Não há mediadores disponíveis no momento! Aguarde até que um mediador entre em serviço.",
                ephemeral=True
            )
            return
        user_id = interaction.user.id
        jogadores = fila_add_jogador(guild_id, self.valor, "infinito", user_id, self.tipo_jogo)

        await interaction.response.defer()

        await atualizar_msg_fila(interaction.channel, self.valor, self.tipo_jogo)

        if len(jogadores) >= 2:
            fila_remove_primeiros(guild_id, self.valor, "infinito", 2, self.tipo_jogo)
            await criar_partida_mob(interaction.guild, jogadores[0], jogadores[1], self.valor, "infinito")
            await atualizar_msg_fila(interaction.channel, self.valor, self.tipo_jogo)

    async def chame_arquiteto(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "🏛️ Você chamou o Arquiteto! Um administrador será notificado.",
            ephemeral=True
        )

    async def sair_fila(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        jogadores_normal = fila_get_jogadores(guild_id, self.valor, "normal", self.tipo_jogo)
        jogadores_infinito = fila_get_jogadores(guild_id, self.valor, "infinito", self.tipo_jogo)

        estava_na_fila = user_id in jogadores_normal or user_id in jogadores_infinito

        fila_remove_jogador(guild_id, self.valor, "normal", user_id, self.tipo_jogo)
        fila_remove_jogador(guild_id, self.valor, "infinito", user_id, self.tipo_jogo)

        if not estava_na_fila:
            await interaction.response.send_message(
                "⚠️ Você não está nesta fila!",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        await atualizar_msg_fila(interaction.channel, self.valor, self.tipo_jogo)

async def atualizar_msg_fila(canal, valor, tipo_jogo='mob'):
    guild_id = canal.guild.id
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT msg_id FROM filas WHERE guild_id = ? AND valor = ? AND tipo_jogo = ? AND msg_id > 0 ORDER BY msg_id DESC LIMIT 1", (guild_id, valor, tipo_jogo))
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return

    try:
        msg = await canal.fetch_message(row[0])
        jogadores_normal = fila_get_jogadores(guild_id, valor, "normal", tipo_jogo)
        jogadores_infinito = fila_get_jogadores(guild_id, valor, "infinito", tipo_jogo)

        if tipo_jogo == 'emu':
            titulo = "1v1 Emulador"
            descricao_modo = "1v1 Emulador"
        else:
            titulo = "1v1 Mobile"
            descricao_modo = "1v1 Mobile"

        total_jogadores = len(jogadores_normal) + len(jogadores_infinito)
        jogadores_text = "Ninguém" if total_jogadores == 0 else f"{total_jogadores} na fila"

        embed = discord.Embed(
            title=titulo,
            description=f"**Modo**\n{descricao_modo}\n\n**Valor**\n{fmt_valor(valor)}\n\n**Jogadores**\n{jogadores_text}",
            color=0x2f3136
        )

        # Prioriza foto configurada, depois foto do servidor
        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        if jogadores_normal:
            normal_text = "\n".join([f"<@{uid}>" for uid in jogadores_normal])
            embed.add_field(name="🔴 Gel Normal", value=normal_text, inline=True)
        else:
            embed.add_field(name="🔴 Gel Normal", value="Nenhum jogador", inline=True)

        if jogadores_infinito:
            infinito_text = "\n".join([f"<@{uid}>" for uid in jogadores_infinito])
            embed.add_field(name="🔵 Gel Infinito", value=infinito_text, inline=True)
        else:
            embed.add_field(name="🔵 Gel Infinito", value="Nenhum jogador", inline=True)

        await msg.edit(embed=embed)
    except Exception as e:
        print(f"⚠️ Erro ao atualizar mensagem da fila: {e}")

class FilaMobView(View):
    def __init__(self, valor: float, tipo_fila: str, tipo_jogo: str = 'mob', guild_id: int = None):
        super().__init__(timeout=None)
        self.valor = valor
        self.tipo_fila = tipo_fila
        self.tipo_jogo = tipo_jogo

        emoji_entrar = get_emoji_fila(guild_id, tipo_fila, "entrar") if guild_id else None
        emoji_sair = get_emoji_fila(guild_id, tipo_fila, "sair") if guild_id else None

        self.btn_entrar = Button(label="Entrar", style=discord.ButtonStyle.success, custom_id="entrar_fila_mob", emoji=emoji_entrar)
        self.btn_entrar.callback = self.entrar_fila
        self.add_item(self.btn_entrar)

        self.btn_sair = Button(label="Sair da fila", style=discord.ButtonStyle.danger, custom_id="sair_fila_mob", emoji=emoji_sair)
        self.btn_sair.callback = self.sair_fila
        self.add_item(self.btn_sair)

    async def entrar_fila(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.\n"
                "Entre em contato com o owner do bot (emanoel7269) para registrar seu servidor.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        mediadores = mediador_get_all(guild_id)
        if not mediadores:
            await interaction.response.send_message(
                "❌ Não há mediadores disponíveis no momento! Aguarde até que um mediador entre em serviço.",
                ephemeral=True
            )
            return
        user_id = interaction.user.id
        jogadores = fila_add_jogador(guild_id, self.valor, self.tipo_fila, user_id, self.tipo_jogo)

        await interaction.response.defer()

        await atualizar_msg_fila_mob(interaction.channel, self.valor, self.tipo_fila, self.tipo_jogo)

        if len(jogadores) >= 2:
            fila_remove_primeiros(guild_id, self.valor, self.tipo_fila, 2, self.tipo_jogo)
            await criar_partida_mob(interaction.guild, jogadores[0], jogadores[1], self.valor, self.tipo_fila)
            await atualizar_msg_fila_mob(interaction.channel, self.valor, self.tipo_fila, self.tipo_jogo)

    async def sair_fila(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        jogadores = fila_get_jogadores(guild_id, self.valor, self.tipo_fila, self.tipo_jogo)

        if user_id not in jogadores:
            await interaction.response.send_message(
                "⚠️ Você não está nesta fila!",
                ephemeral=True
            )
            return

        fila_remove_jogador(guild_id, self.valor, self.tipo_fila, user_id, self.tipo_jogo)

        await interaction.response.defer()

        await atualizar_msg_fila_mob(interaction.channel, self.valor, self.tipo_fila, self.tipo_jogo)

async def atualizar_msg_fila_mob(canal, valor, tipo_fila, tipo_jogo='mob'):
    guild_id = canal.guild.id
    conn = sqlite3.connect(DB_FILE, timeout=1.0)
    cur = conn.cursor()
    cur.execute("SELECT msg_id FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ? LIMIT 1", (guild_id, valor, tipo_fila, tipo_jogo))
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return

    try:
        msg = await asyncio.wait_for(canal.fetch_message(row[0]), timeout=1.0)
        jogadores = fila_get_jogadores(guild_id, valor, tipo_fila, tipo_jogo)

        if tipo_jogo == 'emu':
            titulo = "Filas Emulador"
            tipo_texto = "EMULADOR"
        else:
            titulo = "Filas Mobile"
            tipo_texto = "MOBILE"

        embed = discord.Embed(
            title=titulo,
            description=f"🎮 **Modo**\n{tipo_fila.upper()} {tipo_texto}\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        if jogadores:
            jogadores_text = "\n".join([f"<@{uid}>" for uid in jogadores])
            embed.add_field(name="🎮 Jogadores na Fila", value=jogadores_text, inline=False)
        else:
            embed.add_field(name="🎮 Jogadores na Fila", value="Nenhum jogador", inline=False)

        await msg.edit(embed=embed)
    except asyncio.TimeoutError:
        print(f"⚠️ Timeout ao atualizar mensagem da fila")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar mensagem da fila: {e}")

class FilaMistoView(View):
    def __init__(self, valor: float, tipo_fila: str):
        super().__init__(timeout=None)
        self.valor = valor
        self.tipo_fila = tipo_fila

        if tipo_fila == "2x2-misto":
            btn1 = Button(label="1 Emu", style=discord.ButtonStyle.secondary, custom_id=f"misto_1emu_{valor}", row=0)
            btn1.callback = lambda i: self.entrar_fila_misto(i, 1)
            self.add_item(btn1)
        elif tipo_fila == "3x3-misto":
            btn1 = Button(label="1 Emu", style=discord.ButtonStyle.secondary, custom_id=f"misto_1emu_{valor}", row=0)
            btn1.callback = lambda i: self.entrar_fila_misto(i, 1)
            self.add_item(btn1)
            btn2 = Button(label="2 Emu", style=discord.ButtonStyle.secondary, custom_id=f"misto_2emu_{valor}", row=0)
            btn2.callback = lambda i: self.entrar_fila_misto(i, 2)
            self.add_item(btn2)
        elif tipo_fila == "4x4-misto":
            btn1 = Button(label="1 Emu", style=discord.ButtonStyle.secondary, custom_id=f"misto_1emu_{valor}", row=0)
            btn1.callback = lambda i: self.entrar_fila_misto(i, 1)
            self.add_item(btn1)
            btn2 = Button(label="2 Emu", style=discord.ButtonStyle.secondary, custom_id=f"misto_2emu_{valor}", row=0)
            btn2.callback = lambda i: self.entrar_fila_misto(i, 2)
            self.add_item(btn2)
            btn3 = Button(label="3 Emu", style=discord.ButtonStyle.secondary, custom_id=f"misto_3emu_{valor}", row=0)
            btn3.callback = lambda i: self.entrar_fila_misto(i, 3)
            self.add_item(btn3)

        btn_sair = Button(label="Sair da fila❌️", style=discord.ButtonStyle.danger, custom_id=f"sair_misto_{valor}", row=1)
        btn_sair.callback = self.sair_fila_misto
        self.add_item(btn_sair)

    async def entrar_fila_misto(self, interaction: discord.Interaction, vagas_emu: int):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.\n"
                "Entre em contato com o owner do bot (emanoel7269) para registrar seu servidor.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        mediadores = mediador_get_all(guild_id)
        if not mediadores:
            await interaction.response.send_message(
                "❌ Não há mediadores disponíveis no momento! Aguarde até que um mediador entre em serviço.",
                ephemeral=True
            )
            return
        user_id = interaction.user.id

        conn = get_connection()
        cur = conn.cursor()
        modo_fila = f"{self.tipo_fila}_{vagas_emu}emu"
        cur.execute("INSERT OR IGNORE INTO filas (guild_id, valor, modo, tipo_jogo, vagas_emu, jogadores, msg_id, criado_em) VALUES (?, ?, ?, 'misto', ?, '', 0, ?)",
                    (guild_id, self.valor, modo_fila, vagas_emu, datetime.datetime.utcnow().isoformat()))
        cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = 'misto'", (guild_id, self.valor, modo_fila))
        row = cur.fetchone()
        jogadores = []
        if row and row[0]:
            jogadores = [int(x) for x in row[0].split(",")]
        if user_id not in jogadores:
            jogadores.append(user_id)
        cur.execute("UPDATE filas SET jogadores = ? WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = 'misto'", 
                    (",".join(str(x) for x in jogadores), guild_id, self.valor, modo_fila))
        conn.commit()
        conn.close()

        await interaction.response.defer()

        await atualizar_msg_fila_misto(interaction.channel, self.valor, self.tipo_fila)

        if len(jogadores) >= 2:
            fila_remove_primeiros(guild_id, self.valor, modo_fila, 2, 'misto')
            await criar_partida_mob(interaction.guild, jogadores[0], jogadores[1], self.valor, self.tipo_fila)
            registrar_historico_fila(guild_id, self.valor, modo_fila, "misto", "finalizada")
            await atualizar_msg_fila_misto(interaction.channel, self.valor, self.tipo_fila)

    async def sair_fila_misto(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        for vagas in [1, 2, 3]:
            modo_fila = f"{self.tipo_fila}_{vagas}emu"
            fila_remove_jogador(guild_id, self.valor, modo_fila, user_id, 'misto')

        await interaction.response.defer()
        await atualizar_msg_fila_misto(interaction.channel, self.valor, self.tipo_fila)

async def atualizar_msg_fila_misto(canal, valor, tipo_fila):
    guild_id = canal.guild.id
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT msg_id FROM filas WHERE guild_id = ? AND valor = ? AND modo LIKE ? AND tipo_jogo = 'misto' LIMIT 1", 
                (guild_id, valor, f"{tipo_fila}%"))
    row = cur.fetchone()

    if not row or not row[0]:
        conn.close()
        return

    msg_id = row[0]

    filas_info = []
    total_jogadores = 0

    for vagas in [1, 2, 3]:
        modo_fila = f"{tipo_fila}_{vagas}emu"
        cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = 'misto'", 
                    (guild_id, valor, modo_fila))
        fila_row = cur.fetchone()
        if fila_row and fila_row[0]:
            jogadores = [int(x) for x in fila_row[0].split(",")]
            if jogadores:
                filas_info.append({
                    "vagas": vagas,
                    "jogadores": jogadores
                })
                total_jogadores += len(jogadores)

    conn.close()

    try:
        msg = await canal.fetch_message(msg_id)

        embed = discord.Embed(
            title="Filas Misto",
            description=f"🎮 **Modo**\n{tipo_fila.upper()}\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        # Prioriza foto configurada, depois foto do servidor
        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        if filas_info:
            for fila in filas_info:
                vagas_emu = fila["vagas"]
                jogadores_ids = fila["jogadores"]
                jogadores_text = "\n".join([f"<@{uid}>" for uid in jogadores_ids])
                embed.add_field(
                    name=f"🎮 {vagas_emu} Emulador{'es' if vagas_emu > 1 else ''}",
                    value=jogadores_text,
                    inline=False
                )
        else:
            embed.add_field(name="👥 Jogadores", value="Nenhum jogador na fila", inline=False)

        await msg.edit(embed=embed)
    except Exception as e:
        print(f"⚠️ Erro ao atualizar mensagem da fila: {e}")

class ConfirmarPartidaView(View):
    def __init__(self, partida_id: str, jogador1_id: int, jogador2_id: int):
        super().__init__(timeout=None)
        self.partida_id = partida_id
        self.jogador1_id = jogador1_id
        self.jogador2_id = jogador2_id

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id not in [self.jogador1_id, self.jogador2_id]:
            await interaction.response.send_message("❌ Você não faz parte desta partida!", ephemeral=True)
            return

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT confirmacao_j1, confirmacao_j2 FROM partidas WHERE id = ?", (self.partida_id,))
        row = cur.fetchone()

        if not row:
            await interaction.response.send_message("❌ Partida não encontrada!", ephemeral=True)
            conn.close()
            return

        conf_j1, conf_j2 = row

        if user_id == self.jogador1_id:
            if conf_j1 == 1:
                await interaction.response.send_message("❌ Você já confirmou esta partida!", ephemeral=True)
                conn.close()
                return
            cur.execute("UPDATE partidas SET confirmacao_j1 = 1 WHERE id = ?", (self.partida_id,))
        else:
            if conf_j2 == 1:
                await interaction.response.send_message("❌ Você já confirmou esta partida!", ephemeral=True)
                conn.close()
                return
            cur.execute("UPDATE partidas SET confirmacao_j2 = 1 WHERE id = ?", (self.partida_id,))

        conn.commit()

        cur.execute("SELECT confirmacao_j1, confirmacao_j2, mediador, valor, guild_id FROM partidas WHERE id = ?", (self.partida_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            await interaction.response.send_message("❌ Partida não encontrada!", ephemeral=True)
            return

        conf_j1, conf_j2, mediador_id, valor, guild_id_partida = row

        await interaction.response.send_message("✅ Confirmação registrada!", ephemeral=True)

        if user_id == self.jogador1_id:
            if conf_j2 == 0:
                await interaction.channel.send(f"✅ <@{self.jogador1_id}> confirmou a partida! Aguardando <@{self.jogador2_id}> confirmar...")
        else:
            if conf_j1 == 0:
                await interaction.channel.send(f"✅ <@{self.jogador2_id}> confirmou a partida! Aguardando <@{self.jogador1_id}> confirmar...")

        if conf_j1 == 1 and conf_j2 == 1:
            print(f"🎮 AMBOS CONFIRMARAM - Partida {self.partida_id}")
            
            # ❌ Remover botões da mensagem de confirmação
            try:
                await interaction.message.edit(view=None)
                print(f"✅ Botões removidos da mensagem de confirmação")
            except Exception as e:
                print(f"⚠️ Erro ao remover botões: {e}")
            
            # 📦 Busca dados da partida
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT numero_topico, canal_id, thread_id, guild_id
                FROM partidas WHERE id = ?
            """, (self.partida_id,))
            partida_row = cur.fetchone()
            
            pix_row = None
            
            # ✅ CORREÇÕES CRÍTICAS:
            # 1. Extrair guild_id correto da partida
            topico_guild_id = None
            if partida_row:
                numero_topico, canal_id, thread_id, topico_guild_id = partida_row
            
            # 2. Converter mediador_id para INT (estava como STRING)
            try:
                mediador_id = int(mediador_id) if mediador_id else 0
            except (ValueError, TypeError):
                mediador_id = 0
            
            print(f"\n========== DEBUG PIX COMPLETO ==========")
            print(f"1️⃣ mediador_id={mediador_id}, tipo={type(mediador_id)}")
            print(f"2️⃣ valor={valor}")
            print(f"3️⃣ topico_guild_id={topico_guild_id}")
            
            # Buscar PIX do mediador (otimizado)
            if mediador_id > 0 and topico_guild_id:
                print(f"4️⃣ Buscando PIX: guild_id={topico_guild_id}, user_id={mediador_id}")
                
                # Query otimizada - traz apenas o necessário
                cur.execute("""
                    SELECT nome_completo, chave_pix 
                    FROM mediador_pix 
                    WHERE guild_id = ? AND user_id = ?
                    LIMIT 1
                """, (topico_guild_id, mediador_id))
                pix_row = cur.fetchone()
                
                if pix_row:
                    # Limpar espaços em branco da chave PIX
                    pix_row = (pix_row[0].strip(), pix_row[1].strip())
                    print(f"5️⃣ PIX ENCONTRADO! Nome: {pix_row[0]}, Chave: {pix_row[1][:10]}...")
                else:
                    print(f"5️⃣ PIX NÃO ENCONTRADO para guild={topico_guild_id}, user={mediador_id}")
                    pix_row = None
            else:
                print(f"⚠️ Mediador inválido ou guild_id ausente: mediador_id={mediador_id}, topico_guild_id={topico_guild_id}")
                pix_row = None
            
            print(f"========================================\n")
            conn.close()

            # 🔄 RENOMEIA CANAL PARA mobile-X
            print(f"Renomeando canal...")
            if partida_row:
                numero_topico, canal_id, thread_id, topico_guild_id = partida_row
                print(f"  numero_topico={numero_topico}, canal_id={canal_id}, thread_id={thread_id}, topico_guild_id={topico_guild_id}")
                
                thread_id = int(thread_id) if thread_id else 0
                canal_id = int(canal_id) if canal_id else 0

                try:
                    channel = None
                    if thread_id > 0:
                        channel = await interaction.guild.fetch_channel(thread_id)
                        print(f"  Fetched thread: {channel}")
                    elif canal_id > 0:
                        channel = await interaction.guild.fetch_channel(canal_id)
                        print(f"  Fetched canal: {channel}")
                    
                    if channel:
                        await channel.edit(name=f"mobile-{numero_topico}")
                        print(f"✅ Renomeado para: mobile-{numero_topico}")
                except Exception as e:
                    print(f"❌ Erro ao renomear: {e}")
                    import traceback
                    traceback.print_exc()

            # 💰 ENVIA PIX (se mediador tiver dados)
            print(f"\n========== DEBUG PIX COMPLETO ==========")
            print(f"1️⃣ mediador_id={mediador_id}, tipo={type(mediador_id)}")
            print(f"2️⃣ pix_row={pix_row}, tipo={type(pix_row)}")
            print(f"3️⃣ bool(mediador_id)={bool(mediador_id)}")
            print(f"4️⃣ mediador_id > 0 = {mediador_id > 0 if mediador_id else 'N/A'}")
            print(f"========================================\n")
            
            if mediador_id and mediador_id > 0 and pix_row:
                try:
                    # Garantir que não tem espaços
                    nome_clean = pix_row[0].strip()
                    chave_clean = pix_row[1].strip()
                    
                    print(f"✅ Condição atendida: enviando PIX...")
                    print(f"  - Nome: {nome_clean}")
                    print(f"  - Chave PIX: {chave_clean}")
                    print(f"  - Valor original: {valor}")
                    
                    taxa = get_taxa()
                    print(f"  - Taxa: {taxa}")
                    valor_com_taxa = valor + taxa
                    print(f"  - Valor com taxa: {valor_com_taxa}")
                    
                    view_pix = CopiarCodigoPIXView(chave_clean, chave_clean)
                    print(f"  - Enviando PIX para canal...")
                    await interaction.channel.send(f"💰 **Valor a pagar:** {fmt_valor(valor_com_taxa)}\n(Taxa de {fmt_valor(taxa)} incluída)\n\n{chave_clean}", view=view_pix)
                    print(f"✅ PIX ENVIADO COM SUCESSO!")
                except Exception as e:
                    print(f"❌ ERRO AO ENVIAR PIX: {e}")
                    import traceback
                    traceback.print_exc()
            elif mediador_id and mediador_id > 0 and not pix_row:
                # Mediador não configurou PIX ainda
                print(f"⚠️ Mediador encontrado mas SEM PIX configurado: mediador_id={mediador_id}")
                await interaction.channel.send(
                    f"⚠️ <@{mediador_id}> - **Você ainda não configurou seu PIX!**\n\n"
                    f"Use o comando `/pixmed` para configurar sua chave PIX e habilitar pagamentos automáticos."
                )
            else:
                print(f"⚠️ PIX NÃO ENVIADO:")
                print(f"   mediador_id={mediador_id}")
                print(f"   mediador_id > 0 = {mediador_id > 0 if mediador_id else 'FALSE'}")
                print(f"   pix_row={pix_row}")

            # 📋 MENU DO MEDIADOR - SEMPRE ENVIADO
            print(f"Enviando Menu Mediador... mediador_id={mediador_id}")
            try:
                print(f"  1. Criando embed...")
                embed_menu = discord.Embed(
                    title="Menu Mediador",
                    description=f"🎮 **Player 1:** <@{self.jogador1_id}>\n🎮 **Player 2:** <@{self.jogador2_id}>",
                    color=0x2f3136
                )
                print(f"  2. Criando view...")
                view_menu = MenuMediadorView(self.partida_id)
                print(f"  3. Enviando mensagem...")
                msg = await interaction.channel.send(embed=embed_menu, view=view_menu)
                print(f"✅ Menu Mediador enviado! msg_id={msg.id}")
            except Exception as e:
                print(f"❌ Erro ao enviar Menu: {e}")
                import traceback
                traceback.print_exc()
            
            # 🎮 ACIONAR SISTEMA DE SALA POR TEXTO
            try:
                if mediador_id and mediador_id > 0:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE partidas SET estado_sala = 'aguardando_id' WHERE id = ?", (self.partida_id,))
                    conn.commit()
                    conn.close()
                    await interaction.channel.send(f"<@{mediador_id}> - Digite o ID da sala (6-13 dígitos) e a senha (1-4 dígitos) no chat:")
            except Exception as e:
                print(f"⚠️ Erro ao iniciar sistema de sala: {e}")

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        if user_id not in [self.jogador1_id, self.jogador2_id]:
            await interaction.response.send_message("❌ Você não faz parte desta partida!", ephemeral=True)
            return

        await interaction.response.send_message("❌ Você recusou a partida! O canal será fechado.", ephemeral=True)

        await interaction.channel.send(f"❌ <@{user_id}> recusou a partida. Canal será fechado em 2 segundos...")

        await asyncio.sleep(5)
        await interaction.channel.delete()

async def criar_partida(guild, j1_id, j2_id, valor, modo):
    canal_id = db_get_config("canal_partidas_id")
    if not canal_id:
        return

    canal = guild.get_channel(int(canal_id))
    if not canal:
        return

    partida_id = str(random.randint(100000, 9999999))

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.get_member(j1_id): discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.get_member(j2_id): discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    canal_partida = await guild.create_text_channel(
        f"aguardando-{partida_id}",
        category=canal.category,
        overwrites=overwrites
    )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO partidas (id, guild_id, topico_id, thread_id, valor, jogador1, jogador2, status, criado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmacao', ?)""",
                (partida_id, guild.id, canal_partida.id, 0, valor, j1_id, j2_id, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    mediador_id = mediador_get_next(guild.id)
    if mediador_id:
        mediador_rotacionar(guild.id, mediador_id)

        mediador = guild.get_member(mediador_id)
        if mediador:
            await canal_partida.set_permissions(mediador, read_messages=True, send_messages=True)

            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE partidas SET mediador = ? WHERE id = ?", (mediador_id, partida_id))
            conn.commit()
            conn.close()

    cargos_str = db_get_config("cargos_mencionar")
    mencoes = f"<@{j1_id}> <@{j2_id}>"
    if cargos_str:
        cargos_ids = cargos_str.split(",")
        for cargo_id in cargos_ids:
            mencoes += f" <@&{cargo_id}>"
    if mediador_id:
        mencoes += f" <@{mediador_id}>"

    embed = discord.Embed(
        title="🎮 Partida Encontrada!",
        description=f"**Modo:** 1v1 Mobile - {modo.capitalize()}\n**Valor:** {fmt_valor(valor)}\n\n**Jogadores:**\n<@{j1_id}>\n<@{j2_id}>",
        color=0x2f3136
    )

    if mediador_id:
        embed.add_field(name="👨‍⚖️ Mediador", value=f"<@{mediador_id}>", inline=False)

    embed.add_field(name="⚠️ Atenção", value="Ambos os jogadores devem confirmar a partida clicando em ✅ Confirmar", inline=False)

    view = ConfirmarPartidaView(partida_id, j1_id, j2_id)
    await canal_partida.send(mencoes, embed=embed, view=view)

    registrar_log_partida(partida_id, guild.id, "partida_criada", j1_id, j2_id, mediador_id, valor, f"1x1-{modo}")
    await enviar_log_para_canal(guild, "partida_criada", partida_id, j1_id, j2_id, mediador_id, valor, modo)

async def criar_partida_mob(guild, j1_id, j2_id, valor, tipo_fila):
    canal_id = db_get_config("canal_partidas_id")
    if not canal_id:
        return

    canal = guild.get_channel(int(canal_id))
    if not canal:
        return

    partida_id = str(random.randint(100000, 9999999))
    usar_threads = db_get_config("usar_threads")

    # Contador de tópicos criados
    contador_topicos = db_get_config("contador_topicos")
    if not contador_topicos:
        contador_topicos = "1"
    numero_topico = int(contador_topicos)
    db_set_config("contador_topicos", str(numero_topico + 1))

    if usar_threads == "true":
        thread_name = f"aguardando-{numero_topico}"
        thread = await canal.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread,
            invitable=False
        )

        jogador1 = guild.get_member(j1_id)
        jogador2 = guild.get_member(j2_id)
        if jogador1:
            await thread.add_user(jogador1)
        if jogador2:
            await thread.add_user(jogador2)

        canal_ou_thread_id = thread.id
        thread_id = thread.id
        canal_partida = thread
    else:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.get_member(j1_id): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_member(j2_id): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        canal_partida = await guild.create_text_channel(
            f"aguardando-{numero_topico}",
            category=canal.category,
            overwrites=overwrites
        )
        canal_ou_thread_id = canal_partida.id
        thread_id = 0

    conn = get_connection()
    cur = conn.cursor()

    # Adiciona coluna numero_topico se não existir
    try:
        cur.execute("ALTER TABLE partidas ADD COLUMN numero_topico INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cur.execute("""INSERT INTO partidas (id, guild_id, canal_id, thread_id, valor, jogador1, jogador2, status, numero_topico, criado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmacao', ?, ?)""",
                (partida_id, guild.id, canal_ou_thread_id, thread_id, valor, j1_id, j2_id, numero_topico, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    mediador_id = mediador_get_next(guild.id)
    if mediador_id:
        mediador_rotacionar(guild.id, mediador_id)

        mediador = guild.get_member(mediador_id)
        if mediador:
            if usar_threads == "true":
                await canal_partida.add_user(mediador)
            else:
                await canal_partida.set_permissions(mediador, read_messages=True, send_messages=True)

            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE partidas SET mediador = ? WHERE id = ?", (mediador_id, partida_id))
            conn.commit()
            conn.close()

    cargos_str = db_get_config("cargos_mencionar")
    mencoes = f"<@{j1_id}> <@{j2_id}>"
    if cargos_str:
        cargos_ids = cargos_str.split(",")
        for cargo_id in cargos_ids:
            mencoes += f" <@&{cargo_id}>"
    if mediador_id:
        mencoes += f" <@{mediador_id}>"

    embed = discord.Embed(
        title="🎮 Partida Encontrada!",
        description=f"**Modo:** {tipo_fila.upper()} Mobile\n**Valor:** {fmt_valor(valor)}\n\n**Jogadores:**\n<@{j1_id}>\n<@{j2_id}>",
        color=0x2f3136
    )

    if mediador_id:
        embed.add_field(name="👨‍⚖️ Mediador", value=f"<@{mediador_id}>", inline=False)

    embed.add_field(name="⚠️ Atenção", value="Ambos os jogadores devem confirmar a partida clicando em ✅ Confirmar", inline=False)

    view = ConfirmarPartidaView(partida_id, j1_id, j2_id)
    await canal_partida.send(mencoes, embed=embed, view=view)

    registrar_log_partida(partida_id, guild.id, "partida_criada", j1_id, j2_id, mediador_id, valor, f"1x1-{tipo_fila}")
    await enviar_log_para_canal(guild, "partida_criada", partida_id, j1_id, j2_id, mediador_id, valor, tipo_fila)

class CopiarChavePIXView(View):
    def __init__(self, chave_pix):
        super().__init__(timeout=None)
        self.chave_pix = chave_pix

    @discord.ui.button(label="Copiar PIX", style=discord.ButtonStyle.primary, emoji="💰")
    async def copiar_pix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{self.chave_pix}", ephemeral=True)

class CopiarCodigoPIXView(View):
    def __init__(self, codigo_pix, chave_pix):
        super().__init__(timeout=None)
        self.codigo_pix = codigo_pix
        self.chave_pix = chave_pix

    @discord.ui.button(label="📋 Copiar Código PIX", style=discord.ButtonStyle.success, emoji="📋")
    async def copiar_codigo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{self.chave_pix}", ephemeral=True)

