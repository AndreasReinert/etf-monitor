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


# --- FORMATTING HELPERS ---
def fmt_eur(value, decimals=2, signed=False):
    """Formats a number with thousands separator (German style: 1.234,56)."""
    fmt = f"{{:{'+' if signed else ''},.{decimals}f}}"
    s = fmt.format(value)
    # Convert US-style 1,234.56 to German-style 1.234,56
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def fmt_pct(value, decimals=2, signed=True):
    """Formats a percentage value (German decimal comma)."""
    fmt = f"{{:{'+' if signed else ''}.{decimals}f}}"
    return fmt.format(value).replace(".", ",")


def progress_bar(current_dd, thresholds, width=12):
    """
    Visual progress bar showing how deep the drawdown is, scaled
    against the deepest "ALL IN" threshold (=full bar).
    """
    deepest = thresholds[2]  # e.g. -33% or -50%
    if current_dd >= 0:
        ratio = 0.0
    else:
        ratio = min(abs(current_dd) / abs(deepest), 1.0)
    filled = int(round(ratio * width))
    return "▓" * filled + "░" * (width - filled)


def escape_md(text):
    """Sanitise text for Telegram Markdown (legacy mode)."""
    return str(text).replace("_", " ").replace("*", "")


# --- DATA FUNCTIONS ---
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


# --- MESSAGE BUILDERS ---
def build_holding_card(name, alert_icon, trend_icon, current_price, ath_price,
                       drawdown, ytd_pct, max_dd_ytd, recovery_pct, qty,
                       buy_price, current_value, profit_abs, profit_pct,
                       dd_bar):
    """Builds the message card for an ETF position that is held.
    The P/L block is the visual hero of the card.
    """
    pl_arrow = "📈" if profit_abs >= 0 else "📉"
    pl_dot = "🟢" if profit_abs >= 0 else "🔴"

    # Quantity display: integer if whole number, else 4 decimals (German style)
    if float(qty).is_integer():
        qty_str = f"{int(qty)}"
    else:
        qty_str = f"{qty:.4f}".replace(".", ",")

    # Hero P/L block — most important info, framed for emphasis
    pl_block = (
        f"┌─ 💰 *P/L* ─────────────\n"
        f"│ {pl_dot} *{fmt_eur(profit_abs, signed=True)} €*  "
        f"({fmt_pct(profit_pct)}%) {pl_arrow}\n"
        f"│ Einstand: `{fmt_eur(buy_price)} €`  →  "
        f"Aktuell: `{fmt_eur(current_price)} €`\n"
        f"│ {qty_str} Stk · Wert: `{fmt_eur(current_value)} €`\n"
        f"└────────────────────────"
    )

    # Drawdown block with visual bar
    if recovery_pct > 0:
        recovery_line = (
            f"\n   🔄 Recovery: *+{fmt_pct(recovery_pct, signed=False)}%* nötig"
        )
    else:
        recovery_line = ""

    dd_block = (
        f"📉 DD: *{fmt_pct(drawdown)}%*  │  ATH: `{fmt_eur(ath_price)} €`\n"
        f"   `{dd_bar}`"
        f"{recovery_line}"
    )

    # YTD line
    ytd_dot = "🟢" if ytd_pct >= 0 else "🔴"
    ytd_block = (
        f"📅 YTD: {ytd_dot} *{fmt_pct(ytd_pct)}%*  "
        f"│  Max DD: `{fmt_pct(max_dd_ytd)}%`"
    )

    card = (
        f"{alert_icon} {trend_icon} *{escape_md(name)}*\n"
        f"{pl_block}\n"
        f"{dd_block}\n"
        f"{ytd_block}"
    )
    return card


def build_watchlist_card(name, alert_icon, trend_icon, current_price,
                         ath_price, drawdown, ytd_pct, max_dd_ytd,
                         recovery_pct, dd_bar):
    """Builds the message card for a watchlist ETF (no position)."""
    if recovery_pct > 0:
        recovery_line = (
            f"\n   🔄 Recovery: *+{fmt_pct(recovery_pct, signed=False)}%* nötig"
        )
    else:
        recovery_line = ""

    ytd_dot = "🟢" if ytd_pct >= 0 else "🔴"

    card = (
        f"{alert_icon} {trend_icon} *{escape_md(name)}*  ⚪️ _watchlist_\n"
        f"   Kurs: `{fmt_eur(current_price)} €`  │  "
        f"ATH: `{fmt_eur(ath_price)} €`\n"
        f"   📉 DD: *{fmt_pct(drawdown)}%*  `{dd_bar}`"
        f"{recovery_line}\n"
        f"   📅 YTD: {ytd_dot} *{fmt_pct(ytd_pct)}%*  "
        f"│  Max DD: `{fmt_pct(max_dd_ytd)}%`"
    )
    return card


def build_header(total_value, total_invested, total_pl, total_pl_pct,
                 portfolio_ytd_pct):
    """Portfolio header with prominent overall P/L."""
    pl_dot = "🟢" if total_pl >= 0 else "🔴"
    pl_arrow = "📈" if total_pl >= 0 else "📉"
    ytd_dot = "🟢" if portfolio_ytd_pct >= 0 else "🔴"

    header = (
        f"📊 *ATH MONITOR REPORT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"┌─ 💎 *PORTFOLIO* ───────\n"
        f"│ Wert:    `{fmt_eur(total_value)} €`\n"
        f"│ Invest:  `{fmt_eur(total_invested)} €`\n"
        f"│\n"
        f"│ {pl_dot} *P/L: {fmt_eur(total_pl, signed=True)} €*\n"
        f"│    ({fmt_pct(total_pl_pct)}%) {pl_arrow}\n"
        f"│\n"
        f"│ {ytd_dot} YTD: *{fmt_pct(portfolio_ytd_pct)}%*\n"
        f"└────────────────────────\n"
    )
    return header


# --- MAIN ANALYSIS ---
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
                alert_icon = "✅" if qty > 0 else "🔵"

            # Drawdown progress bar
            dd_bar = progress_bar(drawdown, t_vals, width=12)

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

                print(f"{name[:23]:<25} {current_price:<12.2f} "
                      f"{ath_price:<12.2f} {drawdown:<10.1f} "
                      f"{ytd_pct:<+10.2f} {profit_pct:+.2f}%")

                card = build_holding_card(
                    name=name,
                    alert_icon=alert_icon,
                    trend_icon=trend_icon,
                    current_price=current_price,
                    ath_price=ath_price,
                    drawdown=drawdown,
                    ytd_pct=ytd_pct,
                    max_dd_ytd=max_dd_ytd,
                    recovery_pct=recovery_pct,
                    qty=qty,
                    buy_price=buy_price,
                    current_value=current_value,
                    profit_abs=profit_abs,
                    profit_pct=profit_pct,
                    dd_bar=dd_bar,
                )
                report_holdings.append(card)
            else:
                print(f"{name[:23]:<25} {current_price:<12.2f} "
                      f"{ath_price:<12.2f} {drawdown:<10.1f} "
                      f"{ytd_pct:<+10.2f} -")

                card = build_watchlist_card(
                    name=name,
                    alert_icon=alert_icon,
                    trend_icon=trend_icon,
                    current_price=current_price,
                    ath_price=ath_price,
                    drawdown=drawdown,
                    ytd_pct=ytd_pct,
                    max_dd_ytd=max_dd_ytd,
                    recovery_pct=recovery_pct,
                    dd_bar=dd_bar,
                )
                report_watchlist.append(card)

            if drawdown <= t_vals[0]:
                alarms.append(
                    f"⚠️ {escape_md(name)}: *{fmt_pct(drawdown)}%* unter ATH"
                )

        except Exception as e:
            print(f"❌ Error processing {ticker_symbol}: {e}")

    # --- Totals ---
    total_pl = total_portfolio_value - total_invested
    total_pl_pct = (
        (total_pl / total_invested * 100) if total_invested > 0 else 0
    )

    portfolio_ytd_pct = (
        ((total_value_now_for_ytd - total_value_ytd_start)
         / total_value_ytd_start * 100)
        if total_value_ytd_start > 0 else 0
    )

    header = build_header(
        total_value=total_portfolio_value,
        total_invested=total_invested,
        total_pl=total_pl,
        total_pl_pct=total_pl_pct,
        portfolio_ytd_pct=portfolio_ytd_pct,
    )

    # Section dividers
    holdings_str = (
        "\n*━━━━━ 💼 HOLDINGS ━━━━━*\n\n"
        + "\n\n".join(report_holdings)
        if report_holdings else ""
    )
    watch_str = (
        "\n\n*━━━━━ 👀 WATCHLIST ━━━━━*\n\n"
        + "\n\n".join(report_watchlist)
        if report_watchlist else ""
    )

    full_msg = header + holdings_str + watch_str

    if alarms:
        alarm_block = (
            "🚨 *━━━ CRASH ALERT ━━━* 🚨\n\n"
            + "\n".join(alarms)
            + "\n\n"
        )
        full_msg = alarm_block + full_msg

    send_telegram(full_msg)
    return full_msg


if __name__ == "__main__":
    print("🚀 Starting ATH Monitor...")
    analyze_market()
    print("🏁 Done.")
