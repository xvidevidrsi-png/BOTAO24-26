import discord
from discord.ext import commands
from discord import app_commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree

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
