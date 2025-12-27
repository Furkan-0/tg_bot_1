#!/usr/bin/env python3
"""
🤖 Finans Telegram Botu - Koyeb Cloud Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bu bot altın, döviz, borsa ve kripto fiyatlarını takip eder.
Koyeb bulut platformunda 7/24 çalışacak şekilde yapılandırılmıştır.

Geliştirici: Furkan ÖZTÜRK
Sürüm: 2.0 (Cloud Ready)
"""

# ================== ZORUNLU IMPORTLAR ==================
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import json
import os
import sys
import logging

# ===== Koyeb Free Plan için Dummy HTTP Server =====
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# Thread olarak başlat (botu bloklamaz)
threading.Thread(target=run_dummy_server, daemon=True).start()

# ================== LOGGING ==================
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN tanımlı değil")
    sys.exit(1)

DATA_FILE = "/tmp/kullanici_verileri.json"

# ================== USER DATA ==================
def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================== ALTIN ==================
KAYNAKLAR = {
    "Kapalıçarşı": "🏦",
    "Enpara": "🏪",
    "Ziraat Bankası": "🏪"
}

ALTIN_TURLERI = {
    "Gram Has Altın": "gram-has-altin",
    "Çeyrek Altın": "ceyrek-altin",
    "Yarım Altın": "yarim-altin",
    "Ata Altın": "ata-altin",
}

def parse_price(text):
    try:
        return float(text.replace(".", "").replace(",", "."))
    except:
        return None

def get_gold_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    soup = BeautifulSoup(
        requests.get("https://altin.doviz.com/gram-altin", headers=headers).text,
        "html.parser"
    )
    results = {}
    for row in soup.find_all("tr"):
        txt = row.get_text()
        for k in KAYNAKLAR:
            if k in txt:
                tds = row.find_all("td")
                if len(tds) >= 3:
                    alis = parse_price(tds[1].text)
                    satis = parse_price(tds[2].text)
                    if alis and satis:
                        results[k] = {
                            "alis": alis,
                            "satis": satis,
                            "makas_tl": satis - alis,
                            "makas_yuzde": (satis - alis) / alis * 100
                        }
    return results

def get_altin_turleri_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    soup = BeautifulSoup(
        requests.get("https://altin.doviz.com/", headers=headers).text,
        "html.parser"
    )
    results = {}
    for isim, key in ALTIN_TURLERI.items():
        alis = soup.find("td", {"data-socket-key": key, "data-socket-attr": "bid"})
        satis = soup.find("td", {"data-socket-key": key, "data-socket-attr": "ask"})
        if alis and satis:
            a = parse_price(alis.text)
            s = parse_price(satis.text)
            if a and s:
                results[isim] = {
                    "alis": a,
                    "satis": s,
                    "makas_tl": s - a,
                    "makas_yuzde": (s - a) / a * 100
                }
    return results

# ================== DÖVİZ ==================
PARA_BIRIMLERI = {"USD": "🇺🇸", "EUR": "🇪🇺"}

def get_para_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    soup = BeautifulSoup(
        requests.get("https://kur.doviz.com/", headers=headers).text,
        "html.parser"
    )
    data = {}
    for k in PARA_BIRIMLERI:
        alis = soup.find("td", {"data-socket-key": k, "data-socket-attr": "bid"})
        satis = soup.find("td", {"data-socket-key": k, "data-socket-attr": "ask"})
        if alis and satis:
            data[k] = {
                "alis": parse_price(alis.text),
                "satis": parse_price(satis.text)
            }
    return data

# ================== TELEGRAM ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/au Altın\n/para Döviz\n/kripto Kripto\n/borsa Borsa\n/duzenle\n/kasa"
    )

async def au(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_gold_data()
    msg = "📊 Altın\n"
    for k, v in data.items():
        msg += f"\n{k}\nAlış: {v['alis']}\nSatış: {v['satis']}"
    await update.message.reply_text(msg)

# ================== MAIN ==================
def main():
    logger.info("🚀 Bot başlatıldı (Koyeb Free uyumlu)")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("au", au))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
