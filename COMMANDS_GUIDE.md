# 📖 GUIA COMPLETO - BOT ZEUS

## 🎮 FILAS - CRIAR

### 🔸 `/1x1-mob`
**1v1 Mobile** - Cria filas para partidas individuais em modo mobile
- 💰 Valores pré-configurados: R$ 100, R$ 50, R$ 40, etc
- 👥 2 jogadores máximo
- 📱 Modo: Mobile
- ⏱️ Cada fila com um botão "Entrar"

### 🔸 `/1x1-emulador`
**1v1 Emulador** - Cria filas para partidas individuais em emulador
- 💰 Valores pré-configurados
- 👥 2 jogadores
- 🖥️ Modo: Emulador
- 🎮 Competição em emulador

### 🔸 `/2x2-mob`, `/3x3-mob`, `/4x4-mob`
**Times Mobile** - Filas para partidas em equipes no mobile
- 🤝 `/2x2-mob`: 2v2 (4 jogadores)
- 🤝 `/3x3-mob`: 3v3 (6 jogadores)
- 🤝 `/4x4-mob`: 4v4 (8 jogadores)
- 📱 Modo: Mobile

### 🔸 `/2x2-emu`, `/3x3-emu`, `/4x4-emu`
**Times Emulador** - Filas para partidas em equipes no emulador
- 🖥️ Modo: Emulador
- 🤝 Mesma estrutura das filas mobile
- 🎮 Competição em emulador

### 🔸 `/filamisto-2x2`, `/filamisto-3x3`, `/filamisto-4x4`
**Modo Misto** - Permite tanto mobile quanto emulador na mesma fila
- 🔄 Mistura mobile + emulador
- 🤝 Mesmos tamanhos de times (2v2, 3v3, 4v4)
- 🎯 Jogadores escolhem seu modo

---

## ⚙️ CONFIGURAÇÃO GERAL

### 🔸 `/aux_config` ⭐ **IMPORTANTE**
**Define o cargo de Mediador** - Quem pode usar os botões de mediador
- 🎯 Escolher um cargo específico
- 👨‍⚖️ Apenas este cargo poderá:
  - Criar salas
  - Fazer revanche
  - Escolher vencedor
  - Acessar menu mediador
- ✅ Obrigatório: Configure antes de usar o bot

### 🔸 `/topico` ⭐ **IMPORTANTE**
**Define o canal de partidas** - Onde as partidas serão criadas
- 📍 Selecionar um canal específico
- 🎮 Todas as partidas aparecerão aqui
- 🧵 Pode usar threads (tópicos) ou canal normal
- ✅ Obrigatório: Configure antes de usar

### 🔸 `/configurar`
**Cargos a mencionar** - Quem recebe menção quando partida encontra
- 🔔 Digitar IDs de cargos separados por vírgula
- 📢 Quando uma partida é criada, estes cargos são marcados
- 💡 Exemplo: `123456789,987654321`

### 🔸 `/configurar_nome_bot`
**Nome personalizado** - Mude o nome do bot
- 🏷️ Digite o novo nome desejado
- ✨ Bot mudará de nome no servidor
- 🔄 Pode mudar quantas vezes quiser

### 🔸 `/addimagem`
**Adiciona logo às filas** - Coloca imagem nas mensagens de fila
- 🖼️ Cole a URL da imagem
- 📸 Aparecerá em todas as filas
- 💡 Dica: Use links diretos (imgur, discord, etc)

### 🔸 `/removerimagem`
**Remove logo das filas** - Tira a imagem que foi adicionada
- 🗑️ Remove logo anterior
- ✨ Filas voltam ao padrão

### 🔸 `/taxa` ⚡
**Altera taxa por jogador** - Cobra taxa adicional nas partidas
- 💰 Digite o valor (ex: 0.50)
- 📊 Taxa é ADICIONAL ao valor da partida
- 💡 Exemplo: Partida R$ 100 + Taxa R$ 0.50 = R$ 100.50 total

### 🔸 `/definir`
**Define valores das filas** - Customiza quanto custa cada partida
- 💵 Digitar o valor desejado
- 🎯 Escolher qual fila configurar
- 📝 Pode configurar cada fila diferente

---

## 😀 PERSONALIZAÇÃO (EMOJIS)

### 🔸 `/clonar_emoji`
**Customiza emojis dos botões** - Use emojis personalizados
- 🎨 Para **Filas 1x1**: Gel Normal, Gel Infinito
- 🎨 Para **Filas 2x2+**: Entrar, Sair
- 🔧 Escolha qual fila vai customizar
- 👍 Digite o emoji desejado

---

## 👥 SISTEMA DE MEDIADORES

### 🔸 `/fila_mediadores`
**Cria menu de mediadores** - Sistema para gerenciar mediadores
- 📦 Cria um canal exclusivo #📦・fila-mediadores
- 👨‍⚖️ Lista todos mediadores disponíveis
- ➕ Botão para entrar/sair da fila
- 🔄 Atualiza em tempo real

### 🔸 `!pixmed` (Prefix)
**Configura PIX** - Mediador configura sua chave PIX
- 💳 Digite: `!pixmed`
- 📋 Nome Completo
- 🔑 Chave PIX (email, CPF, telefone)
- 📤 PIX aparecerá automaticamente ao encontrar partida

---

## 🏆 PERFIL E RANKING

### 🔸 `/rank`
**Menu interativo** - Veja seu perfil ou ranking
- 👤 Opção 1: **Meu Perfil**
  - 💰 Coins totais
  - 🏆 Vitórias
  - 💔 Derrotas
  - 📈 Winrate %
  - 🎮 Total de partidas
- 🏆 Opção 2: **Ranking**
  - 🏆 **TODOS os jogadores** do servidor com vitórias
  - 🥇 Ordenado por vitórias (maior para menor)
  - 📊 Mostra vitórias, derrotas, winrate e coins

### 🔸 `!p` (Prefix)
**Ver perfil rápido** - Mostra seu perfil
- 💬 Digite: `!p` ou `!p @usuario`
- 👤 Ver perfil de outra pessoa
- 📊 Mesmas stats do `/rank`

---

## 🔧 ADMINISTRAÇÃO

### 🔸 `/dono_comando_slash`
**Define cargo de Admin** - Quem pode usar comandos de admin
- 👑 Escolher um cargo específico
- 🔐 Apenas este cargo poderá:
  - Configurar filas
  - Gerenciar mediadores
  - Ver logs
  - Usar `/tirar_coin`
- ⭐ Diferente do mediador!

### 🔸 `/tirar_coin`
**Remove coins de um jogador** - Punição ou reembolso
- 🎯 Mencionar o jogador
- 💰 Digitar quantas coins remover
- 📝 Registro automático
- ⚠️ Ação irreversível

### 🔸 `/membro_cargo`
**Cargo automático para novos** - Cargo dado a membros FUTUROS
- 👥 Escolher um cargo
- 🆕 Novos membros recebem automaticamente
- 🔄 Contínuo: funciona sempre que alguém entra

### 🔸 `/remover_membro_cargo`
**Remove auto-cargo** - Para de dar cargo automaticamente
- 🗑️ Remove a configuração
- 🚫 Novos membros NÃO recebem mais o cargo

### 🔸 `/cargos_membros`
**Dar cargo para TODOS** - Atribui cargo em massa
- 👥 Escolher um cargo
- 📊 Todos os membros (existentes + novos) recebem
- ⏳ Leva alguns segundos
- ✅ Mostra confirmação com total

---

## 📋 SISTEMA DE LOGS

### 🔸 `/logs` ⛔ **DESABILITADO**
**Este comando foi desabilitado temporariamente**

### 🔸 `/deletar_logs` ⛔ **DESABILITADO**
**Este comando foi desabilitado temporariamente**

---

## 📚 UTILITÁRIOS

### 🔸 `/manual`
**Este guia completo** - Vê todos os comandos disponíveis
- 📖 Categorizado por tipo
- 💡 Dicas rápidas
- 👀 Visível apenas para você (ephemeral)

### 🔸 `/rank` (com opções)
**Perfil e Ranking** - Menu interativo (descrito acima)

---

## 👑 COMANDOS OWNER

### 🔸 `/separador_de_servidor` ⭐ **CRÍTICO**
**Registra servidor no sistema** - OBRIGATÓRIO para usar o bot!
- 🔐 Apenas dono pode usar
- 📋 Registra o servidor como ativo
- ✅ Sem isto, nenhum comando funciona
- ⚠️ Use UMA VEZ ao configurar o servidor

### 🔸 `/resete_bot`
**Reset completo** - APAGA TODOS OS DADOS!
- 🗑️ Remove todas as partidas
- 🗑️ Remove todos os logs
- 🗑️ Remove configurações
- 🔄 Recomeça do zero
- ⚠️ **PERIGOSO - USE COM CUIDADO!**

### 🔸 `/puxar`
**Busca dados do servidor** - Informações técnicas
- 🔐 Apenas dono pode usar
- 📊 Mostra dados internos
- 🔍 Útil para debug

---

## 🎮 FLUXO DE PARTIDA COMPLETO

```
1. 👥 Jogador entra em fila (/1x1-mob, etc)
   ↓
2. 🎯 Outro jogador entra na MESMA fila
   ↓
3. 📢 Partida encontrada! Jogadores recebem menção
   ↓
4. ✅ Ambos clicam "Confirmar"
   ↓
5. 💰 PIX do mediador aparece automaticamente
   ↓
6. 🎮 Mediador cria sala (botão "CRIAR SALA")
   ↓
7. 🆔 ID e Senha aparecem no canal
   ↓
8. 🏆 Jogadores entram e jogam
   ↓
9. ✍️ Mediador escolhe vencedor
   ↓
10. 🎉 Vitórias/Derrotas registradas automaticamente
```

---

## 💡 DICAS IMPORTANTES

✅ **Sempre configure primeiro:**
1. `/separador_de_servidor` (Owner)
2. `/aux_config` (Admin) - Define mediador
3. `/topico` (Admin) - Define canal de partidas
4. `/dono_comando_slash` (Owner) - Define admin

✅ **Mediadores DEVEM:**
1. Usar `!pixmed` para configurar PIX
2. Entrar na `/fila_mediadores`
3. Estar no cargo configurado em `/aux_config`

✅ **Sistema automático:**
- 🤖 Partidas criam tópicos automaticamente
- 🤖 PIX aparece quando ambos confirmam
- 🤖 Vitórias/Derrotas contabilizadas automaticamente
- 🤖 Coins adicionadas ao vencedor automaticamente

---

**BOT ZEUS v1.0** 🚀 | Gerenciador de Filas para Discord
