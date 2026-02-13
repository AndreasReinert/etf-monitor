import json
import os
import signal
import sys

import requests
import yfinance as yf
from dotenv import load_dotenv

# --- LOAD .ENV FILE ---
load_dotenv()

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Ticker mapping (ISINs mapped to Yahoo Finance tickers)
ETFS_CONFIG = [
    # ISIN: IE00BFY0GT14 (SPDR World)
    {"ticker": "SPPW.DE", "group": "A"},
    # ISIN: IE00BQN1K786 (Europe Momentum)
    {"ticker": "CEMR.DE", "group": "A"},
    # ISIN: IE00BYQCZJ13 (Japan Hedged)
    {"ticker": "WTIF.DE", "group": "A"},
    # ISIN: LU1829219390 (Amundi Banks)
    {"ticker": "BNKE.PA", "group": "B"},
    # ISIN: IE00BK5BQT80 (Vanguard All-World)
    {"ticker": "VWCE.DE", "group": "A"},
    # ISIN: LU1215828218 (EMU CHF Hedged)
    {"ticker": "XDUE.SW", "group": "A"},
    # ISIN: IE00BTJRMP35 (Emerging Markets)
    {"ticker": "XMME.DE", "group": "A"},
]

# Alert thresholds (drawdown from ATH in %)
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
        print("\n\n🛑 Shutdown signal received! Exiting gracefully...")
        sys.exit(0)


shutdown_monitor = GracefulShutdown()


# --- FUNCTIONS ---
def load_portfolio():
    try:
        with open('portfolio.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get_eur_chf_rate():
    """Fetches the current exchange rate: How much is 1 CHF worth in EUR?"""
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
        print("⚠️ Telegram token missing.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"❌ Error sending message: {e}")


def analyze_market():
    portfolio_data = load_portfolio()
    report_holdings = []
    report_watchlist = []
    alarms = []

    # Fetch exchange rate once
    chf_to_eur = get_eur_chf_rate()

    total_portfolio_value = 0
    total_invested = 0
    total_value_ytd_start = 0
    total_value_now_for_ytd = 0

    print(f"{'Name':<25} {'Price (EUR)':<12} {'ATH (EUR)':<12} "
          f"{'Drawdown':<10} {'YTD':<10} {'P/L %'}")
    print("-" * 85)

    for config in ETFS_CONFIG:
        if shutdown_monitor.kill_now:
            break

        ticker_symbol = config["ticker"]
        group = config["group"]

        pf_entry = portfolio_data.get(ticker_symbol, {})
        name = pf_entry.get("name", ticker_symbol)

        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="max")

            if hist.empty:
                print(f"⚠️ No data for {name} ({ticker_symbol})")
                continue

            current_price_raw = hist['Close'].iloc[-1]
            ath_price_raw = hist['High'].max()

            # Convert only Swiss tickers (.SW) from CHF to EUR
            if ticker_symbol.endswith(".SW"):
                current_price = current_price_raw * chf_to_eur
                ath_price = ath_price_raw * chf_to_eur
            else:
                current_price = current_price_raw
                ath_price = ath_price_raw

            drawdown = ((current_price - ath_price) / ath_price) * 100

            # --- YTD calculation (based on raw price, currency-neutral) ---
            current_year = hist.index[-1].year
            hist_ytd = hist[hist.index.year == current_year]
            if len(hist_ytd) > 1:
                ytd_start = hist_ytd['Close'].iloc[0]
                ytd_pct = ((hist_ytd['Close'].iloc[-1] - ytd_start)
                           / ytd_start) * 100
                # Max Drawdown YTD
                ytd_high = hist_ytd['High'].cummax()
                ytd_dd = ((hist_ytd['Close'] - ytd_high) / ytd_high) * 100
                max_dd_ytd = ytd_dd.min()
            else:
                ytd_pct = 0.0
                max_dd_ytd = 0.0

            # --- Trend (SMA20) ---
            if len(hist) >= 20:
                sma20 = hist['Close'].rolling(20).mean().iloc[-1]
                trend_icon = "↗️" if current_price_raw >= sma20 else "↘️"
            else:
                trend_icon = "➡️"

            # --- Recovery distance ---
            if drawdown < 0:
                recovery_pct = ((ath_price - current_price)
                                / current_price) * 100
            else:
                recovery_pct = 0.0

            qty = pf_entry.get('quantity', 0)

            # --- Alert icon logic ---
            t_vals = THRESHOLDS[group]
            if drawdown <= t_vals[2]:
                alert_icon = "🚨 *ALL IN*"
            elif drawdown <= t_vals[1]:
                alert_icon = "🔴 *BUY 2*"
            elif drawdown <= t_vals[0]:
                alert_icon = "🟠 *BUY 1*"
            elif drawdown <= -10:
                alert_icon = "🟡 *Warning*"
            else:
                # Blue for watchlist, green for holdings
                alert_icon = "✅" if qty > 0 else "🔵"

            # --- Portfolio logic ---
            if qty > 0:
                buy_price = pf_entry.get('buy_price', 0)
                invested = qty * buy_price
                current_value = qty * current_price
                profit_abs = current_value - invested
                profit_pct = ((current_price - buy_price) / buy_price) * 100

                total_portfolio_value += current_value
                total_invested += invested

                # YTD value for portfolio-level YTD
                if len(hist_ytd) > 1:
                    if ticker_symbol.endswith(".SW"):
                        ytd_start_eur = ytd_start * chf_to_eur
                    else:
                        ytd_start_eur = ytd_start
                    total_value_ytd_start += qty * ytd_start_eur
                    total_value_now_for_ytd += qty * current_price

                pl_icon = "📈" if profit_abs >= 0 else "📉"
                my_stats = (
                    f"\n   └ 💼 Inv: {invested:.0f}€ ({qty} pcs)"
                    f"\n   └ {pl_icon} P/L: *{profit_abs:+.2f}€* "
                    f"({profit_pct:+.2f}%)"
                )
                print(f"{name[:23]:<25} {current_price:<12.2f} "
                      f"{ath_price:<12.2f} {drawdown:<10.1f} "
                      f"{ytd_pct:<+10.2f} {profit_pct:+.2f}%")
            else:
                my_stats = "\n   └ ⚪ *No position*"
                print(f"{name[:23]:<25} {current_price:<12.2f} "
                      f"{ath_price:<12.2f} {drawdown:<10.1f} "
                      f"{ytd_pct:<+10.2f} -")

            # Recovery text only when in drawdown
            recovery_str = (
                f"\n   🔄 Recovery needed: *+{recovery_pct:.1f}%*"
                if recovery_pct > 0 else ""
            )

            line = (
                f"{alert_icon} {trend_icon} *{name}*\n"
                f"   Price: {current_price:.2f}€ (ATH: {ath_price:.2f})\n"
                f"   📉 Drawdown: *{drawdown:.2f}%*"
                f"  |  📅 YTD: *{ytd_pct:+.2f}%*\n"
                f"   📊 Max DD YTD: *{max_dd_ytd:.2f}%*"
                f"{recovery_str}"
                f"{my_stats}"
            )

            # Sort for report: holdings first, then watchlist
            if qty > 0:
                report_holdings.append(line)
            else:
                report_watchlist.append(line)

            if drawdown <= t_vals[0]:
                alarms.append(
                    f"⚠️ ACTION: {name} is {drawdown:.1f}% below ATH!"
                )

        except Exception as e:
            print(f"❌ Error processing {ticker_symbol}: {e}")

    # --- Totals ---
    total_pl = total_portfolio_value - total_invested
    total_pl_pct = (
        (total_pl / total_invested * 100) if total_invested > 0 else 0
    )

    total_icon = "🤑" if total_pl >= 0 else "💸"
    portfolio_ytd_pct = (
        ((total_value_now_for_ytd - total_value_ytd_start)
         / total_value_ytd_start * 100)
        if total_value_ytd_start > 0 else 0
    )
    ytd_icon = "📈" if portfolio_ytd_pct >= 0 else "📉"
    header = (
        f"📊 *ATH MONITOR REPORT*\n"
        f"Total Value: {total_portfolio_value:.2f}€\n"
        f"{total_icon} Total P/L: *{total_pl:+.2f}€* "
        f"({total_pl_pct:+.2f}%)\n"
        f"{ytd_icon} Portfolio YTD: *{portfolio_ytd_pct:+.2f}%*\n"
        f"-----------------------------------\n\n"
    )

    # Build report: holdings first, then watchlist
    holdings_str = ("*HOLDINGS:*\n" + "\n\n".join(report_holdings)
                    if report_holdings else "")
    watch_str = ("\n\n*WATCHLIST:*\n" + "\n\n".join(report_watchlist)
                 if report_watchlist else "")

    full_msg = header + holdings_str + watch_str

    if alarms:
        full_msg = (
            "🚨 *CRASH ALERT* 🚨\n\n" + "\n".join(alarms) + "\n\n"
            + full_msg
        )

    send_telegram(full_msg)


if __name__ == "__main__":
    print("🚀 Starting ATH Monitor...")
    analyze_market()
    print("🏁 Done.")
