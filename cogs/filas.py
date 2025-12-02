import discord
from discord.ext import commands
from discord import app_commands
import os
import datetime
import sqlite3
import asyncio
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DB_FILE = "bot_zeus.db"
VALORES_FILAS_1V1 = [100.00, 50.00, 40.00, 30.00, 20.00, 10.00, 5.00, 3.00, 2.00, 1.00, 0.80, 0.40]

def get_connection():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_FILE, timeout=1.0)

def db_get_config(k):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT v FROM config WHERE k = ?", (k,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def db_set_config(k, v):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO config (k,v) VALUES (?,?)", (k, v))
    conn.commit()
    conn.close()

def fmt_valor(v):
    if v >= 1:
        return f"R$ {v:.2f}"
    return f"R$ {v:.2f}"

def is_admin(user_id, guild=None, member=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def verificar_separador_servidor(guild_id):
    return db_get_config(f"servidor_registrado_{guild_id}") is not None

def fila_add_jogador(guild_id, valor, modo, user_id, tipo_jogo='mob'):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", 
                   (guild_id, valor, modo, tipo_jogo))
        row = cur.fetchone()
        jogadores = []
        if row and row[0]:
            jogadores = [int(x) for x in row[0].split(",") if x.strip().isdigit()]
        if user_id not in jogadores:
            jogadores.append(user_id)
        cur.execute("UPDATE filas SET jogadores = ? WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", 
                   (",".join(str(x) for x in jogadores), guild_id, valor, modo, tipo_jogo))
        conn.commit()
    finally:
        conn.close()
    return jogadores

def fila_remove_jogador(guild_id, valor, modo, user_id, tipo_jogo='mob'):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", 
                   (guild_id, valor, modo, tipo_jogo))
        row = cur.fetchone()
        jogadores = []
        if row and row[0]:
            jogadores = [int(x) for x in row[0].split(",") if x.strip().isdigit()]
        if user_id in jogadores:
            jogadores.remove(user_id)
        cur.execute("UPDATE filas SET jogadores = ? WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", 
                   (",".join(str(x) for x in jogadores) if jogadores else "", guild_id, valor, modo, tipo_jogo))
        conn.commit()
    finally:
        conn.close()
    return jogadores

def fila_get_jogadores(guild_id, valor, modo, tipo_jogo='mob'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT jogadores FROM filas WHERE guild_id = ? AND valor = ? AND modo = ? AND tipo_jogo = ?", 
               (guild_id, valor, modo, tipo_jogo))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        return [int(x) for x in row[0].split(",")]
    return []

def registrar_historico_fila(guild_id, valor, modo, tipo_jogo, acao):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO historico_filas (guild_id, valor, modo, tipo_jogo, acao, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, valor, modo, tipo_jogo, acao, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

class FilaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="1x1-mob", description="📱 Cria FILAS de 1v1 MOBILE com todos os valores definidos")
    async def criar_filas_1v1(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Este comando só funciona em servidores!", ephemeral=True)
            return
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro para registrar seu servidor.", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return
        
        canal_id = db_get_config("canal_partidas_id")
        if not canal_id:
            await interaction.response.send_message("❌ Canal não configurado! Use `/topico` primeiro.", ephemeral=True)
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
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="🔴 Gel Normal", value="Nenhum jogador", inline=True)
            embed.add_field(name="🔵 Gel Infinito", value="Nenhum jogador", inline=True)
            
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, 'normal', 'mob', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, 'infinito', 'mob', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
            registrar_historico_fila(guild_id, valor, "normal", "mob", "criada")
            registrar_historico_fila(guild_id, valor, "infinito", "mob", "criada")
        
        await interaction.followup.send("✅ Filas 1x1 Mobile criadas!", ephemeral=True)

    @app_commands.command(name="1x1-emulador", description="🖥️ Cria FILAS de 1v1 EMULADOR")
    async def criar_filas_1x1_emu(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="1v1 Emulador", description=f"**Modo**\n1v1 Emulador\n\n**Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="🔴 Gel Normal", value="Nenhum", inline=True)
            embed.add_field(name="🔵 Gel Infinito", value="Nenhum", inline=True)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, 'normal', 'emu', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, 'infinito', 'emu', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 1x1 Emulador criadas!", ephemeral=True)

    @app_commands.command(name="2x2-emu", description="👥 Cria FILAS de 2x2 EMULADOR")
    async def criar_filas_2x2_emu(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Emulador", description=f"🎮 **Modo**\n2X2 EMULADOR\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="🎮 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, '2x2-emu', 'emu', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 2x2 Emulador criadas!", ephemeral=True)

    @app_commands.command(name="3x3-emu", description="👥 Cria FILAS de 3x3 EMULADOR")
    async def criar_filas_3x3_emu(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Emulador", description=f"🎮 **Modo**\n3X3 EMULADOR\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="🎮 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, '3x3-emu', 'emu', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 3x3 Emulador criadas!", ephemeral=True)

    @app_commands.command(name="4x4-emu", description="👥 Cria FILAS de 4x4 EMULADOR")
    async def criar_filas_4x4_emu(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Emulador", description=f"🎮 **Modo**\n4X4 EMULADOR\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="🎮 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, '4x4-emu', 'emu', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 4x4 Emulador criadas!", ephemeral=True)

    @app_commands.command(name="2x2-mob", description="📱 Cria FILAS de 2x2 MOBILE")
    async def criar_filas_2x2_mob(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Mobile", description=f"🎮 **Modo**\n2X2 MOBILE\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="🎮 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, '2x2-mob', 'mob', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 2x2 Mobile criadas!", ephemeral=True)

    @app_commands.command(name="3x3-mob", description="📱 Cria FILAS de 3x3 MOBILE")
    async def criar_filas_3x3_mob(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Mobile", description=f"🎮 **Modo**\n3X3 MOBILE\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="🎮 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, '3x3-mob', 'mob', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 3x3 Mobile criadas!", ephemeral=True)

    @app_commands.command(name="4x4-mob", description="📱 Cria FILAS de 4x4 MOBILE")
    async def criar_filas_4x4_mob(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Mobile", description=f"🎮 **Modo**\n4X4 MOBILE\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="🎮 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, jogadores, msg_id, criado_em) VALUES (?, ?, '4x4-mob', 'mob', '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 4x4 Mobile criadas!", ephemeral=True)

    @app_commands.command(name="filamisto-2x2", description="🎮 Cria FILAS de 2x2 MISTO")
    async def criar_filas_misto_2x2(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Misto", description=f"🎮 **Modo**\n2X2-MISTO\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="👥 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, vagas_emu, jogadores, msg_id, criado_em) VALUES (?, ?, '2x2-misto_1emu', 'misto', 1, '', ?, ?)",
                       (guild_id, valor, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 2x2 Misto criadas!", ephemeral=True)

    @app_commands.command(name="filamisto-3x3", description="🎮 Cria FILAS de 3x3 MISTO")
    async def criar_filas_misto_3x3(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Misto", description=f"🎮 **Modo**\n3X3-MISTO\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="👥 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            for vagas in [1, 2]:
                cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, vagas_emu, jogadores, msg_id, criado_em) VALUES (?, ?, ?, 'misto', ?, '', ?, ?)",
                           (guild_id, valor, f"3x3-misto_{vagas}emu", vagas, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 3x3 Misto criadas!", ephemeral=True)

    @app_commands.command(name="filamisto-4x4", description="🎮 Cria FILAS de 4x4 MISTO")
    async def criar_filas_misto_4x4(self, interaction: discord.Interaction):
        if not verificar_separador_servidor(interaction.guild.id):
            await interaction.response.send_message("⛔ **Servidor não registrado!**\n\nUse `/separador_de_servidor` primeiro!", ephemeral=True)
            return
        if not is_admin(interaction.user.id, member=interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        canal = interaction.channel
        
        for valor in VALORES_FILAS_1V1:
            embed = discord.Embed(title="Filas Misto", description=f"🎮 **Modo**\n4X4-MISTO\n\n💰 **Valor**\n{fmt_valor(valor)}", color=0x2f3136)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="👥 Jogadores", value="Nenhum", inline=False)
            msg = await canal.send(embed=embed)
            conn = get_connection()
            cur = conn.cursor()
            for vagas in [1, 2, 3]:
                cur.execute("INSERT OR REPLACE INTO filas (guild_id, valor, modo, tipo_jogo, vagas_emu, jogadores, msg_id, criado_em) VALUES (?, ?, ?, 'misto', ?, '', ?, ?)",
                           (guild_id, valor, f"4x4-misto_{vagas}emu", vagas, msg.id, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        await interaction.followup.send("✅ Filas 4x4 Misto criadas!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(FilaCog(bot))
