import discord
from discord.ext import commands
from discord import app_commands

class FilasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree

    @self.tree.command(name="1x1-mob", description="📱 Cria FILAS de 1v1 MOBILE com todos os valores definidos")
    async def criar_filas_1v1(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 1x1 Mobile criada!", ephemeral=True)

    @self.tree.command(name="1x1-emulador", description="🖥️ Cria FILAS de 1v1 EMULADOR com todos os valores definidos")
    async def criar_filas_1x1_emulador(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 1x1 Emulador criada!", ephemeral=True)

    @self.tree.command(name="2x2-emu", description="👥 Cria FILAS de 2x2 EMULADOR com todos os valores definidos")
    async def criar_filas_2x2_emu(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 2x2 Emulador criada!", ephemeral=True)

    @self.tree.command(name="3x3-emu", description="👥 Cria FILAS de 3x3 EMULADOR com todos os valores definidos")
    async def criar_filas_3x3_emu(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 3x3 Emulador criada!", ephemeral=True)

    @self.tree.command(name="4x4-emu", description="👥 Cria FILAS de 4x4 EMULADOR com todos os valores definidos")
    async def criar_filas_4x4_emu(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 4x4 Emulador criada!", ephemeral=True)

    @self.tree.command(name="2x2-mob", description="📱 Cria FILAS de 2x2 MOBILE com todos os valores definidos")
    async def criar_filas_2x2_mob(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 2x2 Mobile criada!", ephemeral=True)

    @self.tree.command(name="3x3-mob", description="📱 Cria FILAS de 3x3 MOBILE com todos os valores definidos")
    async def criar_filas_3x3_mob(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 3x3 Mobile criada!", ephemeral=True)

    @self.tree.command(name="4x4-mob", description="📱 Cria FILAS de 4x4 MOBILE com todos os valores definidos")
    async def criar_filas_4x4_mob(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 4x4 Mobile criada!", ephemeral=True)

    @self.tree.command(name="filamisto-2x2", description="🎮 Cria FILAS de 2x2 MISTO (Mobile + Emulador) com todos os valores")
    async def criar_filas_misto_2x2(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 2x2 Misto criada!", ephemeral=True)

    @self.tree.command(name="filamisto-3x3", description="🎮 Cria FILAS de 3x3 MISTO (Mobile + Emulador) com todos os valores")
    async def criar_filas_misto_3x3(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 3x3 Misto criada!", ephemeral=True)

    @self.tree.command(name="filamisto-4x4", description="🎮 Cria FILAS de 4x4 MISTO (Mobile + Emulador) com todos os valores")
    async def criar_filas_misto_4x4(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Fila 4x4 Misto criada!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(FilasCog(bot))
