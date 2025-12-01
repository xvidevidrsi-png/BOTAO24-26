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
            await interaction.response.send_message("❌ Você não faz parte desta partida!")
            return

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT confirmacao_j1, confirmacao_j2 FROM partidas WHERE id = ?", (self.partida_id,))
        row = cur.fetchone()

        if not row:
            await interaction.response.send_message("❌ Partida não encontrada!")
            conn.close()
            return

        conf_j1, conf_j2 = row

        if user_id == self.jogador1_id:
            if conf_j1 == 1:
                await interaction.response.send_message("❌ Você já confirmou esta partida!")
                conn.close()
                return
            cur.execute("UPDATE partidas SET confirmacao_j1 = 1 WHERE id = ?", (self.partida_id,))
        else:
            if conf_j2 == 1:
                await interaction.response.send_message("❌ Você já confirmou esta partida!")
                conn.close()
                return
            cur.execute("UPDATE partidas SET confirmacao_j2 = 1 WHERE id = ?", (self.partida_id,))

        conn.commit()

        cur.execute("SELECT confirmacao_j1, confirmacao_j2, mediador, valor, guild_id FROM partidas WHERE id = ?", (self.partida_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            await interaction.response.send_message("❌ Partida não encontrada!")
            return

        conf_j1, conf_j2, mediador_id, valor, guild_id_partida = row

        await interaction.response.send_message("✅ Confirmação registrada!")

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
                    description=f"<@{self.jogador1_id}>\n<@{self.jogador2_id}>",
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
            
            # 🎮 ACIONAR SISTEMA DE SALA (sem modal - mensagens de texto)
            try:
                if mediador_id and mediador_id > 0:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE partidas SET estado_sala = 'aguardando_id' WHERE id = ?", (self.partida_id,))
                    conn.commit()
                    conn.close()
                    await interaction.channel.send(f"<@{mediador_id}> - Digite o ID da sala (6-13 dígitos):")
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
            await interaction.response.send_message("❌ Você não faz parte desta partida!")
            return

        await interaction.response.send_message("❌ Você recusou a partida! O canal será fechado.")

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
        await interaction.response.send_message(f"{self.chave_pix}")

class CopiarCodigoPIXView(View):
    def __init__(self, codigo_pix, chave_pix):
        super().__init__(timeout=None)
        self.codigo_pix = codigo_pix
        self.chave_pix = chave_pix

    @discord.ui.button(label="📋 Copiar Código PIX", style=discord.ButtonStyle.success, emoji="📋")
    async def copiar_codigo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{self.chave_pix}")

class CopiarIDView(View):
    def __init__(self, sala_id):
        super().__init__(timeout=None)
        self.sala_id = sala_id

    @discord.ui.button(label="Copiar ID", style=discord.ButtonStyle.primary, emoji="📋")
    async def copiar_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{self.sala_id}")

class EscolherVencedorView(View):
    def __init__(self, partida_id, j1_id, j2_id):
        super().__init__(timeout=None)
        self.partida_id = partida_id
        self.j1_id = j1_id
        self.j2_id = j2_id

    @discord.ui.button(label="Jogador 1", style=discord.ButtonStyle.success)
    async def jogador1(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ConfirmarVencedorView(self.partida_id, self.j1_id, self.j2_id)
        await interaction.response.send_message(
            f"⚠️ Confirmar vencedor?\n\nJogador1\n<@{self.j1_id}>\n\nJogador2\n<@{self.j2_id}>",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Jogador 2", style=discord.ButtonStyle.success)
    async def jogador2(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ConfirmarVencedorView(self.partida_id, self.j2_id, self.j1_id)
        await interaction.response.send_message(
            f"⚠️ Confirmar vencedor?\n\nJogador1\n<@{self.j1_id}>\n\nJogador2\n<@{self.j2_id}>",
            view=view,
            ephemeral=True
        )

class ConfirmarVencedorView(View):
    def __init__(self, partida_id, vencedor_id, perdedor_id):
        super().__init__(timeout=None)
        self.partida_id = partida_id
        self.vencedor_id = vencedor_id
        self.perdedor_id = perdedor_id

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        usuario_add_coins(guild_id, self.vencedor_id, COIN_POR_VITORIA)
        usuario_add_vitoria(guild_id, self.vencedor_id)
        usuario_add_derrota(guild_id, self.perdedor_id)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE partidas SET vencedor = ?, status = 'finalizada' WHERE id = ?", 
                    (self.vencedor_id, self.partida_id))
        conn.commit()
        conn.close()

        await interaction.response.edit_message(
            content=f"✅ Vencedor confirmado: <@{self.vencedor_id}>!",
            view=None
        )

        await interaction.channel.send(f"🏆 1 vitória(s) e {COIN_POR_VITORIA} coin(s) adicionados para <@{self.vencedor_id}>!")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, mediador, jogador1, jogador2 FROM partidas WHERE id = ? AND guild_id = ?", (self.partida_id, guild_id))
        row = cur.fetchone()
        conn.close()

        if row:
            partida_id, mediador_id, j1_id, j2_id = row
            embed = discord.Embed(
                title="Menu Mediador",
                description=f"<@{j1_id}>\n<@{j2_id}>",
                color=0x2f3136
            )
            view = MenuMediadorView(partida_id)
            await interaction.channel.send(embed=embed, view=view)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Cancelado!", view=None)

class MenuMediadorView(View):
    def __init__(self, partida_id):
        super().__init__(timeout=None)
        self.partida_id = partida_id

    @discord.ui.button(label="Vitória", style=discord.ButtonStyle.success, emoji="🏆")
    async def vitoria(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_aux_permitido(interaction.user):
            await interaction.response.send_message("❌ Apenas mediadores podem usar este botão!")
            return

        guild_id = interaction.guild.id
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT jogador1, jogador2 FROM partidas WHERE id = ? AND guild_id = ?", (self.partida_id, guild_id))
        row = cur.fetchone()
        conn.close()

        if not row:
            await interaction.response.send_message("❌ Partida não encontrada!")
            return

        j1_id, j2_id = row
        view = EscolherVencedorView(self.partida_id, j1_id, j2_id)
        await interaction.response.send_message("Escolha o vencedor:", view=view)

    @discord.ui.button(label="Finalizar aposta", style=discord.ButtonStyle.danger, emoji="🔚")
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_aux_permitido(interaction.user):
            await interaction.response.send_message("❌ Apenas mediadores podem usar este botão!")
            return

        await interaction.response.send_message("✅ Aposta finalizada! Canal será fechado em 10 segundos...")
        await interaction.channel.send("🔚 Aposta finalizada. Canal será fechado em 10 segundos...")
        await asyncio.sleep(10)
        await interaction.channel.delete()

    @discord.ui.button(label="Vitória por W.O.", style=discord.ButtonStyle.primary, emoji="⚠️")
    async def vitoria_wo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_aux_permitido(interaction.user):
            await interaction.response.send_message("❌ Apenas mediadores podem usar este botão!")
            return

        guild_id = interaction.guild.id
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT jogador1, jogador2 FROM partidas WHERE id = ? AND guild_id = ?", (self.partida_id, guild_id))
        row = cur.fetchone()
        conn.close()

        if not row:
            await interaction.response.send_message("❌ Partida não encontrada!")
            return

        j1_id, j2_id = row
        view = EscolherVencedorView(self.partida_id, j1_id, j2_id)
        await interaction.response.send_message("⚠️ W.O. - Escolha o vencedor:", view=view)


    @discord.ui.button(label="Revanche", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def revanche(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_aux_permitido(interaction.user):
            await interaction.response.send_message("❌ Apenas mediadores podem usar este botão!")
            return

        guild_id = interaction.guild.id
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT sala_id, estado_sala FROM partidas WHERE id = ? AND guild_id = ?", (self.partida_id, guild_id))
        row = cur.fetchone()
        conn.close()

        if not row or not row[0] or row[1] != 'sala_criada':
            await interaction.response.send_message("❌ Precisa criar uma sala primeiro! Digite o ID e senha no chat.")
            return

        modal = TrocarValorModal(self.partida_id, interaction.channel)
        await interaction.response.send_modal(modal)

class DefinirSalaModal(Modal):
    def __init__(self, partida_id, canal, guild):
        super().__init__(title="Criar Nova Sala")
        self.partida_id = partida_id
        self.canal = canal
        self.guild = guild

        self.novo_valor = TextInput(
            label="Valor do Pagamento",
            placeholder="Ex: 2.00 ou 5.00",
            required=True,
            max_length=10
        )

        self.novo_sala_id = TextInput(
            label="ID da Sala",
            placeholder="Digite o ID da nova sala",
            required=True,
            max_length=50
        )

        self.nova_senha = TextInput(
            label="Senha da Sala",
            placeholder="Digite a senha da nova sala",
            required=True,
            max_length=50
        )

        self.add_item(self.novo_valor)
        self.add_item(self.novo_sala_id)
        self.add_item(self.nova_senha)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor_str = self.novo_valor.value.replace(",", ".")
            novo_valor = float(valor_str)

            if novo_valor <= 0:
                await interaction.response.send_message("❌ O valor deve ser maior que zero!")
                return

            novo_sala_id = self.novo_sala_id.value.strip()
            nova_senha = self.nova_senha.value.strip()

            if not novo_sala_id or not nova_senha:
                await interaction.response.send_message("❌ ID e senha da sala são obrigatórios!")
                return

            guild_id = interaction.guild.id
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT jogador1, jogador2, mediador FROM partidas WHERE id = ? AND guild_id = ?", (self.partida_id, guild_id))
            partida_row = cur.fetchone()

            if not partida_row:
                conn.close()
                await interaction.response.send_message("❌ Partida não encontrada!")
                return

            j1_id, j2_id, mediador_id = partida_row

            cur.execute("UPDATE partidas SET valor = ?, sala_id = ?, sala_senha = ? WHERE id = ? AND guild_id = ?", 
                       (novo_valor, novo_sala_id, nova_senha, self.partida_id, guild_id))
            conn.commit()
            conn.close()

            nome_atual = self.canal.name
            if "-" in nome_atual:
                partes = nome_atual.split("-")
                novo_nome = f"{partes[0]}-{novo_valor:.2f}".replace(".", ",")
                try:
                    await self.canal.edit(name=novo_nome)
                except:
                    pass

            embed = discord.Embed(
                title="🎮 Nova Sala Criada",
                description=f"Valor alterado para **{fmt_valor(novo_valor)}**",
                color=0x2f3136
            )
            embed.add_field(name="➡️ Nova Sala", value=f"ID: {novo_sala_id} | Senha: {nova_senha}", inline=False)

            view = CopiarIDView(novo_sala_id)
            await interaction.channel.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Sala criada com sucesso!")

        except ValueError:
            await interaction.response.send_message("❌ Valor inválido! Use apenas números (ex: 2.00)")

class TrocarValorModal(Modal):
    def __init__(self, partida_id, canal):
        super().__init__(title="Revanche - Nova Sala")
        self.partida_id = partida_id
        self.canal = canal

        self.novo_valor = TextInput(
            label="Novo Valor da Partida",
            placeholder="Ex: 2.00 ou 5.00",
            required=True,
            max_length=10
        )

        self.novo_sala_id = TextInput(
            label="Novo ID da Sala",
            placeholder="Digite o ID da nova sala",
            required=True,
            max_length=50
        )

        self.nova_senha = TextInput(
            label="Nova Senha da Sala",
            placeholder="Digite a senha da nova sala",
            required=True,
            max_length=50
        )

        self.add_item(self.novo_valor)
        self.add_item(self.novo_sala_id)
        self.add_item(self.nova_senha)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor_str = self.novo_valor.value.replace(",", ".")
            novo_valor = float(valor_str)

            if novo_valor <= 0:
                await interaction.response.send_message("❌ O valor deve ser maior que zero!")
                return

            novo_sala_id = self.novo_sala_id.value.strip()
            nova_senha = self.nova_senha.value.strip()

            if not novo_sala_id or not nova_senha:
                await interaction.response.send_message("❌ ID e senha da sala são obrigatórios!")
                return

            guild_id = interaction.guild.id
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("UPDATE partidas SET valor = ?, sala_id = ?, sala_senha = ? WHERE id = ? AND guild_id = ?", 
                       (novo_valor, novo_sala_id, nova_senha, self.partida_id, guild_id))
            conn.commit()
            conn.close()

            nome_atual = self.canal.name
            if "-" in nome_atual:
                partes = nome_atual.split("-")
                novo_nome = f"{partes[0]}-{novo_valor:.2f}".replace(".", ",")
                try:
                    await self.canal.edit(name=novo_nome)
                except:
                    pass

            embed = discord.Embed(
                title="🔄 Revanche - Nova Sala Criada",
                description=f"Valor alterado para **{fmt_valor(novo_valor)}**",
                color=0x2f3136
            )
            embed.add_field(name="➡️ Nova Sala", value=f"ID: {novo_sala_id} | Senha: {nova_senha}", inline=False)

            view = CopiarIDView(novo_sala_id)
            await interaction.channel.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Revanche criada com nova sala!")

        except ValueError:
            await interaction.response.send_message("❌ Valor inválido! Use apenas números (ex: 2.00)")

class ConfigurarPIXModal(Modal):
    def __init__(self):
        super().__init__(title="Configurar PIX do Mediador")

        self.nome_completo = TextInput(label="Nome Completo", placeholder="João Silva", required=True, max_length=100)
        self.chave_pix = TextInput(label="Chave PIX", placeholder="email@exemplo.com ou CPF ou telefone", required=True, max_length=100)

        self.add_item(self.nome_completo)
        self.add_item(self.chave_pix)

    async def on_submit(self, interaction: discord.Interaction):
        print(f"\n{'='*60}")
        print(f"📝 MEDIADOR CONFIGURANDO PIX")
        print(f"{'='*60}")
        print(f"Guild ID: {interaction.guild.id}")
        print(f"Mediador: <@{interaction.user.id}> ({interaction.user.display_name})")
        print(f"Nome Completo: {self.nome_completo.value}")
        print(f"Chave PIX: {self.chave_pix.value[:15]}..." if len(self.chave_pix.value) > 15 else f"Chave PIX: {self.chave_pix.value}")
        
        # Limpar espaços em branco
        nome_clean = self.nome_completo.value.strip()
        chave_clean = self.chave_pix.value.strip()
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO mediador_pix (guild_id, user_id, nome_completo, chave_pix, criado_em)
                       VALUES (?, ?, ?, ?, ?)""",
                    (interaction.guild.id, interaction.user.id, nome_clean, chave_clean, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        
        print(f"✅ PIX ARMAZENADO NO BANCO COM SUCESSO!")
        print(f"{'='*60}\n")

        await interaction.response.send_message(
            f"✅ **PIX Configurado com Sucesso!**\n\n"
            f"📋 **Nome:** {nome_clean}\n"
            f"💳 **Chave:** {chave_clean}\n\n"
            f"💡 **Agora você pode entrar na fila de mediadores!**",
            ephemeral=True
        )

class ConfigurarPIXView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Configurar PIX", style=discord.ButtonStyle.primary, emoji="💰", custom_id="pix_configurar_btn")
    async def configurar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Disponível para TODOS os mediadores
        print(f"✅ {interaction.user.display_name} está configurando PIX")
        modal = ConfigurarPIXModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Verificar PIX", style=discord.ButtonStyle.success, emoji="✅", custom_id="pix_verificar_btn")
    async def verificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        user_id = interaction.user.id

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT nome_completo, chave_pix FROM mediador_pix WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            await interaction.response.send_message(
                "❌ Você ainda não configurou seu PIX!\n\nClique em **Configurar PIX** primeiro.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="✅ Seus Dados PIX Configurados",
            description="Apenas você pode ver estas informações",
            color=0x00ff00
        )
        embed.add_field(name="📋 Nome Completo", value=row[0], inline=False)
        embed.add_field(name="🔑 Chave PIX", value=row[1], inline=False)
        embed.set_footer(text="💡 Use o botão 'Configurar PIX' para atualizar seus dados")

        await interaction.response.send_message(embed=embed)

class RemoverMediadorSelect(Select):
    def __init__(self, mediadores_ids, guild):
        options = []
        for med_id in mediadores_ids[:25]:
            member = guild.get_member(med_id)
            if member:
                label = f"{member.display_name}"
                description = f"@{member.name} - ID: {med_id}"
            else:
                label = f"Mediador ID: {med_id}"
                description = f"Usuário não encontrado no servidor"

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    description=description[:100],
                    value=str(med_id)
                )
            )

        super().__init__(
            placeholder="Quem você deseja remover?",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        mediador_id = int(self.values[0])
        guild_id = interaction.guild.id
        mediador_remove(guild_id, mediador_id)
        await interaction.response.send_message(
            f"✅ Mediador <@{mediador_id}> removido com sucesso✔️",
            ephemeral=True
        )

class RemoverMediadorView(View):
    def __init__(self, mediadores_ids, guild):
        super().__init__(timeout=None)
        self.add_item(RemoverMediadorSelect(mediadores_ids, guild))

class FilaMediadoresView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Entrar em serviço", style=discord.ButtonStyle.success, emoji="✅", custom_id="med_entrar_btn")
    async def entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        if not verificar_pix_mediador(guild_id, interaction.user.id):
            await interaction.response.send_message(
                "❌ **PIX não configurado!**\n\n"
                "Para entrar na fila de mediadores, você precisa configurar seu PIX primeiro.\n"
                "Use o comando `!pixmed` para configurar.",
                ephemeral=True
            )
            return

        mediador_add(guild_id, interaction.user.id)
        await interaction.response.send_message("✅ Você entrou na fila de mediadores!")

    @discord.ui.button(label="Sair de serviço", style=discord.ButtonStyle.danger, emoji="❌", custom_id="med_sair_btn")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        mediador_remove(guild_id, interaction.user.id)
        await interaction.response.send_message("✅ Removido com sucesso✔️")

    @discord.ui.button(label="Remover mediador", style=discord.ButtonStyle.secondary, emoji="🗑️", custom_id="med_remover_btn")
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message(
                "⛔ **Servidor não registrado!**\n\n"
                "Este servidor precisa estar registrado para usar o Bot Zeus.",
                ephemeral=True
            )
            return

        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Apenas administradores podem remover mediadores!")
            return

        guild_id = interaction.guild.id
        mediadores = mediador_get_all(guild_id)
        if not mediadores:
            await interaction.response.send_message("❌ Nenhum mediador na fila!")
            return

        view = RemoverMediadorView(mediadores, interaction.guild)
        embed = discord.Embed(
            title="🗑️ Remover Mediador",
            description="Selecione o mediador que deseja remover da fila:",
            color=0xff0000
        )

        if len(mediadores) > 25:
            embed.set_footer(text=f"⚠️ Mostrando apenas os primeiros 25 de {len(mediadores)} mediadores")
        mediadores_lista = "\n".join([f"• <@{med_id}>" for med_id in mediadores[:25]])
        if len(mediadores) > 25:
            mediadores_lista += f"\n\n*...e mais {len(mediadores) - 25} mediadores*"
        embed.add_field(name="Mediadores Disponíveis:", value=mediadores_lista, inline=False)

        await interaction.response.send_message(embed=embed, view=view)


@tree.command(name="aux_config", description="🔐 Define o cargo de MEDIADOR que pode usar botões e comandos")
@app_commands.describe(cargo="Cargo que poderá usar !aux e menu mediador")
async def set_cargo_aux(interaction: discord.Interaction, cargo: discord.Role):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    db_set_config("aux_role_id", str(cargo.id))
    await interaction.response.send_message(f"✅ Cargo aux definido: {cargo.mention}\n\nApenas membros com este cargo poderão usar !aux e acessar o menu mediador!")

@tree.command(name="topico", description="📂 Define o canal onde as THREADS das partidas serão criadas")
@app_commands.describe(canal="Canal onde as threads de partidas serão criadas")
async def set_canal(interaction: discord.Interaction, canal: discord.TextChannel):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    db_set_config("canal_partidas_id", str(canal.id))
    db_set_config("usar_threads", "true")
    await interaction.response.send_message(f"✅ Canal de threads de partidas definido: {canal.mention}\n\n💡 As partidas agora serão criadas como threads (tópicos) neste canal!")

@tree.command(name="configurar", description="🎤 Define quais CARGOS serão mencionados nas partidas")
@app_commands.describe(cargos="IDs dos cargos separados por vírgula")
async def configurar_cargos(interaction: discord.Interaction, cargos: str):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    db_set_config("cargos_mencionar", cargos)
    await interaction.response.send_message("✅ Cargos configurados!")

@tree.command(name="1x1-mob", description="📱 Cria FILAS de 1v1 MOBILE com todos os valores definidos")
async def criar_filas_1v1(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("❌ Este comando só funciona em servidores!")
        return

    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id:
        await interaction.response.send_message("❌ **Canal de partidas não foi configurado!**\n\nUse `/topico` primeiro para definir onde as partidas serão criadas.")
        return

    if not aux_role_id:
        await interaction.response.send_message("❌ **Cargo de mediador não foi configurado!**\n\nUse `/aux_config` primeiro para definir o cargo que terá acesso ao menu mediador.")
        return

    await interaction.response.defer(ephemeral=True)

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="1v1 Mobile",
            description=f"**Modo**\n1v1 Mobile\n\n**Valor**\n{fmt_valor(valor)}\n\n**Jogadores**\nNinguém",
            color=0x2f3136
        )

        # Adicionar imagem do servidor
        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.add_field(name="🔴 Gel Normal", value="Nenhum jogador", inline=True)
        embed.add_field(name="🔵 Gel Infinito", value="Nenhum jogador", inline=True)

        view = FilaView(valor, guild_id, 'mob')
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, 'normal', 'mob', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, 'infinito', 'mob', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

        registrar_historico_fila(guild_id, valor, "normal", "mob", "criada")
        registrar_historico_fila(guild_id, valor, "infinito", "mob", "criada")

    await interaction.followup.send("✅ Todas as filas 1x1 Mobile foram criadas!")

@tree.command(name="1x1-emulador", description="🖥️ Cria FILAS de 1v1 EMULADOR com todos os valores definidos")
async def criar_filas_1x1_emulador(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="1v1 Emulador",
            description=f"**Modo**\n1v1 Emulador\n\n**Valor**\n{fmt_valor(valor)}\n\n**Jogadores**\nNinguém",
            color=0x2f3136
        )

        # Adicionar imagem do servidor
        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.add_field(name="🔴 Gel Normal", value="Nenhum jogador", inline=True)
        embed.add_field(name="🔵 Gel Infinito", value="Nenhum jogador", inline=True)

        view = FilaView(valor, guild_id, 'emu')
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, 'normal', 'emu', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, 'infinito', 'emu', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 1x1 Emulador foram criadas!")

@tree.command(name="2x2-emu", description="👥 Cria FILAS de 2x2 EMULADOR com todos os valores definidos")
async def criar_filas_2x2_emu(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Emulador",
            description=f"🎮 **Modo**\n2X2 EMULADOR\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        embed.add_field(name="🎮 Jogadores na Fila", value="Nenhum jogador", inline=False)

        view = FilaMobView(valor, "2x2-emu", 'emu', guild_id)
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, '2x2-emu', 'emu', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 2x2 Emulador foram criadas!")

@tree.command(name="3x3-emu", description="👥 Cria FILAS de 3x3 EMULADOR com todos os valores definidos")
async def criar_filas_3x3_emu(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Emulador",
            description=f"🎮 **Modo**\n3X3 EMULADOR\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)

        embed.add_field(name="🎮 Jogadores na Fila", value="Nenhum jogador", inline=False)

        view = FilaMobView(valor, "3x3-emu", 'emu', guild_id)
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, '3x3-emu', 'emu', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 3x3 Emulador foram criadas!")

@tree.command(name="4x4-emu", description="👥 Cria FILAS de 4x4 EMULADOR com todos os valores definidos")
async def criar_filas_4x4_emu(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Emulador",
            description=f"🎮 **Modo**\n4X4 EMULADOR\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)

        embed.add_field(name="🎮 Jogadores na Fila", value="Nenhum jogador", inline=False)

        view = FilaMobView(valor, "4x4-emu", 'emu', guild_id)
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, '4x4-emu', 'emu', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 4x4 Emulador foram criadas!")

@tree.command(name="2x2-mob", description="📱 Cria FILAS de 2x2 MOBILE com todos os valores definidos")
async def criar_filas_2x2_mob(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Mobile",
            description=f"🎮 **Modo**\n2X2 MOBILE\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        embed.add_field(name="🎮 Jogadores na Fila", value="Nenhum jogador", inline=False)

        view = FilaMobView(valor, "2x2-mob", 'mob', guild_id)
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, '2x2-mob', 'mob', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 2x2 Mobile foram criadas!")

@tree.command(name="3x3-mob", description="📱 Cria FILAS de 3x3 MOBILE com todos os valores definidos")
async def criar_filas_3x3_mob(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Mobile",
            description=f"🎮 **Modo**\n3X3 MOBILE\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        embed.add_field(name="🎮 Jogadores na Fila", value="Nenhum jogador", inline=False)

        view = FilaMobView(valor, "3x3-mob", 'mob', guild_id)
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, '3x3-mob', 'mob', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 3x3 Mobile foram criadas!")

@tree.command(name="4x4-mob", description="📱 Cria FILAS de 4x4 MOBILE com todos os valores definidos")
async def criar_filas_4x4_mob(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Mobile",
            description=f"🎮 **Modo**\n4X4 MOBILE\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        embed.add_field(name="🎮 Jogadores na Fila", value="Nenhum jogador", inline=False)

        view = FilaMobView(valor, "4x4-mob", 'mob', guild_id)
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em)
                       VALUES (?, ?, '4x4-mob', 'mob', '', ?, ?)""",
                    (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 4x4 Mobile foram criadas!")

@tree.command(name="filamisto-2x2", description="🎮 Cria FILAS de 2x2 MISTO (Mobile + Emulador) com todos os valores")
async def criar_filas_misto_2x2(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Misto",
            description=f"🎮 **Modo**\n2X2-MISTO\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        embed.add_field(name="👥 Jogadores", value="Nenhum jogador na fila", inline=False)

        view = FilaMistoView(valor, "2x2-misto")
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        for vagas in [1]:
            modo_fila = f"2x2-misto_{vagas}emu"
            cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, vagas_emu, jogadores, msg_id, criado_em)
                           VALUES (?, ?, ?, 'misto', ?, '', ?, ?)""",
                        (guild_id, valor, modo_fila, vagas, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 2x2 Misto foram criadas!")

@tree.command(name="filamisto-3x3", description="🎮 Cria FILAS de 3x3 MISTO (Mobile + Emulador) com todos os valores")
async def criar_filas_misto_3x3(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Misto",
            description=f"🎮 **Modo**\n3X3-MISTO\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        embed.add_field(name="👥 Jogadores", value="Nenhum jogador na fila", inline=False)

        view = FilaMistoView(valor, "3x3-misto")
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        for vagas in [1, 2]:
            modo_fila = f"3x3-misto_{vagas}emu"
            cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, vagas_emu, jogadores, msg_id, criado_em)
                           VALUES (?, ?, ?, 'misto', ?, '', ?, ?)""",
                        (guild_id, valor, modo_fila, vagas, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 3x3 Misto foram criadas!")

@tree.command(name="filamisto-4x4", description="🎮 Cria FILAS de 4x4 MISTO (Mobile + Emulador) com todos os valores")
async def criar_filas_misto_4x4(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        return

    canal_id = db_get_config("canal_partidas_id")
    aux_role_id = db_get_config("aux_role_id")

    if not canal_id or not aux_role_id:
        await interaction.response.send_message("❌ **Configuração incompleta!**\n\nUse `/topico` e `/aux_config` antes de criar filas.")
        return

    await interaction.response.defer()

    guild_id = interaction.guild.id
    canal = interaction.channel

    for valor in VALORES_FILAS_1V1:
        embed = discord.Embed(
            title="Filas Misto",
            description=f"🎮 **Modo**\n4X4-MISTO\n\n💰 **Valor**\n{fmt_valor(valor)}\n",
            color=0x2f3136
        )

        imagem_url = db_get_config("imagem_fila_url")
        if imagem_url:
            embed.set_thumbnail(url=imagem_url)
        elif canal.guild.icon:
            embed.set_thumbnail(url=canal.guild.icon.url)

        embed.add_field(name="👥 Jogadores", value="Nenhum jogador na fila", inline=False)

        view = FilaMistoView(valor, "4x4-misto")
        msg = await canal.send(embed=embed, view=view)

        conn = get_connection()
        cur = conn.cursor()
        for vagas in [1, 2, 3]:
            modo_fila = f"4x4-misto_{vagas}emu"
            cur.execute("""INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, vagas_emu, jogadores, msg_id, criado_em)
                           VALUES (?, ?, ?, 'misto', ?, '', ?, ?)""",
                        (guild_id, valor, modo_fila, vagas, msg.id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    await interaction.followup.send("✅ Todas as filas 4x4 Misto foram criadas!")

@tree.command(name="separador_de_servidor", description="⚙️ REGISTRA servidor no sistema - OBRIGATÓRIO ANTES de criar filas!")
@app_commands.describe(
    id_servidor="ID do servidor (use o ID numérico do servidor Discord)",
    nome_dono="Nome do dono do servidor"
)
async def separador_servidor(interaction: discord.Interaction, id_servidor: str, nome_dono: str):
    global BOT_OWNER_ID

    if BOT_OWNER_ID is None:
        await interaction.response.send_message(
            "❌ Owner do bot não foi identificado! Não é possível usar este comando.",
            ephemeral=True
        )
        return

    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message(
            "⛔ **Acesso Negado**\n\n"
            "Este comando é exclusivo do owner do bot (**emanoel7269**).\n\n"
            "📝 **Precisa registrar seu servidor?**\n"
            "Entre em contato com **emanoel7269** para registrar seu servidor no Bot Zeus.\n"
            "O registro é **obrigatório** para usar qualquer funcionalidade do bot!",
            ephemeral=True
        )
        return

    try:
        guild_id_int = int(id_servidor)
    except ValueError:
        await interaction.response.send_message("❌ ID do servidor inválido! Use o ID numérico do servidor.")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT guild_id FROM servidores WHERE guild_id = ?", (guild_id_int,))
    existe = cur.fetchone()

    if existe:
        cur.execute("UPDATE servidores SET nome_dono = ?, ativo = 1 WHERE guild_id = ?",
                    (nome_dono, guild_id_int))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"✅ **Servidor Atualizado com Sucesso!**\n\n"
            f"**ID do Servidor:** {guild_id_int}\n"
            f"**Dono:** {nome_dono}\n"
            f"**Status:** ✅ Ativo\n\n"
            f"🎉 **O servidor já está autorizado a usar o Bot Zeus!**\n"
            f"Todos os comandos estão disponíveis para este servidor.",
            ephemeral=True
        )
    else:
        cur.execute("INSERT INTO servidores (guild_id, nome_dono, ativo, data_registro) VALUES (?, ?, 1, ?)",
                    (guild_id_int, nome_dono, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"✅ **Servidor Registrado com Sucesso!**\n\n"
            f"**ID do Servidor:** {guild_id_int}\n"
            f"**Dono:** {nome_dono}\n"
            f"**Status:** ✅ Ativo\n"
            f"**Data de Registro:** {datetime.datetime.utcnow().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"🎉 **O servidor agora está autorizado a usar o Bot Zeus!**\n\n"
            f"📋 **Próximos Passos:**\n"
            f"1. Use `/dono_comando_slash` para definir o cargo de administração\n"
            f"2. Configure os canais e cargos necessários\n"
            f"3. Use `/manual` para ver todos os comandos disponíveis\n\n"
            f"💡 Este registro garante isolamento de dados e previne bugs críticos.",
            ephemeral=True
        )

@tree.command(name="dono_comando_slash", description="👑 Define o cargo de OWNER com acesso TOTAL a todos os comandos")
@app_commands.describe(
    cargo="O cargo que terá acesso total aos comandos (este cargo não pode ser removido depois)"
)
async def dono_comando_slash(interaction: discord.Interaction, cargo: discord.Role):
    if not interaction.guild:
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado em servidores!",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id

    if not verificar_separador_servidor(guild_id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado no Bot Zeus antes de configurar cargos de administração.\n\n"
            "Entre em contato com o owner do bot (**emanoel7269**) para registrar seu servidor.",
            ephemeral=True
        )
        return

    is_owner = interaction.guild.owner_id == interaction.user.id
    is_admin = interaction.user.guild_permissions.administrator

    if not (is_owner or is_admin):
        await interaction.response.send_message(
            "❌ Apenas o **dono** ou **administradores** do servidor podem usar este comando!",
            ephemeral=True
        )
        return

    existing_role = get_server_owner_role(guild_id)
    if existing_role:
        await interaction.response.send_message(
            f"⚠️ **Cargo de dono já definido!**\n\n"
            f"O cargo <@&{existing_role}> já foi configurado como cargo de dono do servidor.\n"
            f"**Este cargo não pode ser removido ou alterado.**\n\n"
            f"💡 Esta é uma medida de segurança para garantir que sempre haja um cargo com acesso total aos comandos.",
            ephemeral=True
        )
        return

    success = set_server_owner_role(guild_id, cargo.id, cargo.name, interaction.user.id)

    if not success:
        await interaction.response.send_message(
            f"⚠️ **Erro ao configurar cargo!**\n\n"
            f"Parece que outra pessoa acabou de configurar o cargo de dono neste servidor.\n"
            f"Use o comando novamente para ver qual cargo foi definido.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"✅ **Cargo de dono definido com sucesso!**\n\n"
        f"**Cargo:** {cargo.mention}\n"
        f"**Acesso:** Total a todos os comandos do bot\n\n"
        f"⚠️ **ATENÇÃO:** Este cargo **NÃO PODE SER REMOVIDO** depois de definido!\n"
        f"Todos os membros com este cargo terão acesso completo aos comandos administrativos do bot.",
        ephemeral=True
    )

    print(f"[DONO_COMANDO_SLASH] Servidor {guild_id} definiu cargo de dono: {cargo.name} (ID: {cargo.id}) por {interaction.user.name} (ID: {interaction.user.id})")



@tree.command(name="tirar_coin", description="Remove coins de um jogador")
@app_commands.describe(jogador="Jogador", qtd="Quantidade de coins")
async def tirar_coin(interaction: discord.Interaction, jogador: discord.Member, qtd: float):
    if not verificar_separador_servidor(interaction.guild.id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado para usar o Bot Zeus.",
            ephemeral=True
        )
        return

    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message(
            "❌ **Sem permissão!**\n\n"
            "Apenas membros com o cargo de dono configurado podem usar este comando.\n"
            "Use `/dono_comando_slash` para configurar o cargo de administração.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    usuario_remove_coins(guild_id, jogador.id, qtd)
    await interaction.response.send_message(f"✅ {qtd} coin(s) removido(s) de {jogador.mention}!")

@tree.command(name="taxa", description="Altera a taxa por jogador")
@app_commands.describe(valor="Novo valor da taxa (ex: 0.15)")
async def set_taxa(interaction: discord.Interaction, valor: float):
    if not verificar_separador_servidor(interaction.guild.id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado para usar o Bot Zeus.",
            ephemeral=True
        )
        return

    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message(
            "❌ **Sem permissão!**\n\n"
            "Apenas membros com o cargo de dono configurado podem usar este comando.\n"
            "Use `/dono_comando_slash` para configurar o cargo de administração.",
            ephemeral=True
        )
        return

    db_set_config("taxa_por_jogador", str(valor))
    await interaction.response.send_message(f"✅ Taxa alterada para {fmt_valor(valor)}!")

@tree.command(name="definir", description="💰 ALTERA os valores das TODAS filas (Mobile, Emulador e Mistos)")
@app_commands.describe(valores="Valores separados por vírgula (ex: 100,50,40)")
async def definir_valores(interaction: discord.Interaction, valores: str):
    if not verificar_separador_servidor(interaction.guild.id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado para usar o Bot Zeus.",
            ephemeral=True
        )
        return

    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message(
            "❌ **Sem permissão!**\n\n"
            "Apenas membros com o cargo de dono configurado podem usar este comando.\n"
            "Use `/dono_comando_slash` para configurar o cargo de administração.",
            ephemeral=True
        )
        return

    try:
        novos_valores = [float(v.strip()) for v in valores.split(",")]
        global VALORES_FILAS_1V1
        VALORES_FILAS_1V1 = novos_valores
        db_set_config("valores_filas", valores)
        
        guild_id = interaction.guild.id
        conn = get_connection()
        conn.isolation_level = None
        cur = conn.cursor()
        
        cur.execute("BEGIN EXCLUSIVE")
        cur.execute("UPDATE filas SET jogadores = '' WHERE guild_id = ? AND tipo_jogo IN ('mob', 'emu', 'misto')", (guild_id,))
        cur.execute("COMMIT")
        conn.close()
        
        await interaction.response.send_message(
            f"✅ **Valores atualizados com sucesso!**\n\n"
            f"📊 Novos valores: {', '.join([fmt_valor(v) for v in novos_valores])}\n"
            f"🔄 Todas as filas foram limpas! Recrie as filas com os novos valores.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro: {str(e)}\n\nFormato inválido! Use: 100,50,40")

@tree.command(name="addimagem", description="Adiciona uma imagem/logo às filas")
@app_commands.describe(url="URL da imagem (jpg, jpeg, png, gif, webp)")
async def add_imagem(interaction: discord.Interaction, url: str):
    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    url_pattern = re.compile(
        r'^https?://.+\.(jpg|jpeg|png|gif|webp)(\?.*)?$',
        re.IGNORECASE
    )

    if not url_pattern.match(url):
        await interaction.response.send_message(
            "❌ URL inválida! Use uma URL direta de imagem terminando em .jpg, .jpeg, .png, .gif ou .webp",
            ephemeral=True
        )
        return

    db_set_config("imagem_fila_url", url)

    embed = discord.Embed(
        title="✅ Imagem Configurada!",
        description=f"A imagem foi configurada com sucesso e será exibida em todas as filas.\n\nVocê pode visualizar a imagem abaixo:",
        color=0x00ff00
    )
    embed.set_thumbnail(url=url)
    embed.add_field(name="📎 URL", value=f"```{url}```", inline=False)

    await interaction.response.send_message(embed=embed)

@tree.command(name="removerimagem", description="Remove a imagem/logo das filas")
async def remover_imagem(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    imagem_atual = db_get_config("imagem_fila_url")

    if not imagem_atual:
        await interaction.response.send_message("❌ Não há nenhuma imagem configurada!")
        return

    db_set_config("imagem_fila_url", "")
    await interaction.response.send_message("✅ Imagem removida com sucesso! As filas não exibirão mais a imagem.")

@tree.command(name="configurar_nome_bot", description="Configura o nome personalizado do bot")
@app_commands.describe(nome="Nome personalizado para o bot")
async def configurar_nome_bot(interaction: discord.Interaction, nome: str):
    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    if len(nome) > 32:
        await interaction.response.send_message("❌ O nome deve ter no máximo 32 caracteres!")
        return

    try:
        await interaction.guild.me.edit(nick=nome)
        db_set_config("nome_bot", nome)
        await interaction.response.send_message(f"✅ Nome do bot alterado para: **{nome}**!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao alterar o nome do bot: {str(e)}")

@tree.command(name="membro_cargo", description="Configura cargo que será dado a todos os membros do servidor")
@app_commands.describe(cargo="Cargo que será atribuído automaticamente")
async def membro_cargo(interaction: discord.Interaction, cargo: discord.Role):
    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    if not verificar_separador_servidor(interaction.guild.id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado para usar o Bot Zeus.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id

    if cargo.position > interaction.guild.me.top_role.position:
        await interaction.response.send_message(
            "❌ Não posso atribuir este cargo! Ele está acima do meu cargo mais alto.\n\n"
            "Mova meu cargo para uma posição superior nas configurações do servidor.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    set_auto_role(guild_id, cargo.id, cargo.name, interaction.user.id)

    success_count = 0
    fail_count = 0

    for member in interaction.guild.members:
        if not member.bot and cargo not in member.roles:
            try:
                await member.add_roles(cargo, reason=f"Auto-role configurado por {interaction.user}")
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"Erro ao adicionar cargo a {member}: {e}")

    embed = discord.Embed(
        title="✅ Cargo Automático Configurado!",
        description=f"O cargo {cargo.mention} foi configurado com sucesso!",
        color=0x00ff00
    )
    embed.add_field(name="👥 Membros que receberam", value=str(success_count), inline=True)
    if fail_count > 0:
        embed.add_field(name="❌ Falhas", value=str(fail_count), inline=True)
    embed.add_field(
        name="🔔 Automático",
        value="Todos os novos membros receberão este cargo automaticamente!",
        inline=False
    )

    await interaction.followup.send(embed=embed)

@tree.command(name="remover_membro_cargo", description="Remove a configuração de cargo automático")
async def remover_membro_cargo(interaction: discord.Interaction):
    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    if not verificar_separador_servidor(interaction.guild.id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado para usar o Bot Zeus.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    auto_role_id = get_auto_role(guild_id)

    if not auto_role_id:
        await interaction.response.send_message("❌ Nenhum cargo automático está configurado neste servidor!")
        return

    remove_auto_role(guild_id)
    await interaction.response.send_message("✅ Configuração de cargo automático removida com sucesso!")

@tree.command(name="cargos_membros", description="Atribui um cargo a TODOS os membros do servidor (novos e antigos)")
@app_commands.describe(cargo="Cargo que será dado a todos os membros")
async def cargos_membros(interaction: discord.Interaction, cargo: discord.Role):
    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    if not verificar_separador_servidor(interaction.guild.id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado para usar o Bot Zeus.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id

    if cargo.position > interaction.guild.me.top_role.position:
        await interaction.response.send_message(
            "❌ Não posso atribuir este cargo! Ele está acima do meu cargo mais alto.\n\n"
            "Mova meu cargo para uma posição superior nas configurações do servidor.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    set_auto_role(guild_id, cargo.id, cargo.name, interaction.user.id)

    success_count = 0
    fail_count = 0

    for member in interaction.guild.members:
        if not member.bot and cargo not in member.roles:
            try:
                await member.add_roles(cargo, reason=f"Cargo atribuído em massa por {interaction.user}")
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"Erro ao adicionar cargo a {member}: {e}")

    embed = discord.Embed(
        title="✅ Cargo Atribuído com Sucesso!",
        description=f"O cargo {cargo.mention} foi atribuído a todos os membros!",
        color=0x00ff00
    )
    embed.add_field(name="👥 Membros que receberam", value=str(success_count), inline=True)
    if fail_count > 0:
        embed.add_field(name="❌ Falhas", value=str(fail_count), inline=True)
    embed.add_field(
        name="🔔 Automático",
        value="Todos os novos membros também receberão este cargo automaticamente!\n\n💡 Use `/cargos_membros` novamente com outro cargo para trocar.",
        inline=False
    )

    await interaction.followup.send(embed=embed)

@tree.command(name="clonar_emoji", description="Configura emoji customizado para botões específicos de filas")
@app_commands.describe(
    fila="Qual fila deseja customizar",
    botao="Qual botão deseja customizar",
    emoji="Emoji para o botão"
)
@app_commands.choices(fila=[
    app_commands.Choice(name="1x1-mob", value="1x1-mob"),
    app_commands.Choice(name="1x1-emu", value="1x1-emu"),
    app_commands.Choice(name="2x2-mob", value="2x2-mob"),
    app_commands.Choice(name="2x2-emu", value="2x2-emu"),
    app_commands.Choice(name="3x3-mob", value="3x3-mob"),
    app_commands.Choice(name="3x3-emu", value="3x3-emu"),
    app_commands.Choice(name="4x4-mob", value="4x4-mob"),
    app_commands.Choice(name="4x4-emu", value="4x4-emu"),
    app_commands.Choice(name="2x2-misto", value="2x2-misto"),
    app_commands.Choice(name="3x3-misto", value="3x3-misto"),
    app_commands.Choice(name="4x4-misto", value="4x4-misto"),
], botao=[
    app_commands.Choice(name="Gel Normal (apenas 1x1)", value="gel_normal"),
    app_commands.Choice(name="Gel Infinito (apenas 1x1)", value="gel_infinito"),
    app_commands.Choice(name="Entrar (2x2+)", value="entrar"),
    app_commands.Choice(name="Sair (2x2+)", value="sair"),
])
async def clonar_emoji(interaction: discord.Interaction, fila: str, botao: str, emoji: str):
    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    if fila in ["1x1-mob", "1x1-emu"]:
        if botao not in ["gel_normal", "gel_infinito"]:
            await interaction.response.send_message(
                "❌ Para filas 1x1, apenas os botões 'Gel Normal' e 'Gel Infinito' estão disponíveis!",
                ephemeral=True
            )
            return

        set_emoji_custom(interaction.guild.id, botao, emoji)
        botao_nome = {
            "gel_normal": "Gel Normal",
            "gel_infinito": "Gel Infinito"
        }.get(botao, botao.capitalize())
    else:
        if botao not in ["entrar", "sair"]:
            await interaction.response.send_message(
                "❌ Para filas 2x2 ou superiores, apenas os botões 'Entrar' e 'Sair' estão disponíveis!",
                ephemeral=True
            )
            return

        set_emoji_fila(interaction.guild.id, fila, botao, emoji)
        botao_nome = botao.capitalize()

    await interaction.response.send_message(
        f"✅ Emoji {emoji} configurado para o botão **{botao_nome}** na fila **{fila.upper()}**!",
        ephemeral=True
    )



@tree.command(name="fila_mediadores", description="👨‍⚖️ Cria MENU de FILA DE MEDIADORES (Entrar/Sair em serviço)")
async def fila_mediadores_slash(interaction: discord.Interaction):
    if not verificar_separador_servidor(interaction.guild.id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado para usar o Bot Zeus.",
            ephemeral=True
        )
        return

    if not is_admin(interaction.user.id, member=interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!")
        return

    guild_id = interaction.guild.id
    mediadores = mediador_get_all(guild_id)

    embed = discord.Embed(
        title=f"Bem-vindo(a) a #📦・fila-mediadores!",
        description="Este é o começo do canal particular #📦・fila-mediadores.",
        color=0x2f3136
    )

    if mediadores:
        lista_text = "\n".join([f"{i+1}º. <@{med_id}>" for i, med_id in enumerate(mediadores)])
        embed.add_field(name="Mediadores presentes:", value=lista_text, inline=False)
    else:
        embed.add_field(name="Mediadores presentes:", value="Nenhum mediador disponível", inline=False)

    view = FilaMediadoresView()
    await interaction.response.send_message(embed=embed, view=view)
    msg = await interaction.original_response()

    db_set_config(f"fila_mediadores_msg_id_{guild_id}", str(msg.id))
    db_set_config(f"fila_mediadores_canal_id_{guild_id}", str(interaction.channel.id))

@tree.command(name="logs", description="[ADM] Cria canais de log e mostra logs de partidas do servidor")
@app_commands.describe(jogador="Jogador para filtrar logs (opcional)")
async def logs_slash(interaction: discord.Interaction, jogador: discord.Member = None):
    await interaction.response.send_message("⛔ **Este comando foi desabilitado!**")
    return

    cargo_mais_alto = max(guild.roles, key=lambda r: r.position)

    canais_log = [
        ("🔒 • log-filas", "Logs de criação e gestão de filas"),
        ("🔒 • log-black", "Logs de jogadores banidos"),
        ("🔒 • log-ticket", "⚠️ Logs de tickets de suporte (EM DESENVOLVIMENTO)"),
        ("🌐 • log-iniciadas", "Logs de partidas iniciadas"),
        ("✅ • log-confirmadas", "Logs de partidas confirmadas"),
        ("❌ • log-recusada", "Logs de partidas recusadas"),
        ("🔥 • log-criadas", "Logs de partidas criadas"),
        ("🏁 • logs-finalizadas", "Logs de partidas finalizadas")
    ]

    categoria = None
    for cat in guild.categories:
        if "log" in cat.name.lower():
            categoria = cat
            break

    canais_criados = []

    if not categoria:
        categoria = await guild.create_category("📋 LOGS")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        cargo_mais_alto: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }

    for nome_canal, topico in canais_log:
        canal_existente = discord.utils.get(categoria.channels, name=nome_canal)
        if not canal_existente:
            try:
                novo_canal = await categoria.create_text_channel(
                    name=nome_canal,
                    topic=topico,
                    overwrites=overwrites
                )
                canais_criados.append(nome_canal)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Erro ao criar canal {nome_canal}: {e}")

    if canais_criados:
        embed_criacao = discord.Embed(
            title="✅ Canais de Log Criados!",
            description=f"**Categoria:** {categoria.mention}\n**Permissões:** Apenas {cargo_mais_alto.mention} pode ver\n\n⚠️ **ATENÇÃO:** Todos os logs de partidas serão automaticamente enviados para estes canais!",
            color=0x00ff00
        )
        embed_criacao.add_field(
            name="📋 Canais Criados:",
            value="\n".join([f"• {canal}" for canal in canais_criados]),
            inline=False
        )
        await interaction.followup.send(embed=embed_criacao)

    jogador_id = jogador.id if jogador else None
    logs = obter_logs_partidas(guild_id, jogador_id, 15)

    if not logs:
        if not canais_criados:
            await interaction.followup.send("❌ Nenhum log encontrado! Os canais já existem.")
        return

    embed = discord.Embed(
        title=f"📋 Logs de Partidas{' - ' + jogador.display_name if jogador else ''}",
        color=0x2f3136
    )

    for log in logs:
        partida_id, acao, j1_id, j2_id, med_id, valor, tipo_fila, timestamp = log

        try:
            dt = datetime.datetime.fromisoformat(timestamp)
            timestamp_str = dt.strftime("%d/%m/%Y %H:%M")
        except:
            timestamp_str = timestamp

        mediador_txt = f" | Mediador: <@{med_id}>" if med_id else ""
        tipo_fila_txt = tipo_fila.upper() if tipo_fila else "1X1-MOB"

        embed.add_field(
            name=f"🎮 Partida {partida_id} | {tipo_fila_txt}",
            value=f"**Ação:** {acao}\n**Jogadores:** <@{j1_id}> vs <@{j2_id}>{mediador_txt}\n**Valor:** {fmt_valor(valor)}\n**Data:** {timestamp_str}",
            inline=False
        )

    embed.set_footer(text=f"Mostrando últimos {len(logs)} registros")
    await interaction.followup.send(embed=embed)

@tree.command(name="deletar_logs", description="[ADM] Deleta todos os canais de log do servidor")
async def deletar_logs(interaction: discord.Interaction):
    await interaction.response.send_message("⛔ **Este comando foi desabilitado!**")
    return

    categoria_logs = None
    for cat in guild.categories:
        if "log" in cat.name.lower():
            categoria_logs = cat
            break

    if not categoria_logs:
        await interaction.followup.send("❌ Nenhuma categoria de logs encontrada!")
        return

    canais_deletados = []

    for canal in categoria_logs.channels:
        try:
            canais_deletados.append(canal.name)
            await canal.delete()
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Erro ao deletar canal {canal.name}: {e}")

    try:
        await categoria_logs.delete()
    except Exception as e:
        print(f"Erro ao deletar categoria: {e}")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM logs_partidas WHERE guild_id = ?", (guild.id,))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="🗑️ Logs Deletados!",
        description=f"**Categoria:** 📋 LOGS\n**Canais deletados:** {len(canais_deletados)}\n**Logs do banco de dados:** Limpos",
        color=0xff0000
    )

    if canais_deletados:
        embed.add_field(
            name="📋 Canais Removidos:",
            value="\n".join([f"• {canal}" for canal in canais_deletados]),
            inline=False
        )

    embed.set_footer(text="⚠️ ATENÇÃO: Esta ação não pode ser desfeita!")
    await interaction.followup.send(embed=embed)

class RankMenuView(View):
    def __init__(self, user_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.guild_id = guild_id
    
    @discord.ui.button(label="👤 Meu Perfil", style=discord.ButtonStyle.primary, emoji="👤")
    async def meu_perfil(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Mostra o perfil da pessoa que clicou no botão
        await mostrar_perfil(interaction, interaction.user, self.guild_id)
    
    @discord.ui.button(label="🏆 Ranking", style=discord.ButtonStyle.success, emoji="🏆")
    async def ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Mostra o ranking do servidor
        await mostrar_ranking(interaction, self.guild_id)

@tree.command(name="rank", description="Ver seu perfil ou o ranking do servidor")
async def rank_command(interaction: discord.Interaction):
    if not verificar_separador_servidor(interaction.guild.id):
        await interaction.response.send_message(
            "⛔ **Servidor não registrado!**\n\n"
            "Este servidor precisa estar registrado para usar o Bot Zeus.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    
    embed = discord.Embed(
        title="📊 Sistema de Perfil e Ranking",
        description=(
            "**Escolha uma opção:**\n\n"
            "👤 **Meu Perfil** - Ver suas estatísticas completas\n"
            "🏆 **Ranking** - Ver o top 10 jogadores do servidor"
        ),
        color=0x5865F2
    )
    
    view = RankMenuView(interaction.user.id, guild_id)
    await interaction.response.send_message(embed=embed, view=view)

async def mostrar_perfil(interaction: discord.Interaction, usuario: discord.Member, guild_id: int, ephemeral: bool = True):
    """Mostra o perfil detalhado de um usuário"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Buscar dados do usuário
    cur.execute("""SELECT coins, vitorias, derrotas FROM usuarios 
                   WHERE guild_id = ? AND user_id = ?""", (guild_id, usuario.id))
    row = cur.fetchone()
    
    # Buscar posição no ranking
    cur.execute("""SELECT COUNT(*) + 1 FROM usuarios 
                   WHERE guild_id = ? AND vitorias > (
                       SELECT COALESCE(vitorias, 0) FROM usuarios 
                       WHERE guild_id = ? AND user_id = ?
                   )""", (guild_id, guild_id, usuario.id))
    posicao = cur.fetchone()[0]
    
    # Buscar total de jogadores no servidor
    cur.execute("""SELECT COUNT(*) FROM usuarios 
                   WHERE guild_id = ? AND (vitorias > 0 OR derrotas > 0)""", (guild_id,))
    total_jogadores = cur.fetchone()[0]
    
    conn.close()
    
    if not row or (row[1] == 0 and row[2] == 0):
        embed = discord.Embed(
            title=f"📊 Perfil de {usuario.display_name}",
            description="Este jogador ainda não participou de nenhuma partida.",
            color=0x2f3136
        )
        embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else usuario.default_avatar.url)
        await interaction.response.send_message(embed=embed)
        return
    
    coins, vitorias, derrotas = row
    total_partidas = vitorias + derrotas
    winrate = (vitorias / total_partidas * 100) if total_partidas > 0 else 0
    
    # Determinar cor do embed baseado no winrate
    if winrate >= 70:
        cor = 0x00FF00  # Verde - Excelente
    elif winrate >= 50:
        cor = 0xFFAA00  # Laranja - Bom
    else:
        cor = 0xFF0000  # Vermelho - Precisa melhorar
    
    # Posição no ranking com medalha
    if posicao == 1:
        medal = "🥇"
    elif posicao == 2:
        medal = "🥈"
    elif posicao == 3:
        medal = "🥉"
    else:
        medal = "🏅"
    
    embed = discord.Embed(
        title=f"📊 Perfil de {usuario.display_name}",
        description=f"{medal} **Posição #{posicao}** de {total_jogadores} jogadores",
        color=cor
    )
    
    # Adicionar foto do usuário
    embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else usuario.default_avatar.url)
    
    # Estatísticas principais em um layout mais visual
    embed.add_field(
        name="💰 Coins",
        value=f"**{coins}**",
        inline=True
    )
    embed.add_field(
        name="🏆 Vitórias",
        value=f"**{vitorias}**",
        inline=True
    )
    embed.add_field(
        name="💔 Derrotas",
        value=f"**{derrotas}**",
        inline=True
    )
    
    # Winrate com barra visual aprimorada
    barra_size = 20
    barra_cheia = int((winrate / 100) * barra_size)
    barra_vazia = barra_size - barra_cheia
    barra_visual = "█" * barra_cheia + "░" * barra_vazia
    
    embed.add_field(
        name="📈 Taxa de Vitória",
        value=f"**{winrate:.1f}%**\n`{barra_visual}`",
        inline=False
    )
    
    # Estatísticas adicionais
    embed.add_field(
        name="🎮 Total de Partidas",
        value=f"**{total_partidas}**",
        inline=True
    )
    
    embed.add_field(
        name="📊 K/D Ratio",
        value=f"**{(vitorias / derrotas):.2f}**" if derrotas > 0 else "**∞**",
        inline=True
    )
    
    embed.add_field(
        name="⭐ Status",
        value=f"**{'Elite' if winrate >= 70 else 'Veterano' if winrate >= 50 else 'Aprendiz'}**",
        inline=True
    )
    
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name} • ID: {usuario.id}")
    
    await interaction.response.send_message(embed=embed)

async def mostrar_ranking(interaction: discord.Interaction, guild_id: int, ephemeral: bool = True):
    """Mostra o ranking completo do servidor"""
    await interaction.response.defer(ephemeral=ephemeral)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Buscar TODOS os jogadores com vitórias
    cur.execute("""SELECT user_id, coins, vitorias, derrotas 
                   FROM usuarios 
                   WHERE guild_id = ? AND (vitorias > 0 OR derrotas > 0)
                   ORDER BY vitorias DESC, coins DESC""", (guild_id,))
    top_jogadores = cur.fetchall()
    
    conn.close()
    
    if not top_jogadores:
        embed = discord.Embed(
            title="🏆 Ranking do Servidor",
            description="Nenhuma partida foi jogada ainda neste servidor!",
            color=0x2f3136
        )
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        return
    
    embed = discord.Embed(
        title=f"🏆 Ranking - {interaction.guild.name}",
        description=f"**Todos os {len(top_jogadores)} Jogadores Ativos**\nClassificação por número de vitórias",
        color=0xFFD700
    )
    
    # Adicionar logo do servidor
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    
    ranking_text = ""
    for i, (user_id, coins, vitorias, derrotas) in enumerate(top_jogadores, 1):
        usuario = interaction.guild.get_member(user_id)
        nome = usuario.display_name if usuario else f"Usuário {user_id}"
        
        total_partidas = vitorias + derrotas
        winrate = (vitorias / total_partidas * 100) if total_partidas > 0 else 0
        
        # Medalhas para top 3
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"**{i}º**"
        
        ranking_text += (
            f"{medal} **{nome}**\n"
            f"└ 🏆 **{vitorias}V** - 💔 **{derrotas}D** | 📈 **{winrate:.1f}%** | 💰 **{coins}** coins\n\n"
        )
    
    embed.add_field(
        name="👑 Hall da Fama",
        value=ranking_text,
        inline=False
    )
    
    # Estatísticas gerais do servidor
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""SELECT 
                   COUNT(*) as total_jogadores,
                   SUM(vitorias + derrotas) as total_partidas,
                   SUM(coins) as total_coins
                   FROM usuarios 
                   WHERE guild_id = ? AND (vitorias > 0 OR derrotas > 0)""", (guild_id,))
    stats = cur.fetchone()
    conn.close()
    
    if stats:
        total_jogadores, total_partidas, total_coins = stats
        embed.add_field(
            name="📊 Estatísticas Gerais do Servidor",
            value=(
                f"👥 **{total_jogadores}** jogadores ativos\n"
                f"🎮 **{total_partidas}** partidas disputadas\n"
                f"💰 **{total_coins}** coins em circulação"
            ),
            inline=False
        )
    
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name} • Use /rank tipo:Meu Perfil para ver seu perfil")
    
    await interaction.followup.send(embed=embed, ephemeral=ephemeral)

@tree.command(name="manual", description="Manual completo do bot com todos os comandos disponíveis")
async def config_menu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title="📖 Manual Completo - Bot Zeus",
        description=(
            "**Guia completo de todos os comandos disponíveis**\n\n"
            "Use `/manual` a qualquer momento para consultar este guia!\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x5865F2
    )
    
    # Adicionar thumbnail do servidor se disponível
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.add_field(
        name="📊 Filas - Criar",
        value=(
            "```\n"
            "/1x1-mob        - Filas 1v1 Mobile\n"
            "/1x1-emulador   - Filas 1v1 Emulador\n"
            "/2x2-mob        - Filas 2x2 Mobile\n"
            "/2x2-emu        - Filas 2x2 Emulador\n"
            "/3x3-mob        - Filas 3x3 Mobile\n"
            "/3x3-emu        - Filas 3x3 Emulador\n"
            "/4x4-mob        - Filas 4x4 Mobile\n"
            "/4x4-emu        - Filas 4x4 Emulador\n"
            "/filamisto-2x2  - Filas 2x2 Misto\n"
            "/filamisto-3x3  - Filas 3x3 Misto\n"
            "/filamisto-4x4  - Filas 4x4 Misto\n"
            "```"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Configuração Geral",
        value=(
            "```\n"
            "/aux_config          - Define cargo auxiliar\n"
            "/topico              - Define canal de partidas\n"
            "/configurar          - Cargos a mencionar\n"
            "/configurar_nome_bot - Altera nome do bot\n"
            "/addimagem           - Adiciona logo às filas\n"
            "/removerimagem       - Remove logo das filas\n"
            "/taxa                - Altera taxa por jogador\n"
            "/definir             - Define valores das filas\n"
            "```"
        ),
        inline=False
    )

    embed.add_field(
        name="😀 Personalização (Emojis)",
        value=(
            "```\n"
            "/clonar_emoji - Customiza emojis dos botões\n"
            "```\n"
            "**Opções:**\n"
            "• **Filas 1x1:** Gel Normal, Gel Infinito\n"
            "• **Filas 2x2+:** Entrar, Sair"
        ),
        inline=False
    )

    embed.add_field(
        name="👥 Sistema de Mediadores",
        value=(
            "```\n"
            "/fila_mediadores - Cria menu de mediadores\n"
            "!pixmed          - Configura PIX (prefix)\n"
            "```"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 Perfil e Ranking",
        value=(
            "```\n"
            "/rank - Menu interativo com 2 opções\n"
            "!p    - Ver perfil (prefix)\n"
            "```\n"
            "**Opções do /rank:**\n"
            "• 👤 **Meu Perfil** - Suas estatísticas\n"
            "• 🏆 **Ranking** - Top 10 do servidor"
        ),
        inline=False
    )

    embed.add_field(
        name="🔧 Administração",
        value=(
            "```\n"
            "/dono_comando_slash   - Define cargo admin\n"
            "/tirar_coin           - Remove coins\n"
            "/membro_cargo         - Cargo automático\n"
            "/remover_membro_cargo - Remove auto-cargo\n"
            "/cargos_membros       - Cargo para todos\n"
            "```"
        ),
        inline=False
    )

    embed.add_field(
        name="📋 Sistema de Logs",
        value=(
            "```\n"
            "/logs         - ⛔ DESABILITADO\n"
            "/deletar_logs - ⛔ DESABILITADO\n"
            "```\n"
            "⚠️ **Estes comandos foram desabilitados temporariamente**"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Comandos Owner",
        value=(
            "```\n"
            "/separador_de_servidor - Registra servidor\n"
            "/resete_bot            - Reset completo\n"
            "/puxar                 - Busca dados servidor\n"
            "```\n"
            "⚠️ Apenas **emanoel7269** pode usar"
        ),
        inline=False
    )

    embed.add_field(
        name="📚 Legenda de Comandos",
        value=(
            "```\n"
            "/ - Comando slash (barra)\n"
            "! - Comando prefix (prefixo)\n"
            "<> - Parâmetro obrigatório\n"
            "[] - Parâmetro opcional\n"
            "```"
        ),
        inline=False
    )

    embed.set_footer(
        text=f"Bot Zeus • Solicitado por {interaction.user.display_name}",
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )
    
    embed.timestamp = datetime.datetime.utcnow()

    await interaction.followup.send(embed=embed)

@tree.command(name="puxar", description="[OWNER] Busca dados de um servidor específico por ID")
@app_commands.describe(id_servidor="ID do servidor para buscar dados")
async def puxar(interaction: discord.Interaction, id_servidor: str):
    if BOT_OWNER_ID is None:
        await interaction.response.send_message(
            "❌ Owner do bot não foi identificado! Não é possível usar este comando.",
            ephemeral=True
        )
        return

    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message(
            "❌ Apenas o dono do bot pode usar este comando!",
            ephemeral=True
        )
        print(f"⚠️ Tentativa de puxar dados negada: {interaction.user} (ID: {interaction.user.id}) não é o owner")
        return

    try:
        guild_id = int(id_servidor)
    except ValueError:
        await interaction.response.send_message("❌ ID do servidor inválido! Use apenas números.")
        return

    guild = bot.get_guild(guild_id)

    if not guild:
        await interaction.response.send_message(
            f"❌ Servidor com ID `{id_servidor}` não encontrado!\n"
            f"O bot não está neste servidor ou o ID está incorreto.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    conn = get_connection()
    cur = conn.cursor()

    # Estatísticas de filas
    cur.execute("SELECT COUNT(*) FROM historico_filas WHERE guild_id = ? AND acao = 'criada'", (guild_id,))
    filas_criadas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT guild_id || valor || modo || tipo_jogo) FROM filas WHERE guild_id = ? AND jogadores != ''", (guild_id,))
    filas_ativas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM historico_filas WHERE guild_id = ? AND acao = 'finalizada'", (guild_id,))
    filas_finalizadas = cur.fetchone()[0]

    # Estatísticas de partidas
    cur.execute("SELECT COUNT(*) FROM partidas WHERE guild_id = ?", (guild_id,))
    total_partidas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM partidas WHERE guild_id = ? AND status = 'finalizada'", (guild_id,))
    partidas_finalizadas = cur.fetchone()[0]

    # PIX cadastrados
    cur.execute("""SELECT user_id, nome_completo, chave_pix 
                   FROM mediador_pix 
                   WHERE guild_id = ? 
                   ORDER BY nome_completo ASC 
                   LIMIT 10""", (guild_id,))
    pix_rows = cur.fetchall()

    conn.close()

    embed = discord.Embed(
        title=f"📊 Dados do Servidor",
        description=f"**Servidor:** {guild.name}\n**ID:** `{guild_id}`\n**Membros:** {guild.member_count}",
        color=0x5865F2
    )

    # Estatísticas de Filas
    embed.add_field(
        name="📋 Filas",
        value=f"**Total Criadas:** {filas_criadas}\n**Ativas:** {filas_ativas}\n**Finalizadas:** {filas_finalizadas}",
        inline=True
    )

    # Estatísticas de Partidas
    embed.add_field(
        name="🎮 Partidas",
        value=f"**Total:** {total_partidas}\n**Finalizadas:** {partidas_finalizadas}",
        inline=True
    )

    # PIX Cadastrados
    if pix_rows:
        pix_text = ""
        for i, (user_id, nome_completo, chave_pix) in enumerate(pix_rows, 1):
            pix_text += f"{i}. **{nome_completo}**\n   PIX: {chave_pix}\n"

        if len(pix_rows) >= 10:
            pix_text += "\n_Mostrando 10 primeiros..._"

        embed.add_field(
            name=f"💰 PIX Cadastrados ({len(pix_rows)})",
            value=pix_text,
            inline=False
        )
    else:
        embed.add_field(
            name="💰 PIX Cadastrados",
            value="Nenhum PIX cadastrado",
            inline=False
        )

    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(text=f"Solicitado por {interaction.user}")

    await interaction.followup.send(embed=embed)

@tree.command(name="resete_bot", description="[OWNER] Reseta completamente a memória do bot - APAGA TODOS OS DADOS!")
async def resete_bot(interaction: discord.Interaction):
    if BOT_OWNER_ID is None:
        await interaction.response.send_message(
            "❌ Owner do bot não foi identificado! Não é possível usar este comando.",
            ephemeral=True
        )
        return

    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message(
            "❌ Apenas o dono do bot pode usar este comando!",
            ephemeral=True
        )
        print(f"⚠️ Tentativa de reset negada: {interaction.user} (ID: {interaction.user.id}) não é o owner")
        return

    confirm_view = View(timeout=30)

    async def confirmar_reset(inter: discord.Interaction):
        conn = None
        try:
            print(f"🚨 INICIANDO RESET TOTAL DO BOT por {inter.user} (ID: {inter.user.id})")

            conn = get_connection()
            conn.isolation_level = None
            cur = conn.cursor()

            cur.execute("BEGIN TRANSACTION")

            tabelas = [
                "usuarios",
                "filas", 
                "partidas",
                "historico_filas",
                "mediador_pix",
                "fila_mediadores",
                "emoji_config",
                "contras",
                "logs_partidas"
            ]

            rows_deleted = {}
            for tabela in tabelas:
                cur.execute(f"SELECT COUNT(*) FROM {tabela}")
                count = cur.fetchone()[0]
                rows_deleted[tabela] = count

                cur.execute(f"DELETE FROM {tabela}")
                print(f"  ✓ Tabela '{tabela}' limpa ({count} registros apagados)")

            cur.execute("COMMIT")

            total_rows = sum(rows_deleted.values())
            print(f"✅ RESET COMPLETO! Total de {total_rows} registros apagados de {len(tabelas)} tabelas")

            detalhes = "\n".join([f"• {tabela}: {count} registros" for tabela, count in rows_deleted.items()])

            await inter.response.edit_message(
                content=f"✅ **BOT RESETADO COM SUCESSO!**\n\n"
                        f"**Total apagado:** {total_rows} registros\n\n"
                        f"**Detalhes por tabela:**\n{detalhes}\n\n"
                        f"O bot está limpo e pronto para recomeçar!",
                view=None
            )

        except Exception as e:
            if conn:
                try:
                    cur.execute("ROLLBACK")
                    print(f"❌ ROLLBACK executado após erro: {e}")
                except:
                    pass

            print(f"❌ ERRO durante reset do bot: {e}")
            await inter.response.edit_message(
                content=f"❌ **Erro ao resetar bot!**\n\n"
                        f"Nenhum dado foi apagado (rollback executado).\n\n"
                        f"**Erro:** {str(e)}",
                view=None
            )
        finally:
            if conn:
                conn.close()

    async def cancelar_reset(inter: discord.Interaction):
        await inter.response.edit_message(
            content="❌ Reset cancelado. Nenhum dado foi apagado.",
            view=None
        )
        print(f"ℹ️ Reset cancelado por {inter.user}")

    btn_confirmar = Button(label="⚠️ SIM, APAGAR TUDO!", style=discord.ButtonStyle.danger)
    btn_confirmar.callback = confirmar_reset
    confirm_view.add_item(btn_confirmar)

    btn_cancelar = Button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    btn_cancelar.callback = cancelar_reset
    confirm_view.add_item(btn_cancelar)

    await interaction.response.send_message(
        "🚨 **ATENÇÃO - CONFIRMAÇÃO DE RESET TOTAL**\n\n"
        "⚠️ Esta ação vai **APAGAR PERMANENTEMENTE**:\n"
        "• Todos os usuários e coins\n"
        "• Todas as filas ativas\n"
        "• Todas as partidas\n"
        "• Todos os mediadores e PIX\n"
        "• Todo o histórico\n"
        "• Todas as configurações de emoji\n"
        "• Todos os contras e logs\n\n"
        "**ESTA AÇÃO NÃO PODE SER DESFEITA!**\n\n"
        "Tem certeza que deseja continuar?",
        view=confirm_view,
        ephemeral=True
    )

@tasks.loop(seconds=30)
async def rotacao_mediadores_task():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT guild_id FROM servidores WHERE ativo = 1")
    servidores = cur.fetchall()
    conn.close()

    for (guild_id,) in servidores:
        mediadores = mediador_get_all(guild_id)
        if mediadores:
            primeiro = mediadores[0]
            mediador_rotacionar(guild_id, primeiro)

PING_START_TIME = None
PING_COUNT = 0
PING_ERRORS = 0
LAST_PING_STATUS = "OK"

@tasks.loop(seconds=30)
async def ping_task():
    global PING_COUNT, PING_ERRORS, LAST_PING_STATUS
    PING_COUNT += 1

    try:
        latency_ms = round(bot.latency * 1000, 2)
        guild_count = len(bot.guilds)
        user_count = sum([g.member_count for g in bot.guilds])

        uptime_seconds = (datetime.datetime.utcnow() - PING_START_TIME).total_seconds() if PING_START_TIME else 0
        uptime_hours = uptime_seconds / 3600

        status_emoji = "✅" if latency_ms < 300 else "⚠️"

        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {status_emoji} Ping #{PING_COUNT}")
        print(f"  ├─ Latência: {latency_ms}ms")
        print(f"  ├─ Servidores: {guild_count} | Usuários: {user_count}")
        print(f"  ├─ Uptime: {uptime_hours:.2f}h ({uptime_seconds:.0f}s)")
        print(f"  └─ Erros: {PING_ERRORS}")

        LAST_PING_STATUS = "OK"

        db_set_config("last_ping_time", datetime.datetime.utcnow().isoformat())
        db_set_config("last_ping_latency", str(latency_ms))
        db_set_config("ping_count", str(PING_COUNT))
        db_set_config("ping_errors", str(PING_ERRORS))

    except Exception as e:
        PING_ERRORS += 1
        LAST_PING_STATUS = f"ERROR: {str(e)}"
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ❌ Erro no Ping: {e}")

@tasks.loop(seconds=300)
async def health_check_task():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM usuarios")
        user_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM partidas")
        match_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM filas WHERE jogadores != ''")
        active_queues = cur.fetchone()[0]

        conn.close()

        print(f"[HEALTH CHECK] ✅ DB OK | Users: {user_count} | Matches: {match_count} | Active Queues: {active_queues}")
    except Exception as e:
        print(f"[HEALTH CHECK] ❌ Database error: {e}")

# ❌ KEEP-ALIVE REMOVIDO - Desnecessário no Render
# O Render tem seu próprio sistema de health check
# Manter isso rodava overhead sem benefício

@tasks.loop(seconds=60)
async def auto_role_task():
    try:
        for guild in bot.guilds:
            guild_id = guild.id

            if not verificar_separador_servidor(guild_id):
                continue

            auto_role_id = get_auto_role(guild_id)

            if not auto_role_id:
                continue

            role = guild.get_role(auto_role_id)

            if not role:
                continue

            added_count = 0
            for member in guild.members:
                if not member.bot and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Auto-role configurado por {interaction.user}")
                        added_count += 1
                    except Exception as e:
                        print(f"Erro ao adicionar cargo a {member}: {e}")

            if added_count > 0:
                print(f"[AUTO ROLE] {added_count} membros receberam o cargo {role.name} em {guild.name}")

    except Exception as e:
        print(f"[AUTO ROLE] ❌ Erro no task: {e}")

@tasks.loop(seconds=1)
async def atualizar_fila_mediadores_task():
    """Atualiza a mensagem da fila de mediadores a cada 1 segundo"""
    try:
        for guild in bot.guilds:
            guild_id = guild.id
            
            if not verificar_separador_servidor(guild_id):
                continue
            
            msg_id = db_get_config(f"fila_mediadores_msg_id_{guild_id}")
            canal_id = db_get_config(f"fila_mediadores_canal_id_{guild_id}")
            
            if not msg_id or not canal_id:
                continue
            
            try:
                canal = guild.get_channel(int(canal_id))
                if not canal:
                    continue
                
                msg = await asyncio.wait_for(canal.fetch_message(int(msg_id)), timeout=1.0)
                mediadores = mediador_get_all(guild_id)
                
                embed = discord.Embed(
                    title=f"Bem-vindo(a) a #📦・fila-mediadores!",
                    description="Este é o começo do canal particular #📦・fila-mediadores.",
                    color=0x2f3136
                )
                
                if mediadores:
                    lista_text = "\n".join([f"{i+1}º. <@{med_id}>" for i, med_id in enumerate(mediadores)])
                    embed.add_field(name="Mediadores presentes:", value=lista_text, inline=False)
                else:
                    embed.add_field(name="Mediadores presentes:", value="Nenhum mediador disponível", inline=False)
                
                await msg.edit(embed=embed)
            except asyncio.TimeoutError:
                print(f"[FILA MEDIADORES] ⚠️ Timeout ao atualizar guild {guild_id}")
            except discord.NotFound:
                # Mensagem foi deletada, limpar configuração
                db_set_config(f"fila_mediadores_msg_id_{guild_id}", "")
                db_set_config(f"fila_mediadores_canal_id_{guild_id}", "")
            except Exception as e:
                print(f"[FILA MEDIADORES] ⚠️ Erro ao atualizar guild {guild_id}: {e}")
    
    except Exception as e:
        print(f"[FILA MEDIADORES] ❌ Erro geral no task: {e}")

@tasks.loop(seconds=300)
async def garbage_collector_task():
    """Limpeza de memória a cada 5 minutos - Remove objects obsoletos"""
    try:
        collected = gc.collect()
        print(f"🧹 [GC] Limpeza: {collected} objetos removidos")
    except Exception as e:
        print(f"🧹 [GC] ❌ Erro: {e}")

@tasks.loop(hours=24)
async def database_cleanup_task():
    """Limpeza de banco de dados a cada 24 horas - Remove dados obsoletos"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Limpar partidas finalizadas há mais de 7 dias
        data_limite = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()
        cur.execute("DELETE FROM partidas WHERE status IN ('finalizada', 'cancelada') AND criado_em < ?", (data_limite,))
        partidas_removidas = cur.rowcount
        
        # Limpar logs de partidas antigos (> 30 dias)
        data_limite_logs = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat()
        cur.execute("DELETE FROM logs_partidas WHERE timestamp < ?", (data_limite_logs,))
        logs_removidos = cur.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"🗑️ [DB CLEANUP] ✅ Limpeza concluída:")
        print(f"   📦 {partidas_removidas} partidas obsoletas removidas")
        print(f"   📝 {logs_removidos} logs antigos removidos")
        
    except Exception as e:
        print(f"🗑️ [DB CLEANUP] ❌ Erro: {e}")

async def enviar_mensagens_iniciais_logs():
    """Envia mensagens iniciais explicativas em todos os canais de log"""
    try:
        for guild in bot.guilds:
            categoria = None
            for cat in guild.categories:
                if "log" in cat.name.lower():
                    categoria = cat
                    break

            if not categoria:
                continue

            canais_logs = {
                "🔥 • log-criadas": {
                    "titulo": "📋 Log de Partidas Criadas",
                    "descricao": "**Log-criadas**: Partidas criadas pelo sistema\n\nEste canal registra automaticamente todas as partidas criadas quando dois jogadores entram na fila.\n\n**Filas registradas:** TODAS (1x1-mob, 1x1-emu, 2x2-mob, 2x2-emu, 2x2-misto, 3x3-mob, 3x3-emu, 3x3-misto, 4x4-mob, 4x4-emu, 4x4-misto)\n\n**Informações registradas:**\n• ID da partida\n• Jogadores\n• Mediador responsável\n• Valor da aposta\n• Tipo de fila\n• Data e hora",
                    "cor": 0xFF6B6B
                },
                "✅ • log-confirmadas": {
                    "titulo": "📋 Log de Partidas Confirmadas",
                    "descricao": "**Log-confirmadas**: Partidas confirmadas pelos jogadores\n\n⚠️ **EM DESENVOLVIMENTO**\n\nEste canal registrará partidas onde ambos os jogadores confirmaram.",
                    "cor": 0x4ECDC4
                },
                "🌐 • log-iniciadas": {
                    "titulo": "📋 Log de Partidas Iniciadas",
                    "descricao": "**Log-iniciadas**: Partidas com sala criada\n\n⚠️ **EM DESENVOLVIMENTO**\n\nEste canal registrará partidas onde o mediador criou a sala e enviou ID/senha.",
                    "cor": 0x95E1D3
                },
                "🏁 • logs-finalizadas": {
                    "titulo": "📋 Log de Partidas Finalizadas",
                    "descricao": "**Log-finalizadas**: Partidas com vencedor definido\n\n⚠️ **EM DESENVOLVIMENTO**\n\nEste canal registrará partidas que foram finalizadas com um vencedor.",
                    "cor": 0xF38181
                },
                "❌ • log-recusada": {
                    "titulo": "📋 Log de Partidas Recusadas",
                    "descricao": "**Log-recusadas**: Partidas recusadas ou canceladas\n\n⚠️ **EM DESENVOLVIMENTO**\n\nEste canal registrará partidas onde um jogador recusou ou a partida foi cancelada.",
                    "cor": 0xAA96DA
                }
            }

            for nome_canal, info in canais_logs.items():
                canal = discord.utils.get(categoria.channels, name=nome_canal)
                if canal:
                    try:
                        historico = await canal.history(limit=1, oldest_first=True).flatten()
                        if len(historico) == 0 or not historico[0].author.bot:
                            embed = discord.Embed(
                                title=info["titulo"],
                                description=info["descricao"],
                                color=info["cor"]
                            )
                            embed.set_footer(text="Bot Zeus - Sistema de Logs Automáticos")
                            await canal.send(embed=embed)
                            print(f"📝 Mensagem inicial enviada em {nome_canal} - {guild.name}")
                    except Exception as e:
                        print(f"❌ Erro ao enviar mensagem inicial em {nome_canal} - {guild.name}: {e}")
    except Exception as e:
        print(f"❌ Erro geral ao enviar mensagens iniciais: {e}")

# ==================== COMANDOS PREFIX ====================

class AuxMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📋 Ver Partidas Ativas", style=discord.ButtonStyle.primary, row=0)
    async def ver_partidas(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_aux_permitido(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!")
            return
        
        # Buscar canal configurado no /topico
        canal_id = db_get_config("canal_partidas_id")
        if not canal_id:
            await interaction.response.send_message("❌ Canal /topico não configurado! Configure primeiro com `/topico #canal`")
            return
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""SELECT id, jogador1, jogador2, valor, status, canal_id, thread_id
                       FROM partidas 
                       WHERE guild_id = ? AND status != 'finalizada' 
                       ORDER BY criado_em DESC LIMIT 10""", (interaction.guild.id,))
        partidas = cur.fetchall()
        conn.close()
        
        if not partidas:
            await interaction.response.send_message("❌ Nenhuma partida ativa no momento!")
            return
        
        embed = discord.Embed(
            title="📋 Partidas Ativas no /topico",
            description="Partidas vinculadas ao canal configurado:",
            color=0x2f3136
        )
        
        for partida_id, j1_id, j2_id, valor, status, p_canal_id, p_thread_id in partidas:
            # Buscar nomes dos jogadores
            j1 = interaction.guild.get_member(j1_id)
            j2 = interaction.guild.get_member(j2_id)
            
            j1_nome = j1.display_name if j1 else f"Player {j1_id}"
            j2_nome = j2.display_name if j2 else f"Player {j2_id}"
            
            embed.add_field(
                name=f"🎮 Partida {partida_id}",
                value=f"**Player 1:** {j1_nome} (ID: {j1_id})\n**Player 2:** {j2_nome} (ID: {j2_id})\n**Valor:** {fmt_valor(valor)}\n**Status:** {status}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @discord.ui.button(label="🏆 Definir Vencedor", style=discord.ButtonStyle.success, row=1)
    async def definir_vencedor(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_aux_permitido(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!")
            return
        
        modal = DefinirVencedorModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="⚠️ Vitória por W.O", style=discord.ButtonStyle.primary, row=1)
    async def vitoria_wo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_aux_permitido(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!")
            return
        
        modal = DefinirVencedorModal(is_wo=True)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔄 Criar Revanche", style=discord.ButtonStyle.secondary, row=2)
    async def criar_revanche(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_aux_permitido(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!")
            return
        
        modal = RevancheModal()
        await interaction.response.send_modal(modal)

class DefinirVencedorModal(Modal):
    def __init__(self, is_wo=False):
        titulo = "Vitória por W.O" if is_wo else "Definir Vencedor"
        super().__init__(title=titulo)
        self.is_wo = is_wo
        
        self.partida_id = TextInput(
            label="ID da Partida",
            placeholder="Digite o ID da partida",
            required=True,
            max_length=20
        )
        
        self.vencedor_choice = TextInput(
            label="Vencedor (1 ou 2)",
            placeholder="Digite 1 para Jogador 1, ou 2 para Jogador 2",
            required=True,
            max_length=1
        )
        
        self.add_item(self.partida_id)
        self.add_item(self.vencedor_choice)
    
    async def on_submit(self, interaction: discord.Interaction):
        partida_id = self.partida_id.value.strip()
        choice = self.vencedor_choice.value.strip()
        
        if choice not in ["1", "2"]:
            await interaction.response.send_message("❌ Digite apenas 1 ou 2!")
            return
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT jogador1, jogador2, valor FROM partidas WHERE id = ? AND guild_id = ?", 
                    (partida_id, interaction.guild.id))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            await interaction.response.send_message("❌ Partida não encontrada!")
            return
        
        j1_id, j2_id, valor = row
        vencedor_id = j1_id if choice == "1" else j2_id
        perdedor_id = j2_id if choice == "1" else j1_id
        
        # Buscar nomes
        j1 = interaction.guild.get_member(j1_id)
        j2 = interaction.guild.get_member(j2_id)
        vencedor = interaction.guild.get_member(vencedor_id)
        perdedor = interaction.guild.get_member(perdedor_id)
        
        j1_nome = j1.display_name if j1 else f"Player {j1_id}"
        j2_nome = j2.display_name if j2 else f"Player {j2_id}"
        vencedor_nome = vencedor.display_name if vencedor else f"Player {vencedor_id}"
        perdedor_nome = perdedor.display_name if perdedor else f"Player {perdedor_id}"
        
        titulo = "⚠️ Confirmar Vitória por W.O" if self.is_wo else "⚠️ Confirmar Vencedor"
        
        embed = discord.Embed(
            title=titulo,
            description=f"**Partida:** {partida_id}\n**Valor:** {fmt_valor(valor)}",
            color=0xFFAA00
        )
        embed.add_field(
            name="Player 1", 
            value=f"{j1_nome}\n(ID: {j1_id})", 
            inline=True
        )
        embed.add_field(
            name="Player 2", 
            value=f"{j2_nome}\n(ID: {j2_id})", 
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(
            name="🏆 Vencedor", 
            value=f"{vencedor_nome}\n<@{vencedor_id}>", 
            inline=True
        )
        embed.add_field(
            name="💔 Perdedor", 
            value=f"{perdedor_nome}\n<@{perdedor_id}>", 
            inline=True
        )
        
        view = ConfirmarVencedorAuxView(partida_id, vencedor_id, perdedor_id, self.is_wo)
        await interaction.response.send_message(embed=embed, view=view)

class ConfirmarVencedorAuxView(View):
    def __init__(self, partida_id: str, vencedor_id: int, perdedor_id: int, is_wo=False):
        super().__init__(timeout=None)
        self.partida_id = partida_id
        self.vencedor_id = vencedor_id
        self.perdedor_id = perdedor_id
        self.is_wo = is_wo
    
    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        
        usuario_add_coins(guild_id, self.vencedor_id, COIN_POR_VITORIA)
        usuario_add_vitoria(guild_id, self.vencedor_id)
        usuario_add_derrota(guild_id, self.perdedor_id)
        
        status_final = 'finalizada_wo' if self.is_wo else 'finalizada'
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE partidas SET vencedor = ?, status = ? WHERE id = ?", 
                    (self.vencedor_id, status_final, self.partida_id))
        conn.commit()
        conn.close()
        
        tipo_msg = "W.O" if self.is_wo else "Vencedor"
        
        await interaction.response.edit_message(
            content=f"✅ {tipo_msg} confirmado: <@{self.vencedor_id}>!\n+{COIN_POR_VITORIA} coin(s) e +1 vitória adicionados!",
            embed=None,
            view=None
        )
    
    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Cancelado!", embed=None, view=None)

class RevancheModal(Modal):
    def __init__(self):
        super().__init__(title="Criar Revanche")
        
        self.partida_id = TextInput(
            label="ID da Partida",
            placeholder="Digite o ID da partida",
            required=True,
            max_length=20
        )
        
        self.novo_valor = TextInput(
            label="Novo Valor",
            placeholder="Ex: 10.00",
            required=True,
            max_length=10
        )
        
        self.sala_id = TextInput(
            label="ID da Sala",
            placeholder="Digite o ID da nova sala",
            required=True,
            max_length=50
        )
        
        self.senha = TextInput(
            label="Senha da Sala",
            placeholder="Digite a senha da sala",
            required=True,
            max_length=50
        )
        
        self.add_item(self.partida_id)
        self.add_item(self.novo_valor)
        self.add_item(self.sala_id)
        self.add_item(self.senha)
    
    async def on_submit(self, interaction: discord.Interaction):
        partida_id = self.partida_id.value.strip()
        
        try:
            valor_str = self.novo_valor.value.replace(",", ".")
            novo_valor = float(valor_str)
            
            if novo_valor <= 0 or novo_valor > 100:
                await interaction.response.send_message("❌ O valor deve estar entre R$ 0,01 e R$ 100,00!")
                return
            
            novo_valor = round(novo_valor, 2)
        except ValueError:
            await interaction.response.send_message("❌ Valor inválido! Use apenas números (ex: 10.00)")
            return
        
        sala_id = self.sala_id.value.strip()
        senha = self.senha.value.strip()
        
        if not sala_id or not senha:
            await interaction.response.send_message("❌ ID e senha da sala são obrigatórios!")
            return
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT jogador1, jogador2, valor FROM partidas WHERE id = ? AND guild_id = ?", 
                    (partida_id, interaction.guild.id))
        row = cur.fetchone()
        
        if not row:
            conn.close()
            await interaction.response.send_message("❌ Partida não encontrada!")
            return
        
        j1_id, j2_id, valor_antigo = row
        
        cur.execute("UPDATE partidas SET valor = ?, sala_id = ?, sala_senha = ? WHERE id = ? AND guild_id = ?", 
                   (novo_valor, sala_id, senha, partida_id, interaction.guild.id))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="🔄 Revanche Criada",
            description=f"**Partida:** {partida_id}\n**Valor Anterior:** {fmt_valor(valor_antigo)}\n**Novo Valor:** {fmt_valor(novo_valor)}",
            color=0x00FF00
        )
        embed.add_field(name="🎮 Jogadores", value=f"<@{j1_id}> vs <@{j2_id}>", inline=False)
        embed.add_field(name="🆔 ID da Sala", value=f"{sala_id}", inline=True)
        embed.add_field(name="🔐 Senha", value=f"{senha}", inline=True)
        
        await interaction.response.send_message(embed=embed)

@bot.command(name="pixmed")
async def cmd_pixmed(ctx):
    """Configurar PIX do mediador - Painel completo"""
    if not verificar_separador_servidor(ctx.guild.id):
        await ctx.send("⛔ **Servidor não registrado!**")
        return
    
    # Data e hora de Brasília (UTC-3)
    from datetime import timezone, timedelta
    brasilia_tz = timezone(timedelta(hours=-3))
    data_brasilia = datetime.datetime.now(brasilia_tz).strftime("%d/%m/%Y %H:%M")
    
    embed = discord.Embed(
        title="💰 Envie sua chave Pix",
        description=(
            "• **Sistema de automatização de pagamentos!**\n\n"
            "• **Como funciona?**\n\n"
            "O sistema de automatização de pagamentos é essencial para que todos os mediadores "
            "garantam a agilidade nas partidas abertas. Após configurar, nunca mais precisará enviar "
            "novamente sua chave PIX nas salas criadas. Eu farei todo o trabalho!\n\n"
            f"[ZEROTAXA] SALAO,00 | Automatização de Pagamentos | {data_brasilia}"
        ),
        color=0x2f3136
    )
    
    view = ConfigurarPIXView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="p")
async def cmd_perfil(ctx, *, membro: str = None):
    """Ver perfil e estatísticas de um jogador"""
    if not ctx.guild or not verificar_separador_servidor(ctx.guild.id):
        await ctx.send("⛔ **Servidor não registrado ou comando usado fora de um servidor!**")
        return
    
    # Tentar converter menção/ID/nome para membro
    usuario = None
    user_id_for_fetch = None
    
    if membro:
        try:
            # Tentar converter menção ou ID
            if membro.startswith('<@') and membro.endswith('>'):
                user_id_for_fetch = int(membro[2:-1].replace('!', ''))
            elif membro.isdigit():
                user_id_for_fetch = int(membro)
            
            # Se temos um ID, tentar buscar o membro (cache primeiro, depois API)
            if user_id_for_fetch:
                usuario = ctx.guild.get_member(user_id_for_fetch)
                if not usuario:
                    try:
                        usuario = await ctx.guild.fetch_member(user_id_for_fetch)
                    except discord.NotFound:
                        # Membro não está no servidor, mas pode ter dados históricos
                        try:
                            usuario = await ctx.bot.fetch_user(user_id_for_fetch)
                        except:
                            pass
                    except:
                        pass
            else:
                # Buscar por nome/nick no cache
                usuario = discord.utils.find(lambda m: m.name.lower() == membro.lower() or (m.nick and m.nick.lower() == membro.lower()), ctx.guild.members)
        except Exception:
            pass
        
        if not usuario:
            await ctx.send(f"❌ Usuário `{membro}` não encontrado!")
            return
    else:
        usuario = ctx.author
    
    guild_id = ctx.guild.id
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""SELECT coins, vitorias, derrotas FROM usuarios 
                       WHERE guild_id = ? AND user_id = ?""", (guild_id, usuario.id))
        row = cur.fetchone()
        conn.close()
    except sqlite3.Error as e:
        await ctx.send(f"❌ Erro ao buscar dados no banco: {e}")
        return
    except Exception as e:
        await ctx.send(f"❌ Erro inesperado: {e}")
        return
    
    embed = discord.Embed(
        title=f"📊 Perfil de {usuario.display_name}",
        color=0x2f3136
    )
    
    if not row:
        coins, vitorias, derrotas = 0, 0, 0
    else:
        coins, vitorias, derrotas = row
    
    total_partidas = vitorias + derrotas
    winrate = (vitorias / total_partidas * 100) if total_partidas > 0 else 0
    
    embed.add_field(name="💰 Coins", value=f"{coins}", inline=True)
    embed.add_field(name="🏆 Vitórias", value=f"{vitorias}", inline=True)
    embed.add_field(name="💔 Derrotas", value=f"{derrotas}", inline=True)
    embed.add_field(name="📈 Winrate", value=f"{winrate:.1f}%", inline=True)
    embed.add_field(name="🎮 Total de Partidas", value=f"{total_partidas}", inline=True)
    
    if usuario.avatar:
        embed.set_thumbnail(url=usuario.avatar.url)
    
    await ctx.send(embed=embed)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    channel = message.channel
    if not channel or not hasattr(channel, 'id'):
        return
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, mediador, estado_sala, guild_id
            FROM partidas 
            WHERE (canal_id = ? OR thread_id = ?) 
            AND estado_sala IS NOT NULL
            AND (estado_sala = 'aguardando_id' OR estado_sala = 'aguardando_senha')
        """, (channel.id, channel.id))
        partida_row = cur.fetchone()
        
        if not partida_row:
            conn.close()
            await bot.process_commands(message)
            return
        
        partida_id, mediador_id, estado_sala, guild_id = partida_row
        
        if message.author.id != mediador_id:
            conn.close()
            await bot.process_commands(message)
            return
        
        conteudo = message.content.strip()
        
        if estado_sala == 'aguardando_id':
            if conteudo.isdigit() and 6 <= len(conteudo) <= 13:
                await message.add_reaction('✔️')
                cur.execute("""
                    UPDATE partidas 
                    SET estado_sala = 'aguardando_senha', sala_id = ?
                    WHERE id = ?
                """, (conteudo, partida_id))
                conn.commit()
                await message.channel.send(f"✅ ID {conteudo} salvo! Agora digite a senha (1-4 dígitos):")
            else:
                await message.add_reaction('❌')
                await message.channel.send(f"❌ ID inválido! Deve ter 6-13 dígitos.")
        
        elif estado_sala == 'aguardando_senha':
            if conteudo.isdigit() and 1 <= len(conteudo) <= 4:
                await message.add_reaction('✔️')
                cur.execute("""
                    UPDATE partidas 
                    SET estado_sala = 'sala_criada', sala_senha = ?
                    WHERE id = ?
                """, (conteudo, partida_id))
                conn.commit()
                
                cur.execute("SELECT sala_id FROM partidas WHERE id = ?", (partida_id,))
                sala_id_row = cur.fetchone()
                sala_id = sala_id_row[0] if sala_id_row else "???"
                
                embed = discord.Embed(
                    title="✅ Sala Criada!",
                    color=0x2f3136
                )
                embed.add_field(name="🆔 ID da Sala", value=sala_id, inline=False)
                embed.add_field(name="🔐 Senha", value=conteudo, inline=False)
                await message.channel.send(embed=embed)
            else:
                await message.add_reaction('❌')
                await message.channel.send(f"❌ Senha inválida! Deve ter 1-4 dígitos.")
        
        conn.close()
    except Exception as e:
        print(f"❌ Erro em on_message: {e}")
        import traceback
        traceback.print_exc()
    
    await bot.process_commands(message)

@bot.event
async def on_ready():
    global BOT_OWNER_ID, PING_START_TIME

    init_db()

    saved_start_time = db_get_config("bot_start_time")
    if saved_start_time:
        try:
            PING_START_TIME = datetime.datetime.fromisoformat(saved_start_time)
            print(f"⏰ Uptime restaurado: {saved_start_time}")
        except:
            PING_START_TIME = datetime.datetime.utcnow()
            db_set_config("bot_start_time", PING_START_TIME.isoformat())
            print(f"⏰ Novo uptime iniciado: {PING_START_TIME.isoformat()}")
    else:
        PING_START_TIME = datetime.datetime.utcnow()
        db_set_config("bot_start_time", PING_START_TIME.isoformat())
        print(f"⏰ Uptime iniciado: {PING_START_TIME.isoformat()}")

    print("🔄 Iniciando sincronização de comandos slash...")

    # Sincronizar globalmente (sem limpar comandos antes!)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"📝 Tentativa {attempt + 1}/{max_retries} de sincronização global...")
            synced = await tree.sync()
            print(f'✅ SUCESSO: {len(synced)} comandos slash sincronizados globalmente!')
            print(f'⚡ Comandos disponíveis em TODOS os servidores!')
            print(f'📋 Total de comandos: {len(tree.get_commands())}')
            break
        except discord.HTTPException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f'⚠️ Rate limit detectado, aguardando {wait_time}s...')
                await asyncio.sleep(wait_time)
            else:
                print(f'❌ Falha na sincronização após {max_retries} tentativas: {e}')
        except Exception as e:
            print(f'❌ Erro inesperado na sincronização: {e}')
            if attempt == max_retries - 1:
                print(f'⚠️ Continuando sem sincronização completa...')

    # Listar comandos prefix
    print(f'📝 Comandos prefix registrados: {len(bot.commands)}')

    # Define status de presença do bot
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Filas 1v1 | /manual"
        ),
        status=discord.Status.online
    )
    print(f'✅ Status de presença definido: Online - Watching Filas 1v1')

    ping_task.start()
    health_check_task.start()
    # keep_alive_task.start()  # ❌ REMOVIDO - Desnecessário no Render, gera overhead
    rotacao_mediadores_task.start()
    auto_role_task.start()
    garbage_collector_task.start()
    database_cleanup_task.start()
    atualizar_fila_mediadores_task.start()

    print(f"🔄 Tasks iniciados:")
    print(f"  ├─ Ping: a cada 30s")
    print(f"  ├─ Health Check: a cada 5min")
    print(f"  ├─ Rotação Mediadores: a cada 30s")
    print(f"  ├─ Auto Role: a cada 60s")
    print(f"  ├─ Fila Mediadores: a cada 10s")
    print(f"  ├─ Garbage Collector: a cada 5min")
    print(f"  └─ Database Cleanup: a cada 24h")

    await enviar_mensagens_iniciais_logs()

    # Registrar Views Persistentes
    bot.add_view(ConfigurarPIXView())
    bot.add_view(FilaMediadoresView())

    print(f'Bot conectado como {bot.user}')
    print(f'ID: {bot.user.id}')

    for guild in bot.guilds:
        for member in guild.members:
            if member.name == BOT_OWNER_USERNAME or str(member) == BOT_OWNER_USERNAME:
                BOT_OWNER_ID = member.id
                print(f'Owner encontrado: {member} (ID: {BOT_OWNER_ID})')
                break
        if BOT_OWNER_ID:
            break

    if not BOT_OWNER_ID:
        print(f'⚠️ Owner {BOT_OWNER_USERNAME} não encontrado!')

    print('Bot pronto!')

async def ping_handler(request):
    """Endpoint otimizado para Cron-Job.org e serviços de uptime"""
    # Registra timestamp do ping externo
    db_set_config("last_external_ping", datetime.datetime.utcnow().isoformat())
    
    # Informações úteis para debugging
    uptime_seconds = (datetime.datetime.utcnow() - PING_START_TIME).total_seconds() if PING_START_TIME else 0
    uptime_hours = uptime_seconds / 3600
    
    # Resposta simples e rápida para compatibilidade máxima
    response_text = f"pong | uptime: {uptime_hours:.2f}h | status: ok"
    
    print(f"[PING EXTERNO] ✅ Recebido de {request.remote} | Uptime: {uptime_hours:.2f}h")
    
    return web.Response(
        text=response_text,
        status=200,
        headers={
            'Content-Type': 'text/plain',
            'X-Bot-Uptime-Hours': str(round(uptime_hours, 2)),
            'X-Bot-Status': 'healthy'
        }
    )

async def health_handler(request):
    """Health check detalhado com métricas do sistema"""
    import json

    uptime_seconds = (datetime.datetime.utcnow() - PING_START_TIME).total_seconds() if PING_START_TIME else 0
    
    # Verifica último ping externo
    last_external_ping_str = db_get_config("last_external_ping")
    external_ping_age_minutes = None
    external_ping_status = "never"
    
    if last_external_ping_str:
        try:
            last_external_ping = datetime.datetime.fromisoformat(last_external_ping_str)
            time_since_external = (datetime.datetime.utcnow() - last_external_ping).total_seconds()
            external_ping_age_minutes = round(time_since_external / 60, 2)
            external_ping_status = "healthy" if time_since_external < 360 else "stale"
        except:
            external_ping_status = "error"
    
    health_data = {
        "status": "healthy",
        "bot_name": str(bot.user) if bot.user else "Not Connected",
        "latency_ms": round(bot.latency * 1000, 2) if bot.is_ready() else -1,
        "guilds": len(bot.guilds),
        "users": sum([g.member_count for g in bot.guilds]) if bot.guilds else 0,
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_hours": round(uptime_seconds / 3600, 2),
        "ping_count": PING_COUNT,
        "ping_errors": PING_ERRORS,
        "last_ping_status": LAST_PING_STATUS,
        "external_ping_status": external_ping_status,
        "external_ping_age_minutes": external_ping_age_minutes,
        "keep_alive_status": db_get_config("keep_alive_status") or "unknown",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "endpoints": {
            "ping": "/ping - Simple ping (200ms timeout)",
            "health": "/health - Health check detalhado",
            "stats": "/stats - Estatísticas do banco de dados"
        }
    }
    
    print(f"[HEALTH CHECK] Requisição de {request.remote} | Uptime: {health_data['uptime_hours']}h")
    
    return web.Response(
        text=json.dumps(health_data, indent=2),
        content_type='application/json',
        status=200,
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'X-Bot-Status': 'healthy'
        }
    )

async def stats_handler(request):
    import json

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM usuarios")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM partidas")
        total_matches = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM filas WHERE jogadores != ''")
        active_queues = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM fila_mediadores")
        mediators = cur.fetchone()[0]

        conn.close()

        stats_data = {
            "total_users": total_users,
            "total_matches": total_matches,
            "active_queues": active_queues,
            "mediators": mediators
        }

        return web.Response(
            text=json.dumps(stats_data, indent=2),
            content_type='application/json',
            status=200
        )
    except Exception as e:
        return web.Response(
            text=json.dumps({"error": str(e)}),
            content_type='application/json',
            status=500
        )

async def status_handler(request):
    """Endpoint simples para verificação rápida de status"""
    uptime_seconds = (datetime.datetime.utcnow() - PING_START_TIME).total_seconds() if PING_START_TIME else 0
    
    status_text = (
        f"✅ Bot Online\n"
        f"Uptime: {uptime_seconds / 3600:.2f}h\n"
        f"Latency: {round(bot.latency * 1000, 2)}ms\n"
        f"Servers: {len(bot.guilds)}\n"
        f"Status: Healthy"
    )
    
    return web.Response(
        text=status_text,
        status=200,
        headers={'Content-Type': 'text/plain'}
    )

async def start_web_server():
    app = web.Application()
    
    # Endpoints principais (compatíveis com Cron-Job.org)
    app.router.add_get('/ping', ping_handler)
    app.router.add_get('/', ping_handler)  # Root também retorna ping
    
    # Endpoints de monitoramento detalhado
    app.router.add_get('/health', health_handler)
    app.router.add_get('/api/health', health_handler)
    app.router.add_get('/status', status_handler)
    
    # Endpoints de estatísticas
    app.router.add_get('/stats', stats_handler)
    app.router.add_get('/api/stats', stats_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Porta fixa: 5000
    port = 5000
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f'✅ Servidor HTTP rodando na porta {port}')
    print(f'  ├─ GET /ping - Ping otimizado (Cron-Job.org compatible)')
    print(f'  ├─ GET /status - Status rápido em texto')
    print(f'  ├─ GET /health - Health check JSON detalhado')
    print(f'  └─ GET /stats - Estatísticas do banco de dados')
    print(f'')
    print(f'📋 Configuração recomendada para Cron-Job.org:')
    print(f'  ├─ URL: https://seu-repl.replit.dev/ping')
    print(f'  ├─ Intervalo: 5 minutos')
    print(f'  ├─ Timeout: 30 segundos')
    print(f'  └─ Palavra-chave esperada: "pong"')
    
    # Salvar porta usada no banco para o keep-alive
    db_set_config("http_server_port", str(port))
    
    # ✅ CRÍTICO: Manter o servidor rodando ETERNAMENTE
    # Sem isso, a função termina e a porta é fechada!
    await asyncio.sleep(float('inf'))

async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ ERRO: Token do Discord não encontrado!")
        print("Configure o secret DISCORD_TOKEN")
        exit(1)

    # ✅ Inicia servidor web em BACKGROUND (executa SIMULTANEAMENTE com o bot)
    asyncio.create_task(start_web_server())
    
    # ✅ Bot roda em FOREGROUND (bloqueante, conecta ao Discord)
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())