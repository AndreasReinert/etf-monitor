import json
import os
import signal
import sys
import time

import requests
import yfinance as yf
from dotenv import load_dotenv

# --- LÄDT DIE .ENV DATEI ---
load_dotenv()

# --- KONFIGURATION ---
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Ticker-Mapping (ISINs auf Yahoo-Ticker gemappt)
ETFS_CONFIG = [
    # ISIN: IE00BFY0GT14 (SPDR World)
    {"ticker": "SPPW.DE", "group": "A"},
    # ISIN: IE00BK5BQT80 (Vanguard All-World)
    {"ticker": "VWCE.DE", "group": "A"},
    # ISIN: IE00BQN1K786 (Europe Momentum)
    {"ticker": "CEMR.DE", "group": "A"},
    # ISIN: IE00BTJRMP35 (Emerging Markets)
    {"ticker": "XMME.DE", "group": "A"},
    # ISIN: LU1829219390 (Amundi Banks)
    {"ticker": "BNKE.PA", "group": "B"},
    # ISIN: IE00BYQCZJ13 (Japan Hedged)
    {"ticker": "WTIF.DE", "group": "A"},
    # ISIN: LU1215828218 (EMU CHF Hedged)
    {"ticker": "XDUE.SW", "group": "A"},
]

# Alarm-Schwellen (Drawdown vom ATH in %)
THRESHOLDS = {
    "A": [-18, -26, -33],
    "B": [-25, -40, -50]
}


# --- SHUTDOWN HANDLER ---
class GracefulShutdown:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True
        print("\n\n🛑 Shutdown Signal empfangen! Beende sauber...")
        sys.exit(0)


shutdown_monitor = GracefulShutdown()


# --- FUNKTIONEN ---
def load_portfolio():
    try:
        with open('portfolio.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get_eur_chf_rate():
    """Holt den aktuellen Wechselkurs: Wie viel ist 1 CHF in EUR wert?"""
    try:
        forex = yf.Ticker("CHFEUR=X")
        hist = forex.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
    except Exception:
        pass
    return 1.0  # Fallback


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram Token fehlt.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"❌ Fehler beim Senden: {e}")


def analyze_market():
    portfolio_data = load_portfolio()
    report_lines = []
    alarms = []

    # Wechselkurs einmalig holen
    chf_to_eur = get_eur_chf_rate()

    total_portfolio_value = 0
    total_invested = 0

    print(f"{'Name':<25} {'Kurs (EUR)':<12} {'ATH (EUR)':<12} {'Abstand':<10} {'P/L %'}")
    print("-" * 75)

    for config in ETFS_CONFIG:
        if shutdown_monitor.kill_now:
            break

        ticker_symbol = config["ticker"]
        group = config["group"]

        pf_entry = portfolio_data.get(ticker_symbol, {})
        name = pf_entry.get("name", ticker_symbol)

        try:
            # Marktdaten holen (Max für ATH)
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="max")

            if hist.empty:
                print(f"⚠️ Keine Daten für {name} ({ticker_symbol})")
                continue

            current_price_raw = hist['Close'].iloc[-1]
            ath_price_raw = hist['High'].max()

            # Umrechnung nur für Schweizer Ticker (.SW)
            if ticker_symbol.endswith(".SW"):
                current_price = current_price_raw * chf_to_eur
                ath_price = ath_price_raw * chf_to_eur
            else:
                current_price = current_price_raw
                ath_price = ath_price_raw

            drawdown = ((current_price - ath_price) / ath_price) * 100

            # --- Portfolio Logik ---
            my_stats = ""
            qty = pf_entry.get('quantity', 0)
            profit_pct = 0.0

            if qty > 0:
                buy_price = pf_entry.get('buy_price', 0)
                invested = qty * buy_price
                current_value = qty * current_price
                profit_abs = current_value - invested
                profit_pct = ((current_price - buy_price) / buy_price) * 100

                total_portfolio_value += current_value
                total_invested += invested

                pl_icon = "📈" if profit_abs >= 0 else "📉"
                my_stats = (
                    f"\n   └ 💼 Inv: {invested:.0f}€ ({qty} Stk.)"
                    f"\n   └ {pl_icon} P/L: *{profit_abs:+.2f}€* ({profit_pct:+.2f}%)"
                )

                print(
                    f"{name[:23]:<25} {current_price:<12.2f} "
                    f"{ath_price:<12.2f} {drawdown:<10.1f} {profit_pct:+.2f}%"
                )
            else:
                my_stats = "\n   └ ⚪ *Nicht im Depot*"
                print(
                    f"{name[:23]:<25} {current_price:<12.2f} "
                    f"{ath_price:<12.2f} {drawdown:<10.1f} -"
                )

            # --- Alarm Logik ---
            alert_icon = "✅"
            t_vals = THRESHOLDS[group]

            if drawdown <= t_vals[2]:
                alert_icon = "🚨 *ALL IN*"
            elif drawdown <= t_vals[1]:
                alert_icon = "🔴 *NACHKAUF 2*"
            elif drawdown <= t_vals[0]:
                alert_icon = "🟠 *NACHKAUF 1*"
            elif drawdown <= -10:
                alert_icon = "🟡 *Warnung*"

            line = (
                f"{alert_icon} *{name}*\n"
                f"   Kurs: {current_price:.2f}€ (ATH: {ath_price:.2f})\n"
                f"   📉 Drawdown: *{drawdown:.2f}%*"
                f"{my_stats}"
            )
            report_lines.append(line)

            if drawdown <= t_vals[0]:
                alarms.append(
                    f"⚠️ HANDLUNG: {name} ist {drawdown:.1f}% unter ATH!"
                )

        except Exception as e:
            print(f"❌ Fehler bei {ticker_symbol}: {e}")

    # --- Gesamtsummen ---
    total_pl = total_portfolio_value - total_invested
    total_pl_pct = (
        (total_pl / total_invested * 100) if total_invested > 0 else 0
    )

    total_icon = "🤑" if total_pl >= 0 else "💸"
    header = (
        f"📊 *ATH-MONITOR REPORT*\n"
        f"Gesamtwert: {total_portfolio_value:.2f}€\n"
        f"{total_icon} Gesamt P/L: *{total_pl:+.2f}€* ({total_pl_pct:+.2f}%)\n"
        f"-----------------------------------\n\n"
    )

    full_msg = header + "\n\n".join(report_lines)

    if alarms:
        full_msg = (
            "🚨 *CRASH ALARM* 🚨\n\n" + "\n".join(alarms) + "\n\n" + full_msg
        )

    send_telegram(full_msg)


if __name__ == "__main__":
    print("🚀 Starte ATH-Monitor...")
    analyze_market()
    print("🏁 Fertig.")