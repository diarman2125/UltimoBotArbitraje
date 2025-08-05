
import requests
import time
import pytz
from datetime import datetime
from telegram import Bot

# Configuración
API_KEY = "TU_API_KEY"
SPORT = "tennis"
REGION = "us"
MARKETS = "h2h,game_totals,set_spreads,totals,spreads"
BOOKMAKERS = "fanduel,draftkings,betmgm,caesars,pointsbet_us,barstool,betonlineag,bovada,betus,betrivers,superbook,sugarhouse,wynnbet,unibet_us,ballybet,fliff,prophet_exchange,espnbet,hardrock,novig,onyx,sportzino,rebets,betopenly,365,play_ballybet"
TELEGRAM_TOKEN = "TU_TOKEN"
TELEGRAM_CHAT_ID = "TU_CHAT_ID"
STAKE_TOTAL = 100
RENTABILIDAD_MINIMA = 3.0  # Valor editable

bot = Bot(token=TELEGRAM_TOKEN)

def decimal_to_american(decimal_odds):
    if decimal_odds >= 2.0:
        return f"+{round((decimal_odds - 1) * 100)}"
    else:
        return f"-{round(100 / (decimal_odds - 1))}"

def obtener_datos():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?regions={REGION}&markets={MARKETS}&bookmakers={BOOKMAKERS}&apiKey={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error al obtener cuotas:", e)
        return []

def enviar_mensaje(mensaje):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensaje, parse_mode="HTML")

def analizar_cuotas():
    eventos = obtener_datos()
    zona_horaria = pytz.timezone("America/Indiana/Indianapolis")

    for evento in eventos:
        equipos = " vs ".join(evento["teams"])
        hora_evento = datetime.fromisoformat(evento["commence_time"].replace("Z", "+00:00")).astimezone(zona_horaria)
        nombre = evento["home_team"]
        rival = [team for team in evento["teams"] if team != nombre][0]

        for mercado in evento["bookmakers"]:
            tipo_mercado = mercado["key"]
            outcomes = mercado.get("markets", [])

            for market_data in outcomes:
                outcomes = market_data.get("outcomes", [])
                if len(outcomes) < 2:
                    continue

                cuota_A = outcomes[0]
                cuota_B = outcomes[1]

                if cuota_A["price"] > cuota_B["price"]:
                    mejor = cuota_A["price"]
                    peor = cuota_B["price"]
                    nombre_jugador = cuota_A["name"]
                    rival_jugador = cuota_B["name"]
                    casa_mejor = cuota_A["bookmaker"]
                    casa_peor = cuota_B["bookmaker"]
                else:
                    mejor = cuota_B["price"]
                    peor = cuota_A["price"]
                    nombre_jugador = cuota_B["name"]
                    rival_jugador = cuota_A["name"]
                    casa_mejor = cuota_B["bookmaker"]
                    casa_peor = cuota_A["bookmaker"]

                suma_probabilidades = round((1 / mejor + 1 / peor) * 100, 2)
                rentabilidad = round(100 - suma_probabilidades, 2)

                if rentabilidad >= RENTABILIDAD_MINIMA:
                    inversa_mejor = 1 / mejor
                    inversa_peor = 1 / peor
                    apuesta_A = round(STAKE_TOTAL / (1 + mejor / peor), 2)
                    apuesta_B = round(STAKE_TOTAL - apuesta_A, 2)
                    ganancia_neta = round(min(apuesta_A * mejor, apuesta_B * peor) - STAKE_TOTAL, 2)
                    diferencia = round(((mejor - peor) / peor) * 100, 2)

                    mensaje = (
                        f"🟢 <b>Oportunidad de Arbitraje (Tenis)</b>\n"
                        f"📌 <b>Evento:</b> {equipos}\n"
                        f"📅 <b>Fecha y hora:</b> {hora_evento.strftime('%Y-%m-%d %I:%M %p')}\n"
                        f"🎯 <b>Mercado:</b> {tipo_mercado} - {nombre_jugador}\n"
                        f"🏆 <b>Cuota más ALTA ({nombre_jugador}):</b> {casa_mejor} | {mejor} ({decimal_to_american(mejor)})\n"
                        f"⚠️ <b>Cuota más BAJA del rival ({rival_jugador}):</b> {casa_peor} | {peor} ({decimal_to_american(peor)})\n"
                        f"📉 <b>Diferencia entre cuotas:</b> {diferencia}%\n"
                        f"🧮 <b>Suma de probabilidades:</b> {suma_probabilidades}%\n"
                        f"💰 <b>Rentabilidad del arbitraje:</b> {rentabilidad}%\n"
                        f"💵 <b>Inversión sugerida (total ${STAKE_TOTAL}):</b>\n"
                        f"• Apostar ${apuesta_A} a {nombre_jugador} ({mejor})\n"
                        f"• Apostar ${apuesta_B} a {rival_jugador} ({peor})\n"
                        f"🏅 <b>Ganancia neta asegurada:</b> ${ganancia_neta}"
                    )
                    enviar_mensaje(mensaje)

if __name__ == "__main__":
    while True:
        analizar_cuotas()
        time.sleep(60)
