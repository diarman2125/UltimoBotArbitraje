import os
import requests
from datetime import datetime
from telegram import Bot
import pytz

# Configuración
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

STAKE_TOTAL = 100  # Puedes ajustar este valor según tu presupuesto
RENTABILIDAD_MINIMA = 3.0  # Editable según el porcentaje mínimo deseado

# Mercados a solicitar en una sola llamada
MARKETS = "h2h,spreads,totals"
SPORT = "tennis"
REGION = "us"
BOOKMAKERS = "fanduel,draftkings,betmgm,pointsbetus,wynnbet,caesars,espnbet,betrivers"

# Zona horaria local
zona_horaria_local = pytz.timezone('America/Indiana/Indianapolis')

def decimal_to_american(odds):
    if odds >= 2.0:
        return f"+{round((odds - 1) * 100)}"
    else:
        return f"-{round(100 / (odds - 1))}"

def calcular_apuestas(cuota_a, cuota_b, total):
    inv_a = total / (1 + (cuota_a / cuota_b))
    inv_b = total - inv_a
    ganancia = round(inv_a * cuota_a - total, 2)
    return round(inv_a, 2), round(inv_b, 2), ganancia

def enviar_mensaje(mensaje):
    bot = Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode="HTML")

def verificar_arbitraje():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?regions={REGION}&markets={MARKETS}&apiKey={ODDS_API_KEY}"
    respuesta = requests.get(url)

    if respuesta.status_code != 200:
        print("Error al obtener cuotas:", respuesta.text)
        return

    eventos = respuesta.json()

    for evento in eventos:
        equipos = "No disponible"
        if "teams" in evento:
            equipos = " vs ".join(evento["teams"])
        hora_utc = datetime.strptime(evento["commence_time"], "%Y-%m-%dT%H:%M:%SZ")
        hora_local = hora_utc.replace(tzinfo=pytz.utc).astimezone(zona_horaria_local)

        for mercado in evento["bookmakers"]:
            tipo_mercado = mercado["markets"][0]["key"] if mercado["markets"] else "unknown"
            for outcome_index in range(len(mercado["markets"][0]["outcomes"])):
                nombre = mercado["markets"][0]["outcomes"][outcome_index]["name"]
                odds = []

                for book in evento["bookmakers"]:
                    for market in book["markets"]:
                        for out in market["outcomes"]:
                            if out["name"] == nombre:
                                odds.append({
                                    "casa": book["title"],
                                    "cuota": out["price"]
                                })

                if len(odds) < 2:
                    continue

                mejor = max(odds, key=lambda x: x["cuota"])
                peor_rival = min(odds, key=lambda x: x["cuota"])

                probabilidad_total = (1 / mejor["cuota"]) + (1 / peor_rival["cuota"])
                arbitraje_valor = round(probabilidad_total * 100, 2)
                rentabilidad = round((1 - probabilidad_total) * 100, 2)

                if rentabilidad >= RENTABILIDAD_MINIMA:
                    apuesta_A, apuesta_B, ganancia_neta = calcular_apuestas(mejor["cuota"], peor_rival["cuota"], STAKE_TOTAL)

                    mensaje = (
                        f"🟢 <b>Oportunidad de Arbitraje (Tenis)</b>\n"
                        f"📌 <b>Evento:</b> {equipos}\n"
                        f"📅 <b>Fecha y hora:</b> {hora_local.strftime('%Y-%m-%d %I:%M %p')}\n"
                        f"🎯 <b>Mercado:</b> {tipo_mercado} - {nombre}\n"
                        f"🏆 <b>Cuota más ALTA ({nombre}):</b> {mejor['casa']} | {mejor['cuota']} ({decimal_to_american(mejor['cuota'])})\n"
                        f"⚠️ <b>Cuota más BAJA del rival:</b> {peor_rival['casa']} | {peor_rival['cuota']} ({decimal_to_american(peor_rival['cuota'])})\n"
                        f"🧮 <b>Suma de probabilidades:</b> {arbitraje_valor}%\n"
                        f"💰 <b>Rentabilidad del arbitraje:</b> {rentabilidad}%\n"
                        f"💵 <b>Inversión sugerida (total ${STAKE_TOTAL}):</b>\n"
                        f"• Apostar ${apuesta_A} a {nombre} ({mejor['cuota']})\n"
                        f"• Apostar ${apuesta_B} al rival ({peor_rival['cuota']})\n"
                        f"🏅 <b>Ganancia neta asegurada:</b> ${ganancia_neta}"
                    )

                    enviar_mensaje(mensaje)

if __name__ == '__main__':
    verificar_arbitraje()