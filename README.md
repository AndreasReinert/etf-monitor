# 📈 ETF Crash-Monitor & Portfolio Tracker

Ein vollautomatisierter Python-Bot, der auf **GitHub Actions** läuft. Er überwacht ETF-Kurse stündlich, berechnet den Abstand zum All-Time-High (ATH) und sendet detaillierte Berichte sowie Crash-Warnungen via **Telegram**.

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-green)

## 🚀 Was macht dieses Tool?

Dieses Projekt löst das Problem, dass man in Krisenzeiten oft zu früh oder zu spät nachkauft. Es verfolgt eine emotionslose Strategie basierend auf festen Drawdown-Schwellen.

* **ATH-Überwachung:** Berechnet live den Abstand zum historischen Höchststand (All-Time-High).
* **Währungs-Handling:** Rechnet Schweizer ETFs (CHF) automatisch live in EUR um.
* **Crash-Alarm:** Sendet sofortige Warnungen bei Erreichen von definierten Schwellen (z.B. -18%, -25%, -33%).
* **Portfolio-Tracking:** Berechnet (privat) die persönliche Performance (Gewinn/Verlust) gegen den Markt.
* **Telegram-Integration:** Schickt Statusberichte bequem aufs Smartphone.

## 🛠️ Funktionsweise

Der Bot unterscheidet zwischen normalen ETFs (Gruppe A) und volatilen Sektoren wie Banken (Gruppe B) mit unterschiedlichen Alarm-Schwellen:

| Gruppe | Typ | Schwellen (Nachkauf-Signale) |
| :--- | :--- | :--- |
| **A** | Welt/Europa/Mix | -18% / -26% / -33% |
| **B** | Volatil (z.B. Banken) | -25% / -40% / -50% |

## ⚙️ Installation & Nutzung

Da dieses Projekt **Public** ist, werden keine sensiblen Finanzdaten im Code gespeichert. Die Konfiguration erfolgt über **GitHub Secrets**.

### 1. Repository Forken / Klonen
Lade den Code herunter oder forke das Repository.

### 2. Secrets einrichten
Gehe im Repository zu `Settings` -> `Secrets and variables` -> `Actions` und erstelle folgende Secrets:

* `TELEGRAM_TOKEN`: Dein Bot-Token vom BotFather.
* `TELEGRAM_CHAT_ID`: Deine User-ID für den Empfang.
* `PORTFOLIO_JSON`: Deine Bestandsdaten im JSON-Format (siehe unten).

### 3. Das Portfolio-JSON Format
Das Skript erwartet, dass das Secret `PORTFOLIO_JSON` folgenden Aufbau hat:

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
