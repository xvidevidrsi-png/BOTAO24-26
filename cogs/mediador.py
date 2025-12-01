import discord
from discord.ext import commands
from discord import app_commands

class MediadorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree

    @self.tree.command(name="fila_mediadores", description="👨‍⚖️ Cria MENU de FILA DE MEDIADORES (Entrar/Sair em serviço)")
    async def fila_mediadores_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila de mediadores criada!", ephemeral=True)

    @self.tree.command(name="rank", description="Ver seu perfil ou o ranking do servidor")
    async def rank_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏆 Ranking",
            description="Seu perfil de jogador",
            color=0x2f3136
        )
        embed.add_field(name="👤 Jogador", value=interaction.user.mention, inline=False)
        embed.add_field(name="⭐ Vitórias", value="0", inline=True)
        embed.add_field(name="💔 Derrotas", value="0", inline=True)
        embed.add_field(name="💰 Coins", value="0", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MediadorCog(bot))
