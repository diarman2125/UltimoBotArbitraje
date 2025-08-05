
import requests
import os
import time
from datetime import datetime
from pytz import timezone

print("🔁 Bot de Arbitraje (Tenis) ejecutándose...")

API_KEY = os.getenv("ODDS_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_KEY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

REGION = "us"
SPORT = "tennis"
MARKETS = "h2h,spreads,totals,sets,game_totals,set_spreads"
STAKE_TOTAL = 100

# 🔧 Puedes editar fácilmente el % mínimo requerido para arbitraje aquí:
MIN_RENTABILIDAD = 3.0

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
    for evento in data:
        equipos = evento.get("teams", [])
        if len(equipos) != 2:
            continue

        jugadorA, jugadorB = equipos
        hora_utc = evento.get("commence_time")
        hora_local = datetime.fromisoformat(hora_utc.replace("Z", "+00:00")).astimezone(timezone("America/Indiana/Indianapolis"))

        for casa in evento.get("bookmakers", []):
            if casa["title"] not in CASAS_INDIANA:
                continue

            for mercado in casa["markets"]:
                tipo_mercado = mercado["key"]
                if tipo_mercado not in MARKETS.split(","):
                    continue
                outcomes = mercado["outcomes"]
                if len(outcomes) != 2:
                    continue

                cuotaA = None
                cuotaB = None

                for outcome in outcomes:
                    if outcome["name"] == jugadorA:
                        cuotaA = outcome["price"]
                    elif outcome["name"] == jugadorB:
                        cuotaB = outcome["price"]

                if not cuotaA or not cuotaB:
                    continue

                arbitraje_valor = round((1 / cuotaA + 1 / cuotaB) * 100, 2)
                rentabilidad = round(100 - arbitraje_valor, 2)

                if rentabilidad >= MIN_RENTABILIDAD:
                    inversa_A = 1 / cuotaA
                    inversa_B = 1 / cuotaB
                    suma_inversas = inversa_A + inversa_B

                    apuesta_A = round((inversa_A / suma_inversas) * STAKE_TOTAL, 2)
                    apuesta_B = round((inversa_B / suma_inversas) * STAKE_TOTAL, 2)
                    ganancia_neta = round(min(apuesta_A * cuotaA, apuesta_B * cuotaB) - STAKE_TOTAL, 2)

                    mensaje = (
                        f"🟢 <b>Oportunidad de Arbitraje (Tenis)</b>\n"
                        f"📌 <b>Evento:</b> {jugadorA} vs {jugadorB}\n"
                        f"📅 <b>Fecha y hora:</b> {hora_local.strftime('%Y-%m-%d %I:%M %p')}\n"
                        f"🎯 <b>Mercado:</b> {tipo_mercado}\n"
                        f"🏆 <b>Cuota A ({jugadorA}):</b> {cuotaA} ({decimal_to_american(cuotaA)})\n"
                        f"⚠️ <b>Cuota B ({jugadorB}):</b> {cuotaB} ({decimal_to_american(cuotaB)})\n"
                        f"🧮 <b>Suma de probabilidades:</b> {arbitraje_valor}%\n"
                        f"💰 <b>Rentabilidad del arbitraje:</b> {rentabilidad}%\n"
                        f"💵 <b>Inversión sugerida (total ${STAKE_TOTAL}):</b>\n"
                        f"• Apostar ${apuesta_A} a {jugadorA} ({cuotaA})\n"
                        f"• Apostar ${apuesta_B} a {jugadorB} ({cuotaB})\n"
                        f"🏅 <b>Ganancia neta asegurada:</b> ${ganancia_neta}"
                    )
                    enviar_telegram(mensaje)

def main():
    while True:
        try:
            analizar_partidos()
        except Exception as e:
            print("Error:", e)
        time.sleep(60)

if __name__ == "__main__":
    main()