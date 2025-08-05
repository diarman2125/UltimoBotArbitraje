import requests
import os
import time
from datetime import datetime
from pytz import timezone

print("🔥 El bot está corriendo correctamente")

# Claves desde Railway (asegúrate de que estén bien nombradas)
API_KEY = os.getenv("ODDS_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_KEY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configuración
REGION = "us"
SPORT = "tennis"
MARKETS = "h2h,spreads,totals"

# Lista de casas legales en Indiana
CASAS_INDIANA = [
    "FanDuel", "DraftKings", "BetMGM", "Caesars", "BetRivers",
    "PointsBet", "ESPN BET", "HardRockBet", "Bet365",
    "Bally Bet", "ReBet", "Sportzino", "BetOpenly"
]

ODDS_API_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"

def decimal_to_american(odds):
    if odds >= 2.0:
        return f"+{int((odds - 1) * 100)}"
    else:
        return f"{int(-100 / (odds - 1))}"

def get_odds():
    params = {
        "regions": REGION,
        "markets": MARKETS,
        "oddsFormat": "decimal",
        "apiKey": API_KEY
    }
    response = requests.get(ODDS_API_URL, params=params)
    if response.status_code != 200:
        print("Error al obtener cuotas:", response.text)
        return []
    return response.json()

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    requests.post(url, data=data)

def analizar_partidos():
    data = get_odds()
    now = datetime.now(timezone("America/Indiana/Indianapolis"))
    for evento in data:
        equipos = " vs ".join(evento.get("teams", []))
        hora_utc = evento.get("commence_time")
        hora_local = datetime.fromisoformat(hora_utc.replace("Z", "+00:00")).astimezone(timezone("America/Indiana/Indianapolis"))
        hora_str = hora_local.strftime("%I:%M %p")

        for mercado in evento.get("bookmakers", []):
            casa = mercado["title"]
            if casa not in CASAS_INDIANA:
                continue

            for outcome in mercado["markets"]:
                tipo_mercado = outcome["key"]
                outcomes = outcome["outcomes"]
                for o in outcomes:
                    nombre = o["name"]
                    cuota = o["price"]

                    mejor = cuota
                    peor = cuota
                    casa_mejor = casa
                    casa_peor = casa

                    for otra_casa in evento.get("bookmakers", []):
                        if otra_casa["title"] not in CASAS_INDIANA:
                            continue
                        for m in otra_casa["markets"]:
                            if m["key"] != tipo_mercado:
                                continue
                            for oc in m["outcomes"]:
                                if oc["name"] == nombre:
                                    if oc["price"] > mejor:
                                        mejor = oc["price"]
                                        casa_mejor = otra_casa["title"]
                                    if oc["price"] < peor:
                                        peor = oc["price"]
                                        casa_peor = otra_casa["title"]

                    if mejor == peor:
                        continue

                    diferencia = round((mejor - peor) / peor * 100, 2)
                    prob_implicita = round(100 / mejor, 2)
                    prob_real = round((100 / mejor + 100 / peor) / 2, 2)

                    if diferencia >= 15:
                        mensaje = (
                            f"🟢 <b>Value Bet Encontrada (Tenis)</b>"
                            f"📌 <b>Evento:</b> {equipos}"
                            f"📅 <b>Hora del Partido:</b> {hora_str}"
                            f"🎯 <b>Mercado:</b> {tipo_mercado} - {nombre}"
                            f"🏆 <b>Casa con cuota MÁS ALTA:</b> {casa_mejor} | {mejor} ({decimal_to_american(mejor)})"
                            f"⚠️ <b>Casa con cuota MÁS BAJA:</b> {casa_peor} | {peor} ({decimal_to_american(peor)})"
                            f"📉 <b>Diferencia:</b> {diferencia}%"
                            f"📊 <b>Probabilidad Implícita:</b> {prob_implicita}%"
                            f"✅ <b>Probabilidad Real:</b> {prob_real}%"
                        )
                        enviar_telegram(mensaje)

def main():
    while True:
        try:
            analizar_partidos()
        except Exception as e:
            print("Error general:", e)
        time.sleep(60)

if __name__ == "__main__":
    main()
