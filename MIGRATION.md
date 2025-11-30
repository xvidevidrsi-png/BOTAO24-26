# 🚀 MIGRAÇÃO POSTGRESQL - GUIA DE DEPLOY

## ✅ Mudanças Implementadas:
1. **Importados PostgreSQL (psycopg2) e SQLite**
2. **Função `get_connection()` automática:**
   - Se `DATABASE_URL` existir → Usa PostgreSQL
   - Senão → Usa SQLite local (fallback)
3. **79 linhas atualizadas** para usar `get_connection()`

## 📋 Próximos Passos no RENDER:

### 1. Criar Database PostgreSQL
```
No painel do Render:
- Novo PostgreSQL Database
- Copiar CONNECTION STRING
```

### 2. Configurar Variáveis de Ambiente
```
No seu Web Service do Render:
Environment Variables
├─ DISCORD_TOKEN = seu_token
├─ BOT_OWNER_ID = seu_id  
└─ DATABASE_URL = postgres://...
```

### 3. Deploy
```
Git push para Render
Bot inicia → Detecta DATABASE_URL → Conecta PostgreSQL automaticamente
```

## 🔄 Migração de Dados (SQLite → PostgreSQL)

Executar localmente ANTES de fazer deploy:
```python
# Script pra copiar dados do SQLite pra PostgreSQL
# (Se precisar, posso criar depois)
```

## ✅ Pronto para 24/7 no Render!
- Dados persistem na nuvem
- Sem mais reinicializações deletando tudo
- Compatível com Free Tier
