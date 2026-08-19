#!/usr/bin/env python3
"""
Monitor disponibilità Single Studio - THE FIZZ Utrecht
=========================================================
Versione "single-run" pensata per GitHub Actions: fa UN controllo,
confronta con l'ultimo stato salvato in status.json, e se è cambiato
manda un'email. Lo scheduler (il file .yml) si occupa di rieseguirlo
ogni tot minuti, anche a PC spento.

CREDENZIALI: NON scriverle qui nel file. Vanno lette dalle variabili
d'ambiente, che imposterai come "Secrets" su GitHub (vedi istruzioni
nel file fizz-monitor.yml).
"""

import os
import json
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ============================== CONFIG ==============================

URL = "https://www.the-fizz.com/en/student-accommodation/utrecht/"

UNAVAILABLE_PHRASES = [
    "currently no single studio apartments available",
    "currently we are fully booked",
]

STATE_FILE = "status.json"

# Credenziali: lette da variabili d'ambiente (impostate come Secrets su GitHub)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]

# ======================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def check_availability() -> bool:
    """Ritorna True se sembra esserci disponibilità, False se non disponibile."""
    response = requests.get(URL, headers=HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True).lower()

    for phrase in UNAVAILABLE_PHRASES:
        if phrase in page_text:
            return False

    return True


def load_last_status():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        return data.get("available")
    except Exception:
        return None


def save_status(available: bool) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(
            {
                "available": available,
                "checked_at": datetime.now().isoformat(),
            },
            f,
        )


def send_alert_email(available: bool) -> None:
    subject = "THE FIZZ Utrecht - Disponibilita Single Studio cambiata"
    if available:
        body = (
            f"Buone notizie! Sembra che sia tornata disponibilita per i Single Studio "
            f"a THE FIZZ Utrecht.\n\n"
            f"Controlla subito qui: {URL}\n\n"
            f"Rilevato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        body = (
            f"Attenzione: lo stato e cambiato e ora risulta NON disponibile.\n\n"
            f"Controlla qui: {URL}\n\n"
            f"Rilevato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

    logging.info("Email di alert inviata.")


def main() -> None:
    logging.info(f"Controllo: {URL}")

    available = check_availability()
    status_label = "DISPONIBILE" if available else "non disponibile"
    logging.info(f"Stato attuale: {status_label}")

    last_status = load_last_status()

    if last_status is not None and available != last_status:
        logging.info("Cambio di stato rilevato! Invio email di alert...")
        send_alert_email(available)
    else:
        logging.info("Nessun cambiamento rispetto all'ultimo controllo.")

    save_status(available)


if __name__ == "__main__":
    main()
