import os
import time
import requests
from datetime import datetime
from telegram import Bot
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("THE_ODDS_API_KEY")
STAKE_TOTAL = 100
RENTABILIDAD_MINIMA = 3.0  # 🔧 Puedes editar este valor como filtro

bot = Bot(token=TELEGRAM_TOKEN)

def decimal_to_american(decimal_odds):
    decimal_odds = float(decimal_odds)
    if decimal_odds >= 2.0:
        return f"+{round((decimal_odds - 1) * 100)}"
    else:
        return f"-{round(100 / (decimal_odds - 1))}"

def calcular_arbitraje(cuota_1, cuota_2):
    cuota_1 = Decimal(str(cuota_1))
    cuota_2 = Decimal(str(cuota_2))
    suma_inv = (1/cuota_1) + (1/cuota_2)
    rentabilidad = (1 - suma_inv) * 100
    return float(suma_inv * 100), float(rentabilidad)

def enviar_alerta_arbitraje(data):
    equipos = data['teams']
    tipo_mercado = data['market']
    nombre = data['mejor_nombre']
    mejor = data['mejor_cuota']
    casa_mejor = data['mejor_casa']
    peor_rival = data['peor_cuota_rival']
    casa_peor_rival = data['peor_casa_rival']
    rival = data['rival']
    arbitraje_valor = data['suma_prob']
    rentabilidad = data['rentabilidad']
    hora_local = datetime.now()

    cuota_1 = Decimal(str(mejor))
    cuota_2 = Decimal(str(peor_rival))
    inv_total = STAKE_TOTAL
    apuesta_A = round(inv_total / (1 + (cuota_1 / cuota_2)), 2)
    apuesta_B = round(inv_total - apuesta_A, 2)
    ganancia_neta = round(min(apuesta_A * cuota_1, apuesta_B * cuota_2) - inv_total, 2)

    mensaje = (
        f"🟢 <b>Oportunidad de Arbitraje (Tenis)</b>\n"
        f"📌 <b>Evento:</b> {equipos}\n"
        f"📅 <b>Fecha y hora:</b> {hora_local.strftime('%Y-%m-%d %I:%M %p')}\n"
        f"🎯 <b>Mercado:</b> {tipo_mercado} - {nombre}\n"
        f"🏆 <b>Cuota más ALTA ({nombre}):</b> {casa_mejor} | {mejor} ({decimal_to_american(mejor)})\n"
        f"⚠️ <b>Cuota más BAJA del rival ({rival}):</b> {casa_peor_rival} | {peor_rival} ({decimal_to_american(peor_rival)})\n"
        f"🧮 <b>Suma de probabilidades:</b> {round(arbitraje_valor, 2)}%\n"
        f"💰 <b>Rentabilidad del arbitraje:</b> {round(rentabilidad, 2)}%\n"
        f"💵 <b>Inversión sugerida (total ${STAKE_TOTAL}):</b>\n"
        f"• Apostar ${apuesta_A} a {nombre} ({mejor})\n"
        f"• Apostar ${apuesta_B} a {rival} ({peor_rival})\n"
        f"🏅 <b>Ganancia neta asegurada:</b> ${ganancia_neta}"
    )

    bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode='HTML')

def obtener_cuotas():
    url = f"https://api.the-odds-api.com/v4/sports/tennis_atp/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,totals,spreads",
        "oddsFormat": "decimal"
    }
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print("Error al obtener cuotas:", response.text)
        return []

    return response.json()

def procesar_cuotas():
    datos = obtener_cuotas()

    for evento in datos:
        equipos = evento["teams"]
        mercados = evento["bookmakers"]
        for mercado in mercados:
            casa = mercado["title"]
            for market in mercado["markets"]:
                tipo = market["key"]
                for outcome in market["outcomes"]:
                    nombre = outcome["name"]
                    cuota = outcome["price"]

                    # Buscar la cuota rival
                    for otro_outcome in market["outcomes"]:
                        if otro_outcome["name"] != nombre:
                            rival = otro_outcome["name"]
                            cuota_rival = otro_outcome["price"]

                            suma_prob, rentabilidad = calcular_arbitraje(cuota, cuota_rival)
                            if rentabilidad >= RENTABILIDAD_MINIMA:
                                enviar_alerta_arbitraje({
                                    "teams": f"{equipos[0]} vs {equipos[1]}",
                                    "market": tipo,
                                    "mejor_nombre": nombre,
                                    "mejor_cuota": cuota,
                                    "mejor_casa": casa,
                                    "peor_cuota_rival": cuota_rival,
                                    "peor_casa_rival": casa,
                                    "rival": rival,
                                    "suma_prob": suma_prob,
                                    "rentabilidad": rentabilidad
                                })

if __name__ == "__main__":
    while True:
        print("Buscando oportunidades de arbitraje...")
        procesar_cuotas()
        time.sleep(60)
