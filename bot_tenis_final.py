
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
MARKETS = "h2h"
STAKE_TOTAL = 100  # Monto total a invertir en arbitraje

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

        mejor_cuota_A = 0
        mejor_casa_A = ""
        mejor_cuota_B = 0
        mejor_casa_B = ""

        for casa in evento.get("bookmakers", []):
            if casa["title"] not in CASAS_INDIANA:
                continue
            for mercado in casa["markets"]:
                if mercado["key"] != "h2h":
                    continue
                for outcome in mercado["outcomes"]:
                    if outcome["name"] == jugadorA:
                        if outcome["price"] > mejor_cuota_A:
                            mejor_cuota_A = outcome["price"]
                            mejor_casa_A = casa["title"]
                    elif outcome["name"] == jugadorB:
                        if outcome["price"] > mejor_cuota_B:
                            mejor_cuota_B = outcome["price"]
                            mejor_casa_B = casa["title"]

        if mejor_cuota_A == 0 or mejor_cuota_B == 0:
            continue

        arbitraje_valor = round((1 / mejor_cuota_A + 1 / mejor_cuota_B) * 100, 2)
        rentabilidad = round(100 - arbitraje_valor, 2)

        if rentabilidad >= 3:
            # cálculo de apuestas óptimas
            inversa_A = 1 / mejor_cuota_A
            inversa_B = 1 / mejor_cuota_B
            suma_inversas = inversa_A + inversa_B

            apuesta_A = round((inversa_A / suma_inversas) * STAKE_TOTAL, 2)
            apuesta_B = round((inversa_B / suma_inversas) * STAKE_TOTAL, 2)
            ganancia_A = round(apuesta_A * mejor_cuota_A, 2)
            ganancia_B = round(apuesta_B * mejor_cuota_B, 2)
            ganancia_neta = round(min(ganancia_A, ganancia_B) - STAKE_TOTAL, 2)

            mensaje = (
                f"🟢 <b>Oportunidad de Arbitraje (Tenis)</b>\n"
                f"📌 <b>Evento:</b> {jugadorA} vs {jugadorB}\n"
                f"📅 <b>Fecha y hora:</b> {hora_local.strftime('%Y-%m-%d %I:%M %p')}\n"
                f"🎯 <b>Mercado:</b> h2h\n"
                f"🏆 <b>Cuota más ALTA ({jugadorA}):</b> {mejor_casa_A} | {mejor_cuota_A} ({decimal_to_american(mejor_cuota_A)})\n"
                f"⚠️ <b>Cuota más BAJA del rival ({jugadorB}):</b> {mejor_casa_B} | {mejor_cuota_B} ({decimal_to_american(mejor_cuota_B)})\n"
                f"📉 <b>Diferencia entre cuotas:</b> {round((mejor_cuota_A - mejor_cuota_B) / mejor_cuota_B * 100, 2)}%\n"
                f"🧮 <b>Suma de probabilidades:</b> {arbitraje_valor}%\n"
                f"💰 <b>Rentabilidad del arbitraje:</b> {rentabilidad}%\n"
                f"💵 <b>Inversión sugerida (total ${STAKE_TOTAL}):</b>\n"
                f"• Apostar ${apuesta_A} a {jugadorA} ({mejor_cuota_A})\n"
                f"• Apostar ${apuesta_B} a {jugadorB} ({mejor_cuota_B})\n"
                f"🏅 <b>Ganancia neta asegurada:</b> ${ganancia_neta}"
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