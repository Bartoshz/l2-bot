import logging
import requests
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
from datetime import datetime

BOT_TOKEN = "8069640766:AAG5pj5XwjVnM8e-vstCYBXS-_GQd0g8KD0"
API_KEY = "e88d1bf1bedc69613ec3dce7cd92e684"

HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_KEY
}

def get_fixtures():
    hoje = datetime.now().strftime("%Y-%m-%d")
    params = {"timezone": "America/Sao_Paulo", "date": hoje}
    resp = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params=params)
    return resp.json().get("response", [])

def get_last_matches(team_id):
    params = {"team": team_id, "last": 10}
    r = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params=params)
    return r.json().get("response", [])

def get_odds(fixture_id):
    url = "https://v3.football.api-sports.io/odds"
    params = {"fixture": fixture_id, "market": "both_teams_score"}
    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json().get("response", [])
    try:
        for bookmaker in data[0]["bookmakers"]:
            for bet in bookmaker["bets"]:
                for val in bet["values"]:
                    if val["value"].lower() == "yes":
                        return float(val["odd"])
    except:
        return None
    return None

def analisar_estrategia():
    resultados = []
    jogos = get_fixtures()
    for jogo in jogos:
        try:
            home = jogo["teams"]["home"]
            away = jogo["teams"]["away"]
            fixture_id = jogo["fixture"]["id"]
            hora = jogo["fixture"]["date"][11:16]

            odd = get_odds(fixture_id)
            if not odd or odd < 1.7:
                continue

            ultimos_jogos = get_last_matches(home["id"])
            if len(ultimos_jogos) < 10:
                continue

            btts_hits = 0
            posse_total = 0
            posse_count = 0

            for partida in ultimos_jogos:
                g_home = partida["goals"]["home"]
                g_away = partida["goals"]["away"]
                if g_home > 0 and g_away > 0:
                    btts_hits += 1

                stats = partida.get("statistics", [])
                if stats and stats[0]["team"]["id"] == home["id"]:
                    for item in stats[0]["statistics"]:
                        if item["type"] == "Ball Possession" and item["value"]:
                            val = item["value"].replace('%', '')
                            posse_total += int(val)
                            posse_count += 1

            if posse_count == 0:
                continue

            posse_avg = posse_total / posse_count

            if btts_hits >= 6 and posse_avg >= 50:
                resultados.append({
                    "jogo": f"{home['name']} x {away['name']}",
                    "hora": hora,
                    "btts": btts_hits,
                    "posse": round(posse_avg, 1),
                    "odd": odd
                })

        except Exception as e:
            print("Erro ao processar jogo:", e)
            continue

    return resultados

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Buscando jogos com valor real usando dados oficiais...")
    jogos = analisar_estrategia()
    if not jogos:
        await update.message.reply_text("Nenhum jogo encontrado hoje!")
        return

    msg = "📊 Jogos com valor hoje:\n\n"
    for j in jogos:
        msg += f"🏟️ {j['jogo']} às {j['hora']}\n"
        msg += f"📈 BTTS: {j['btts']}/10 | Posse: {j['posse']}% | Odd BTTS: {j['odd']}\n\n"

    await update.message.reply_text(msg)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("buscar", buscar))
    app.run_polling()
