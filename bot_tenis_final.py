
import requests
import os
import time
from datetime import datetime
from pytz import timezone
import hashlib

print("🔥 El bot está corriendo correctamente")

# Claves desde Railway
API_KEY = os.getenv("ODDS_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_KEY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configuración
REGION = "us"
SPORT = "tennis"
MARKETS = "h2h,spreads,totals"
STAKE_TOTAL = 100  # Monto total que se desea invertir en cada arbitraje

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

alertas_enviadas = set()

def generar_id_alerta(nombre_evento, mercado, nombre_apuesta, cuota):
    clave = f"{nombre_evento}_{mercado}_{nombre_apuesta}_{cuota}"
    return hashlib.md5(clave.encode()).hexdigest()

def analizar_partidos():
    data = get_odds()
    now = datetime.now(timezone("America/Indiana/Indianapolis"))
    for evento in data:
        equipos = " vs ".join(evento.get("teams", []))
        hora_utc = evento.get("commence_time")
        hora_local = datetime.fromisoformat(hora_utc.replace("Z", "+00:00")).astimezone(timezone("America/Indiana/Indianapolis"))

        for mercado in evento.get("bookmakers", []):
            casa = mercado["title"]
            if casa not in ["FanDuel", "DraftKings", "BetMGM"]:
                continue

            for outcome in mercado["markets"]:
                tipo_mercado = outcome["key"]
                outcomes = outcome["outcomes"]
                for o in outcomes:
                    nombre = o["name"]
                    cuota = o["price"]

                    mejor = cuota
                    casa_mejor = casa
                    peor_rival = None
                    casa_peor_rival = None

                    equipos_evento = evento.get("teams", [])
                    rival = [e for e in equipos_evento if e != nombre]
                    rival = rival[0] if rival else None

                    for otra_casa in evento.get("bookmakers", []):
                        if otra_casa["title"] not in ["FanDuel", "DraftKings", "BetMGM"]:
                            continue
                        for m in otra_casa["markets"]:
                            if m["key"] != tipo_mercado:
                                continue
                            for oc in m["outcomes"]:
                                if oc["name"] == nombre and oc["price"] > mejor:
                                    mejor = oc["price"]
                                    casa_mejor = otra_casa["title"]
                                if rival and oc["name"] == rival:
                                    if peor_rival is None or oc["price"] < peor_rival:
                                        peor_rival = oc["price"]
                                        casa_peor_rival = otra_casa["title"]

                    if peor_rival is None or mejor <= 1.01 or peor_rival <= 1.01:
                        continue

                    diferencia = round((mejor - peor_rival) / peor_rival * 100, 2)

                    # Cálculo de arbitraje real
                    inv_mejor = 1 / mejor
                    inv_peor_rival = 1 / peor_rival
                    arbitraje_valor = round((inv_mejor + inv_peor_rival) * 100, 2)
                    rentabilidad = round(100 - arbitraje_valor, 2)

                    if arbitraje_valor >= 100 or rentabilidad < 3.0:
                        continue

                    id_alerta = generar_id_alerta(equipos, tipo_mercado, nombre, mejor)
                    if id_alerta in alertas_enviadas:
                        continue
                    alertas_enviadas.add(id_alerta)

                    apuesta_A = round(STAKE_TOTAL / (1 + (mejor / peor_rival)), 2)
                    apuesta_B = round(STAKE_TOTAL - apuesta_A, 2)
                    ganancia_neta = round(apuesta_A * mejor - STAKE_TOTAL, 2)

                    mensaje = (
                        f"🟢 <b>Oportunidad de Arbitraje (Tenis)</b>
"
                        f"📌 <b>Evento:</b> {equipos}
"
                        f"📅 <b>Fecha y hora:</b> {hora_local.strftime('%Y-%m-%d %I:%M %p')}
"
                        f"🎯 <b>Mercado:</b> {tipo_mercado} - {nombre}
"
                        f"🏆 <b>Cuota más ALTA ({nombre}):</b> {casa_mejor} | {mejor} ({decimal_to_american(mejor)})
"
                        f"⚠️ <b>Cuota más BAJA del rival ({rival}):</b> {casa_peor_rival} | {peor_rival} ({decimal_to_american(peor_rival)})
"
                        f"📉 <b>Diferencia entre cuotas:</b> {diferencia}%
"
                        f"🧮 <b>Suma de probabilidades:</b> {arbitraje_valor}%
"
                        f"💰 <b>Rentabilidad del arbitraje:</b> {rentabilidad}%
"
                        f"💵 <b>Inversión sugerida (total ${STAKE_TOTAL}):</b>
"
                        f"• Apostar ${apuesta_A} a {nombre} ({mejor})
"
                        f"• Apostar ${apuesta_B} a {rival} ({peor_rival})
"
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