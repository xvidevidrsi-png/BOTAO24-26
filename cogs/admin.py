import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import datetime
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DB_FILE = "bot_zeus.db"

def get_connection():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_FILE, timeout=1.0)

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

def is_admin(user_id, guild=None, member=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def admin_add(user_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO admins (user_id, adicionado_em) VALUES (?, ?)", 
                   (user_id, datetime.datetime.utcnow().isoformat()))
        conn.commit()
    finally:
        conn.close()

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_owner", description="👑 Adiciona um novo dono ao bot")
    @app_commands.describe(user="Mencionar usuário ou colocar username/ID")
    async def add_owner(self, interaction: discord.Interaction, user: discord.User = None):
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return
            
        if user is None:
            await interaction.response.send_message("❌ Você deve mencionar um usuário ou fornecer o ID!", ephemeral=True)
            return

        admin_add(user.id)
        embed = discord.Embed(
            title="👑 Novo Dono Adicionado",
            description=f"{user.mention} agora é DONO do Bot Zeus!",
            color=0x2f3136
        )
        embed.add_field(name="👤 ID", value=user.id, inline=True)
        embed.add_field(name="🎯 Username", value=user.name, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="separador_de_servidor", description="⚙️ REGISTRA servidor no sistema")
    @app_commands.describe(
        id_servidor="ID numérico do servidor Discord",
        nome_dono="Nome do dono do servidor"
    )
    async def separador_servidor(self, interaction: discord.Interaction, id_servidor: str, nome_dono: str):
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        db_set_config(f"servidor_registrado_{guild_id}", "true")
        db_set_config(f"dono_{guild_id}", nome_dono)
        
        embed = discord.Embed(
            title="✅ Servidor Registrado!",
            description=f"Servidor **{interaction.guild.name}** foi registrado com sucesso!",
            color=0x2f3136
        )
        embed.add_field(name="🏠 Servidor", value=interaction.guild.name, inline=True)
        embed.add_field(name="👤 Dono", value=nome_dono, inline=True)
        embed.add_field(name="📌 ID", value=guild_id, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="topico", description="📂 Define o canal para threads de partidas")
    @app_commands.describe(canal="Canal onde as threads serão criadas")
    async def set_canal(self, interaction: discord.Interaction, canal: discord.TextChannel):
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return

        db_set_config("canal_partidas_id", str(canal.id))
        db_set_config("usar_threads", "true")
        await interaction.response.send_message(f"✅ Canal de threads definido: {canal.mention}", ephemeral=True)

    @app_commands.command(name="aux_config", description="🎤 Define o cargo de mediador/auxiliar")
    @app_commands.describe(cargo="Cargo que será mediador")
    async def aux_config(self, interaction: discord.Interaction, cargo: discord.Role):
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return

        db_set_config("aux_role_id", str(cargo.id))
        await interaction.response.send_message(f"✅ Cargo aux definido: {cargo.mention}", ephemeral=True)

    @app_commands.command(name="configurar", description="🎤 Define quais cargos serão mencionados nas partidas")
    @app_commands.describe(cargos="IDs dos cargos separados por vírgula")
    async def configurar_cargos(self, interaction: discord.Interaction, cargos: str):
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return

        db_set_config("cargos_mencionar", cargos)
        await interaction.response.send_message("✅ Cargos configurados!", ephemeral=True)

    @app_commands.command(name="definir", description="💰 Altera os valores de TODAS as filas")
    @app_commands.describe(valores="Valores separados por vírgula (ex: 100,50,40)")
    async def definir_valores(self, interaction: discord.Interaction, valores: str):
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return

        db_set_config("valores_filas", valores)
        await interaction.response.send_message(f"✅ Valores alterados: {valores}", ephemeral=True)

    @app_commands.command(name="taxa", description="Altera a taxa por jogador")
    @app_commands.describe(valor="Novo valor da taxa (ex: 0.15)")
    async def taxa_comando(self, interaction: discord.Interaction, valor: str):
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return

        db_set_config("taxa_por_jogador", valor)
        await interaction.response.send_message(f"✅ Taxa alterada para: {valor}", ephemeral=True)

    @app_commands.command(name="manual", description="📖 Manual completo do bot com todos os comandos")
    async def config_menu(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Manual Bot Zeus",
            description="Comandos disponíveis",
            color=0x2f3136
        )
        embed.add_field(name="📱 Filas", value="/1x1-mob, /1x1-emulador, /2x2-emu, /3x3-emu, /4x4-emu, /2x2-mob, /3x3-mob, /4x4-mob", inline=False)
        embed.add_field(name="🎮 Filas Misto", value="/filamisto-2x2, /filamisto-3x3, /filamisto-4x4", inline=False)
        embed.add_field(name="👨‍⚖️ Mediador", value="/fila_mediadores, /rank", inline=False)
        embed.add_field(name="⚙️ Admin", value="/separador_de_servidor, /topico, /aux_config, /configurar, /definir, /taxa, /add_owner", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
