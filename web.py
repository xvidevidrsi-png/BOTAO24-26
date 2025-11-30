from flask import Flask, jsonify
import os
import sqlite3

app = Flask(__name__)
DB_FILE = "bot_zeus.db"

@app.route("/")
def home():
    return jsonify({
        "status": "🟢 Bot Zeus está ONLINE",
        "nome": "Bot Zeus - Gerenciador de Filas e PIX",
        "funcionalidades": [
            "Gerencia filas de gaming",
            "Sistema PIX automático",
            "Fila de mediadores 24/7",
            "Estatísticas de jogadores"
        ]
    })

@app.route("/health")
def health():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"})
    except:
        return jsonify({"status": "unhealthy", "database": "disconnected"}), 500

@app.route("/stats")
def stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT guild_id) FROM usuarios")
        servidores = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM usuarios")
        usuarios = cur.fetchone()[0] or 0
        conn.close()
        return jsonify({
            "servidores": servidores,
            "usuarios_totais": usuarios,
            "status": "online"
        })
    except:
        return jsonify({"error": "Banco não inicializado"}), 503

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
