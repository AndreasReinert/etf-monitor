# 📈 ETF Crash-Monitor & Portfolio Tracker

Ein vollautomatisierter Python-Bot, der auf GitHub Actions läuft. Er überwacht ETF-Kurse alle 60 Minuten, berechnet den Abstand zum All-Time-High (ATH) und sendet detaillierte Berichte sowie Crash-Warnungen via Telegram.

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-green)
---

## 🚀 Was macht dieses Tool?

Dieses Projekt löst das Problem, dass man in Krisenzeiten oft zu früh oder zu spät nachkauft. Es verfolgt eine emotionslose Strategie basierend auf festen Drawdown-Schwellen.

- **ATH-Überwachung:** Berechnet live den Abstand zum historischen Höchststand (All-Time-High).
- **Währungs-Handling:** Rechnet Schweizer ETFs (CHF) automatisch live in EUR um.
- **Crash-Alarm:** Sendet sofortige Warnungen bei Erreichen von definierten Schwellen (z.B. -18%, -25%, -33%).
- **Portfolio-Tracking:** Berechnet (privat) die persönliche Performance (Gewinn/Verlust) gegen den Markt.
- **Telegram-Integration:** Schickt Statusberichte bequem aufs Smartphone.

---

## 📊 Kennzahlen im Detail

Der Report liefert für jeden ETF folgende Kennzahlen:

### Drawdown vom ATH

Der prozentuale Abstand zwischen dem aktuellen Kurs und dem historischen Höchstkurs (All-Time-High). Dies ist die zentrale Kennzahl des Tools – sie bestimmt, ob ein Nachkauf-Signal ausgelöst wird.

**Beispiel:** ATH war 50.00€, aktueller Kurs ist 40.00€ → Drawdown: -20.00%

### 📅 YTD (Year-to-Date)

Die Kurs-Performance seit dem ersten Handelstag des laufenden Jahres. Zeigt, wie sich der ETF im aktuellen Kalenderjahr entwickelt hat – unabhängig vom persönlichen Kaufzeitpunkt.

**Beispiel:** Kurs am 2. Januar: 45.00€, aktueller Kurs: 48.60€ → YTD: +8.00%

### 📊 Max Drawdown YTD

Der tiefste Rückgang vom jeweiligen Jahreshoch bis zum tiefsten Punkt im laufenden Jahr. Diese Kennzahl zeigt, wie schlimm es in diesem Jahr bereits war.

**Warum ist das nützlich?** In Kombination mit dem aktuellen Drawdown erkennt man, ob sich der ETF bereits erholt. Wenn der aktuelle Drawdown -15% beträgt, der Max DD YTD aber -25% war, hat bereits eine deutliche Erholung stattgefunden.

**Beispiel:** Der ETF erreichte im März ein Jahreshoch von 52€, fiel im April auf 39€ → Max DD YTD: -25.00%

### ↗️ / ↘️ Trend-Indikator (SMA20)

Ein Trendpfeil neben dem ETF-Namen, basierend auf dem 20-Tage gleitenden Durchschnitt (Simple Moving Average). Liegt der aktuelle Kurs über dem SMA20, zeigt der Pfeil nach oben (↗️) – der kurzfristige Trend ist positiv. Liegt er darunter, zeigt er nach unten (↘️).

**Warum SMA20?** Der 20-Tage-Durchschnitt ist ein guter Kompromiss: robuster als ein Tagesvergleich (weniger Rauschen), aber reaktiver als der SMA200 (erkennt Trendwechsel schneller). Ideal für die Einschätzung, ob ein Drawdown gerade noch zunimmt oder die Erholung bereits begonnen hat.

**Beispiel:** Kurs: 42.00€, SMA20: 40.50€ → ↗️ (Kurs über Durchschnitt = Aufwärtstrend)

### 🔄 Recovery-Distanz

Zeigt an, wie viel Prozent der ETF steigen müsste, um sein ATH wieder zu erreichen. Wird nur angezeigt, wenn sich der ETF im Drawdown befindet.

**Warum ist das wichtig?** Drawdowns und Recoveries sind asymmetrisch. Ein Verlust von -33% erfordert einen Anstieg von +49%, um den Ausgangspunkt wieder zu erreichen. Diese Kennzahl macht die tatsächliche Erholungsdistanz sichtbar und hilft, realistische Erwartungen zu setzen.

**Beispiel:** ATH: 50.00€, aktueller Kurs: 33.50€ → Recovery nötig: +49.3%

### Portfolio-Header

Im Kopf des Reports werden aggregierte Werte über alle gehaltenen Positionen angezeigt:

- **Gesamtwert:** Aktueller Marktwert aller Positionen in EUR.
- **Gesamt P/L:** Gewinn oder Verlust in EUR und Prozent über alle Positionen.
- **Portfolio YTD:** Gewichtete YTD-Performance aller gehaltenen Positionen. Grössere Positionen haben proportional mehr Einfluss auf den Gesamtwert. _Hinweis: Nachkäufe während des Jahres können die Berechnung leicht verzerren, da die aktuelle Stückzahl auf den Jahresanfangskurs angewendet wird._

---

## 🚨 Alarm-Schwellen & Signale

Der Bot unterscheidet zwischen normalen ETFs (Gruppe A) und volatilen Sektoren wie Banken (Gruppe B) mit unterschiedlichen Alarm-Schwellen:

| Gruppe | Typ | Schwellen (Nachkauf-Signale) |
|--------|-----|------------------------------|
| A | Welt / Europa / Mix | -18% / -26% / -33% |
| B | Volatil (z.B. Banken) | -25% / -40% / -50% |

### Signal-Icons im Report

| Icon | Bedeutung |
|------|-----------|
| ✅ | Alles in Ordnung – Position im Bestand |
| 🔵 | Watchlist – kein Bestand |
| 🟡 *Warnung* | Drawdown > -10% – Markt unter Beobachtung |
| 🟠 *NACHKAUF 1* | Erste Schwelle erreicht – moderater Nachkauf |
| 🔴 *NACHKAUF 2* | Zweite Schwelle erreicht – aggressiver Nachkauf |
| 🚨 *ALL IN* | Dritte Schwelle erreicht – maximale Position |
| ↗️ | Kurzfristiger Aufwärtstrend (Kurs über SMA20) |
| ↘️ | Kurzfristiger Abwärtstrend (Kurs unter SMA20) |

---

## 📱 Beispiel Telegram-Report

```
📊 ATH-MONITOR REPORT
Gesamtwert: 12345.67€
🤑 Gesamt P/L: +1234.56€ (+10.50%)
📈 Portfolio YTD: +5.23%
-----------------------------------

DEPO-BESTAND:
🟠 NACHKAUF 1 ↘️ SPDR MSCI World
   Kurs: 32.45€ (ATH: 41.20)
   📉 Drawdown: -21.24%  |  📅 YTD: -8.35%
   📊 Max DD YTD: -26.10%
   🔄 Recovery nötig: +26.9%
   └ 💼 Inv: 5708€ (150 Stk.)
   └ 📉 P/L: -345.70€ (-6.91%)

✅ ↗️ Amundi Euro Stoxx Banks
   Kurs: 265.40€ (ATH: 280.10)
   📉 Drawdown: -5.25%  |  📅 YTD: +12.80%
   📊 Max DD YTD: -14.30%
   └ 💼 Inv: 4068€ (17 Stk.)
   └ 📈 P/L: +443.80€ (+10.91%)

WATCHLIST:
🔵 ↗️ Vanguard FTSE All-World
   Kurs: 118.50€ (ATH: 125.80)
   📉 Drawdown: -5.80%  |  📅 YTD: +3.20%
   📊 Max DD YTD: -9.40%
   🔄 Recovery nötig: +6.2%
   └ ⚪ Kein Bestand
```

---

## ⚙️ Installation & Nutzung

Da dieses Projekt Public ist, werden keine sensiblen Finanzdaten im Code gespeichert. Die Konfiguration erfolgt über GitHub Secrets.

### 1. Repository Forken / Klonen

Lade den Code herunter oder forke das Repository.

### 2. Secrets einrichten

Gehe im Repository zu `Settings` → `Secrets and variables` → `Actions` und erstelle folgende Secrets:

- **`TELEGRAM_TOKEN`**: Dein Bot-Token vom BotFather.
- **`TELEGRAM_CHAT_ID`**: Deine User-ID für den Empfang.
- **`PORTFOLIO_JSON`**: Deine Bestandsdaten im JSON-Format (siehe unten).

### 3. Das Portfolio-JSON Format

Das Skript erwartet, dass das Secret `PORTFOLIO_JSON` folgenden Aufbau hat. Kopiere von `{` bis `}` alles ins Secret:

```json
{
  "SPPW.DE": {
    "name": "SPDR MSCI World",
    "buy_price": 38.05,
    "quantity": 150
  },
  "BNKE.PA": {
    "name": "Amundi Euro Stoxx Banks",
    "buy_price": 239.30,
    "quantity": 17
  }
}
```

### 4. GitHub Actions

Der Bot läuft automatisch alle 60 Minuten via GitHub Actions Workflow. Kein eigener Server nötig.

---

## 🛠️ Technische Details

- **Datenquelle:** Yahoo Finance via `yfinance`
- **Währungsumrechnung:** Automatisch für `.SW`-Ticker (CHF → EUR) via Live-Wechselkurs
- **Laufzeit:** Python 3.x auf GitHub Actions
- **Abhängigkeiten:** `yfinance`, `requests`, `python-dotenv`

---
---

# 🇬🇧 English Version

# 📈 ETF Crash Monitor & Portfolio Tracker

A fully automated Python bot running on GitHub Actions. It monitors ETF prices every 60 minutes, calculates the distance to the All-Time-High (ATH), and sends detailed reports and crash alerts via Telegram.

---

## 🚀 What does this tool do?

This project solves the problem of buying too early or too late during market crises. It follows an emotion-free strategy based on fixed drawdown thresholds.

- **ATH Monitoring:** Calculates the live distance to the historical all-time-high.
- **Currency Handling:** Automatically converts Swiss ETFs (CHF) to EUR in real-time.
- **Crash Alerts:** Sends immediate warnings when defined thresholds are hit (e.g. -18%, -25%, -33%).
- **Portfolio Tracking:** Calculates personal performance (profit/loss) against market prices.
- **Telegram Integration:** Delivers status reports directly to your smartphone.

---

## 📊 Metrics in Detail

The report provides the following metrics for each ETF:

### Drawdown from ATH

The percentage distance between the current price and the historical all-time-high. This is the core metric of the tool – it determines whether a buy signal is triggered.

**Example:** ATH was 50.00€, current price is 40.00€ → Drawdown: -20.00%

### 📅 YTD (Year-to-Date)

The price performance since the first trading day of the current year. Shows how the ETF has performed in the current calendar year – independent of your personal buy date.

**Example:** Price on Jan 2: 45.00€, current price: 48.60€ → YTD: +8.00%

### 📊 Max Drawdown YTD

The deepest decline from the respective year-to-date high to the lowest point in the current year. This metric shows the worst it has been this year.

**Why is this useful?** Combined with the current drawdown, you can see whether the ETF is already recovering. If the current drawdown is -15% but the max DD YTD was -25%, a significant recovery has already taken place.

**Example:** The ETF reached a year-high of 52€ in March, fell to 39€ in April → Max DD YTD: -25.00%

### ↗️ / ↘️ Trend Indicator (SMA20)

A trend arrow next to the ETF name, based on the 20-day Simple Moving Average. If the current price is above the SMA20, the arrow points up (↗️) – the short-term trend is positive. Below it, the arrow points down (↘️).

**Why SMA20?** The 20-day average is a good compromise: more robust than a day-over-day comparison (less noise), but more reactive than the SMA200 (catches trend changes faster). Ideal for assessing whether a drawdown is still deepening or recovery has already begun.

**Example:** Price: 42.00€, SMA20: 40.50€ → ↗️ (price above average = uptrend)

### 🔄 Recovery Distance

Shows the percentage the ETF would need to rise to reach its ATH again. Only displayed when the ETF is in a drawdown.

**Why does this matter?** Drawdowns and recoveries are asymmetric. A -33% loss requires a +49% gain to break even. This metric makes the actual recovery distance visible and helps set realistic expectations.

**Example:** ATH: 50.00€, current price: 33.50€ → Recovery needed: +49.3%

### Portfolio Header

The report header shows aggregated values across all held positions:

- **Total Value:** Current market value of all positions in EUR.
- **Total P/L:** Profit or loss in EUR and percent across all positions.
- **Portfolio YTD:** Weighted YTD performance of all held positions. Larger positions have proportionally more influence on the total. _Note: Mid-year purchases may slightly skew the calculation, as the current quantity is applied to the year-start price._

---

## 🚨 Alert Thresholds & Signals

The bot differentiates between standard ETFs (Group A) and volatile sectors like banks (Group B) with different alert thresholds:

| Group | Type | Thresholds (Buy Signals) |
|-------|------|--------------------------|
| A | World / Europe / Mix | -18% / -26% / -33% |
| B | Volatile (e.g. Banks) | -25% / -40% / -50% |

### Signal Icons in the Report

| Icon | Meaning |
|------|---------|
| ✅ | All good – position held |
| 🔵 | Watchlist – no position |
| 🟡 *Warning* | Drawdown > -10% – market under observation |
| 🟠 *BUY 1* | First threshold reached – moderate buy |
| 🔴 *BUY 2* | Second threshold reached – aggressive buy |
| 🚨 *ALL IN* | Third threshold reached – maximum position |
| ↗️ | Short-term uptrend (price above SMA20) |
| ↘️ | Short-term downtrend (price below SMA20) |

---

## ⚙️ Installation & Usage

Since this project is public, no sensitive financial data is stored in code. Configuration is done via GitHub Secrets.

### 1. Fork / Clone the Repository

Download the code or fork the repository.

### 2. Set up Secrets

Go to `Settings` → `Secrets and variables` → `Actions` in your repository and create the following secrets:

- **`TELEGRAM_TOKEN`**: Your bot token from BotFather.
- **`TELEGRAM_CHAT_ID`**: Your user ID for receiving messages.
- **`PORTFOLIO_JSON`**: Your holdings data in JSON format (see below).

### 3. Portfolio JSON Format

The script expects the `PORTFOLIO_JSON` secret to have the following structure. Copy everything from `{` to `}` into the secret:

```json
{
  "SPPW.DE": {
    "name": "SPDR MSCI World",
    "buy_price": 38.05,
    "quantity": 150
  },
  "BNKE.PA": {
    "name": "Amundi Euro Stoxx Banks",
    "buy_price": 239.30,
    "quantity": 17
  }
}
```

### 4. GitHub Actions

The bot runs automatically every 60 minutes via GitHub Actions workflow. No dedicated server required.

---

## 🛠️ Technical Details

- **Data Source:** Yahoo Finance via `yfinance`
- **Currency Conversion:** Automatic for `.SW` tickers (CHF → EUR) via live exchange rate
- **Runtime:** Python 3.x on GitHub Actions
- **Dependencies:** `yfinance`, `requests`, `python-dotenv`
