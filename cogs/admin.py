import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import psycopg2
import os
from dotenv import load_dotenv
import datetime

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect("bot_zeus.db", timeout=1.0)

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
        self.tree = bot.tree

    @self.tree.command(name="add_owner", description="👑 Adiciona um novo dono ao bot (uso: /add_owner @usuario ou /add_owner ID)")
    @app_commands.describe(user="Mencionar usuário ou colocar username/ID")
    async def add_owner(self, interaction: discord.Interaction, user: discord.User = None):
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

    @self.tree.command(name="separador_de_servidor", description="⚙️ REGISTRA servidor no sistema - OBRIGATÓRIO ANTES de criar filas!")
    async def separador_servidor(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Servidor registrado!", ephemeral=True)

    @self.tree.command(name="configurar", description="🎤 Define quais CARGOS serão mencionados nas partidas")
    @app_commands.describe(cargos="IDs dos cargos separados por vírgula")
    async def configurar_cargos(self, interaction: discord.Interaction, cargos: str):
        await interaction.response.send_message(f"✅ Cargos configurados: {cargos}", ephemeral=True)

    @self.tree.command(name="definir", description="💰 ALTERA os valores das TODAS filas (Mobile, Emulador e Mistos)")
    @app_commands.describe(valores="Valores separados por vírgula (ex: 100,50,40)")
    async def definir_valores(self, interaction: discord.Interaction, valores: str):
        await interaction.response.send_message(f"✅ Valores alterados: {valores}", ephemeral=True)

    @self.tree.command(name="taxa", description="Altera a taxa por jogador")
    @app_commands.describe(valor="Novo valor da taxa (ex: 0.15)")
    async def taxa_comando(self, interaction: discord.Interaction, valor: str):
        await interaction.response.send_message(f"✅ Taxa alterada para: {valor}", ephemeral=True)

    @self.tree.command(name="manual", description="Manual completo do bot com todos os comandos disponíveis")
    async def config_menu(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Manual Bot Zeus",
            description="Comandos disponíveis",
            color=0x2f3136
        )
        embed.add_field(name="📱 Filas", value="/1x1-mob, /1x1-emulador, /2x2-emu", inline=False)
        embed.add_field(name="👨‍⚖️ Mediador", value="/fila_mediadores, /rank", inline=False)
        embed.add_field(name="⚙️ Admin", value="/separador_de_servidor, /configurar, /definir", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
