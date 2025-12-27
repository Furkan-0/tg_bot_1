#!/usr/bin/env python3
"""
🤖 Finans Telegram Botu - Koyeb Cloud Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bu bot altın, döviz, borsa ve kripto fiyatlarını takip eder.
Koyeb bulut platformunda 7/24 çalışacak şekilde yapılandırılmıştır.

Geliştirici: Furkan ÖZTÜRK
Sürüm: 2.0 (Cloud Ready)

Environment Variables (Koyeb'de tanımlanmalı):
  - BOT_TOKEN: Telegram Bot Token (@BotFather'dan alınır)
  - CHAT_ID: Telegram Chat ID (opsiyonel)

Kullanım:
  python lap.py
"""

import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import json
import os
import sys
import logging

# ========== LOGGING AYARLARI ==========
# Bulut ortamında log takibi için
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ========== ENVIRONMENT VARIABLES ==========
# Gizli bilgiler environment variable olarak alınır (Koyeb'de tanımlanmalı)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "")

# Token kontrolü
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN environment variable tanımlanmamış!")
    logger.error("Koyeb Dashboard > Service > Environment Variables bölümünden ekleyin.")
    sys.exit(1)

logger.info("✅ Bot Token yüklendi.")

# ========== VERİ DOSYASI ==========
# Bulut ortamında /tmp dizini kullanılır (yazılabilir alan)
DATA_FILE = os.getenv("DATA_FILE_PATH", "/tmp/kullanici_verileri.json")

def load_user_data():
    """Kullanıcı verilerini dosyadan yükler."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Veri yükleme hatası: {e}")
    return {}

def save_user_data(data):
    """Kullanıcı verilerini dosyaya kaydeder."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Veri kaydetme hatası: {e}")
        return False

KAYNAKLAR = {
    "Kapalıçarşı": "🏦",
    "Enpara": "🏪",
    "Ziraat Bankası": "🏪"
}

# Varsayılan miktar (gram)
DEFAULT_MIKTAR = 65.0

def parse_price(text):
    try:
        clean = text.replace(".", "").replace(",", ".").strip()
        return float(clean)
    except:
        return None

def get_gold_data():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get("https://altin.doviz.com/gram-altin", headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = {}
        rows = soup.find_all("tr")
        
        for row in rows:
            row_text = row.get_text()
            for kaynak in KAYNAKLAR.keys():
                if kaynak in row_text:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        alis = parse_price(cells[1].get_text())
                        satis = parse_price(cells[2].get_text())
                        
                        if alis and satis:
                            makas_tl = satis - alis
                            makas_yuzde = (makas_tl / alis) * 100
                            
                            results[kaynak] = {
                                "alis": alis,
                                "satis": satis,
                                "makas_tl": makas_tl,
                                "makas_yuzde": makas_yuzde
                            }
                    break
        
        return results
    except Exception as e:
        print(f"Scraping hatası: {e}")
        return {}

def format_message(data):
    if not data:
        return "❌ Veri alınamadı."
    
    message = "📊 Gram Altın Karşılaştırması\n"
    
    for kaynak in KAYNAKLAR.keys():
        if kaynak in data:
            info = data[kaynak]
            emoji = KAYNAKLAR[kaynak]
            message += f"\n{emoji} {kaynak}\n"
            message += f"Alış: {info['alis']:.2f} TL\n"
            message += f"Satış: {info['satis']:.2f} TL\n"
            message += f"Makas: %{info['makas_yuzde']:.2f} | {info['makas_tl']:.2f} TL\n"
    
    return message

# Altın türleri için socket key eşleştirmeleri
ALTIN_TURLERI = {
    "Gram Has Altın": "gram-has-altin",
    "Çeyrek Altın": "ceyrek-altin",
    "Yarım Altın": "yarim-altin",
    "Ata Altın": "ata-altin",
}

def get_altin_turleri_data():
    """altin.doviz.com'dan Ata, Yarım, Çeyrek ve Gram Has Altın fiyatlarını çeker."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get("https://altin.doviz.com/", headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = {}
        
        for isim, socket_key in ALTIN_TURLERI.items():
            try:
                # data-socket-key ve data-socket-attr ile fiyatları bul
                alis_elem = soup.find("td", {"data-socket-key": socket_key, "data-socket-attr": "bid"})
                satis_elem = soup.find("td", {"data-socket-key": socket_key, "data-socket-attr": "ask"})
                
                if alis_elem and satis_elem:
                    alis = parse_price(alis_elem.get_text(strip=True))
                    satis = parse_price(satis_elem.get_text(strip=True))
                    
                    if alis and satis:
                        makas_tl = satis - alis
                        makas_yuzde = (makas_tl / alis) * 100
                        
                        results[isim] = {
                            "alis": alis,
                            "satis": satis,
                            "makas_tl": makas_tl,
                            "makas_yuzde": makas_yuzde
                        }
            except Exception as e:
                print(f"{isim} parse hatası: {e}")
                continue
        
        return results
    except Exception as e:
        print(f"Altın türleri scraping hatası: {e}")
        return {}

def format_altin_turleri_message(data):
    if not data:
        return "❌ Altın türleri verisi alınamadı."
    
    message = "🪙 Altın Fiyatları (doviz.com)\n"
    
    for isim in ALTIN_TURLERI.keys():
        if isim in data:
            info = data[isim]
            message += f"\n• {isim}\n"
            message += f"  Alış: {info['alis']:,.2f} TL\n"
            message += f"  Satış: {info['satis']:,.2f} TL\n"
            message += f"  Makas: %{info['makas_yuzde']:.2f} | {info['makas_tl']:,.2f} TL\n"
    
    return message

# ========== PARA BİRİMLERİ (USD/EUR) ==========
PARA_BIRIMLERI = {
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
}

def get_para_data():
    """kur.doviz.com'dan USD ve EUR fiyatlarını çeker."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get("https://kur.doviz.com/", headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = {}
        
        for kod in PARA_BIRIMLERI.keys():
            try:
                alis_elem = soup.find("td", {"data-socket-key": kod, "data-socket-attr": "bid"})
                satis_elem = soup.find("td", {"data-socket-key": kod, "data-socket-attr": "ask"})
                
                if alis_elem and satis_elem:
                    alis = parse_price(alis_elem.get_text(strip=True))
                    satis = parse_price(satis_elem.get_text(strip=True))
                    
                    if alis and satis:
                        results[kod] = {"alis": alis, "satis": satis}
            except Exception as e:
                print(f"{kod} parse hatası: {e}")
                continue
        
        return results
    except Exception as e:
        print(f"Para birimi scraping hatası: {e}")
        return {}

def format_para_message(data):
    if not data:
        return "❌ Döviz verisi alınamadı."
    
    message = "💱 Döviz Kurları\n"
    
    for kod in PARA_BIRIMLERI.keys():
        if kod in data:
            info = data[kod]
            emoji = PARA_BIRIMLERI[kod]
            message += f"\n{emoji} {kod}\n"
            message += f"  Alış: {info['alis']:.4f} TL\n"
            message += f"  Satış: {info['satis']:.4f} TL\n"
    
    return message

# ========== BORSA (BIST100/BIST30) ==========
def get_borsa_data():
    """borsa.doviz.com'dan BIST100 ve BIST30 verilerini çeker."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get("https://borsa.doviz.com/", headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = {}
        
        for kod in ["XU100", "XU030"]:
            try:
                li_elem = soup.find("li", {"data-container": kod})
                if li_elem:
                    change_elem = li_elem.find("span", class_="change")
                    if change_elem:
                        degisim = change_elem.get_text(strip=True)
                        results[kod] = {"degisim": degisim}
            except Exception as e:
                print(f"{kod} parse hatası: {e}")
                continue
        
        return results
    except Exception as e:
        print(f"Borsa scraping hatası: {e}")
        return {}

def format_borsa_message(data):
    if not data:
        return "❌ Borsa verisi alınamadı."
    
    message = "📈 Borsa İstanbul\n"
    
    isimler = {"XU100": "BIST 100", "XU030": "BIST 30"}
    
    for kod in ["XU100", "XU030"]:
        if kod in data:
            info = data[kod]
            isim = isimler.get(kod, kod)
            emoji = "🟢" if "+" in info["degisim"] or info["degisim"].startswith("%") and "-" not in info["degisim"] else "🔴"
            message += f"\n{emoji} {isim}: {info['degisim']}\n"
    
    return message

# ========== KRİPTO (BTC/ETH) ==========
KRIPTO_LISTESI = ["BTC", "ETH"]

def get_kripto_data():
    """doviz.com/kripto-paralar'dan BTC ve ETH verilerini çeker."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get("https://www.doviz.com/kripto-paralar", headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = {}
        rows = soup.find_all("tr")
        
        for row in rows:
            try:
                link = row.find("a")
                if not link:
                    continue
                    
                details = row.find("div", class_="currency-details")
                if not details:
                    continue
                    
                kod_div = details.find("div")
                if not kod_div:
                    continue
                    
                kod = kod_div.get_text(strip=True)
                
                if kod in KRIPTO_LISTESI:
                    cells = row.find_all("td")
                    if len(cells) >= 6:
                        # İkinci td: USD fiyat (örn: $87.342)
                        fiyat_usd = cells[1].get_text(strip=True)
                        # Altıncı td: Değişim (örn: %-0,80)
                        degisim = cells[5].get_text(strip=True)
                        
                        results[kod] = {
                            "fiyat_usd": fiyat_usd,
                            "degisim": degisim
                        }
            except Exception as e:
                print(f"Kripto satır parse hatası: {e}")
                continue
        
        return results
    except Exception as e:
        print(f"Kripto scraping hatası: {e}")
        return {}

def format_kripto_message(data):
    if not data:
        return "❌ Kripto verisi alınamadı."
    
    message = "₿ Kripto Paralar\n"
    
    emojiler = {"BTC": "🟠", "ETH": "🔷"}
    
    for kod in KRIPTO_LISTESI:
        if kod in data:
            info = data[kod]
            emoji = emojiler.get(kod, "🪙")
            message += f"\n{emoji} {kod}\n"
            message += f"  Fiyat: {info['fiyat_usd']}\n"
            message += f"  Değişim: {info['degisim']}\n"
    
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım mesajı gösterir."""
    try:
        help_msg = (
            "🤖 Finans Botu\n\n"
            "/au - Altın fiyatları\n"
            "/para - USD/EUR\n"
            "/borsa - BIST 100/30\n"
            "/kripto - BTC/ETH\n"
            "/all - Tüm veriler\n"
            "/duzenle - Portföy gir\n"
            "/kasa - Portföy değeri\n\n"
            "💡Furkan ÖZTÜRK sunar... 🚀"
        )
        if update.message is not None:
            await update.message.reply_text(help_msg)
    except Exception as e:
        print(f"Start hatası: {e}")

async def duzenle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı portföy verilerini kaydeder."""
    try:
        if update.message is None or update.message.from_user is None:
            return
        
        user_id = str(update.message.from_user.id)
        
        if not context.args:
            await update.message.reply_text(
                "📝 Portföy Düzenleme\n\n"
                "/duzenle enpara_gr, ziraat_gr, ata, ceyrek, borsa, kripto, diger\n\n"
                "Örnek: /duzenle 30,35,2,3,50000,1000,25000"
            )
            return
        
        raw = " ".join(context.args).strip()
        parcalar = raw.split(",")
        
        if len(parcalar) != 7:
            await update.message.reply_text("❌ 7 veri girin! Örnek: /duzenle 30,35,2,3,50000,1000,25000")
            return
        
        try:
            veriler = {
                "enpara_gr": float(parcalar[0].strip()),
                "ziraat_gr": float(parcalar[1].strip()),
                "ata": float(parcalar[2].strip()),
                "ceyrek": float(parcalar[3].strip()),
                "borsa": float(parcalar[4].strip()),
                "kripto": float(parcalar[5].strip()),
                "diger": float(parcalar[6].strip())
            }
        except ValueError:
            await update.message.reply_text("❌ Sayısal değerler giriniz!")
            return
        
        tum_veriler = load_user_data()
        tum_veriler[user_id] = veriler
        
        if save_user_data(tum_veriler):
            await update.message.reply_text(
                f"✅ Kaydedildi!\n"
                f"Enpara: {veriler['enpara_gr']}g | Ziraat: {veriler['ziraat_gr']}g\n"
                f"Ata: {veriler['ata']} | Çeyrek: {veriler['ceyrek']}\n"
                f"Borsa: {veriler['borsa']:,.0f}₺ | Kripto: {veriler['kripto']:,.0f}$ | Diğer: {veriler['diger']:,.0f}₺"
            )
        else:
            await update.message.reply_text("❌ Kaydetme hatası!")
            
    except Exception as e:
        print(f"Düzenle hatası: {e}")

async def kasa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Portföy toplam değerini hesaplar."""
    try:
        if update.message is None or update.message.from_user is None:
            return
        
        user_id = str(update.message.from_user.id)
        tum_veriler = load_user_data()
        
        if user_id not in tum_veriler:
            await update.message.reply_text("❌ Portföy yok! /duzenle ile girin.")
            return
        
        v = tum_veriler[user_id]
        
        # Fiyatları çek
        gram_data = get_gold_data()
        altin_tur = get_altin_turleri_data()
        para_data = get_para_data()
        
        # Hesaplamalar
        ziraat_fiyat = gram_data.get("Ziraat Bankası", {}).get("alis", 0)
        enpara_fiyat = gram_data.get("Enpara", {}).get("alis", 0)
        
        ata_fiyat = altin_tur.get("Ata Altın", {}).get("alis", 0)
        ceyrek_fiyat = altin_tur.get("Çeyrek Altın", {}).get("alis", 0)
        gram_has_fiyat = altin_tur.get("Gram Has Altın", {}).get("alis", 0)
        usd = para_data.get("USD", {}).get("alis", 0)
        
        # Toplamlar
        t_enpara = v["enpara_gr"] * enpara_fiyat
        t_ziraat = v["ziraat_gr"] * ziraat_fiyat
        t_ata = v["ata"] * ata_fiyat
        t_ceyrek = v["ceyrek"] * ceyrek_fiyat
        t_borsa = v["borsa"]
        t_kripto = v["kripto"] * usd
        t_diger = v["diger"]
        toplam = t_enpara + t_ziraat + t_ata + t_ceyrek + t_borsa + t_kripto + t_diger
        
        # Gram Has Altın cinsinden toplam değer
        toplam_gram = toplam / gram_has_fiyat if gram_has_fiyat > 0 else 0
        
        # Zekat kontrolü (80.18 gram nisab)
        ZEKAT_NISAB = 80.18
        zekat_durumu = "Zekâta tâbiisiniz 😎" if toplam_gram > ZEKAT_NISAB else "Nisab miktarına ulaşılmadı."
        
        msg = (
            f"💰 KASA\n\n"
            f"Enpara ({v['enpara_gr']}g): {t_enpara:,.0f}₺\n"
            f"Ziraat ({v['ziraat_gr']}g): {t_ziraat:,.0f}₺\n"
            f"Ata ({v['ata']:.0f}): {t_ata:,.0f}₺\n"
            f"Çeyrek ({v['ceyrek']:.0f}): {t_ceyrek:,.0f}₺\n"
            f"Borsa: {t_borsa:,.0f}₺\n"
            f"Kripto ({v['kripto']:.0f}$): {t_kripto:,.0f}₺\n"
            f"Diğer: {t_diger:,.0f}₺\n\n"
            f"🏆 TOPLAM: {toplam:,.0f}₺\n\n"
            f"⚖️ Altın Karşılığı (gr) : {toplam_gram:,.2f}g\n\n"
            f"{zekat_durumu}"
        )
        
        await update.message.reply_text(msg)
        
    except Exception as e:
        print(f"Kasa hatası: {e}")

async def au(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm altın fiyatlarını gösterir (gram altın kaynakları + altın türleri)."""
    try:
        # Gram altın kaynakları (Kapalıçarşı, Enpara, Ziraat)
        gram_data = get_gold_data()
        
        # Altın türleri (Gram Has, Çeyrek, Yarım, Ata)
        tur_data = get_altin_turleri_data()
        
        # Tek mesaj olarak birleştir
        message = "📊 Altın Fiyatları\n"
        
        # Gram altın kaynakları
        for kaynak in KAYNAKLAR.keys():
            if kaynak in gram_data:
                info = gram_data[kaynak]
                emoji = KAYNAKLAR[kaynak]
                message += f"\n{emoji} {kaynak}\n"
                message += f"Alış: {info['alis']:.2f} TL\n"
                message += f"Satış: {info['satis']:.2f} TL\n"
                message += f"Makas: %{info['makas_yuzde']:.2f} | {info['makas_tl']:.2f} TL\n"
        
        # Altın türleri
        for isim in ALTIN_TURLERI.keys():
            if isim in tur_data:
                info = tur_data[isim]
                message += f"\n {isim}\n"
                message += f"  Alış: {info['alis']:,.2f} TL\n"
                message += f"  Satış: {info['satis']:,.2f} TL\n"
                message += f"  Makas: %{info['makas_yuzde']:.2f} | {info['makas_tl']:,.2f} TL\n"
        
        if update.message is not None:
            await update.message.reply_text(message)
        else:
            print("Mesaj nesnesi bulunamadı.")
    except Exception as e:
        print(f"Au komutu hatası: {e}")

async def para(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """USD ve EUR döviz kurlarını gösterir."""
    try:
        data = get_para_data()
        message = format_para_message(data)
        if update.message is not None:
            await update.message.reply_text(message)
        else:
            print("Mesaj nesnesi bulunamadı.")
    except Exception as e:
        print(f"Para komutu hatası: {e}")

async def borsa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """BIST 100 ve BIST 30 verilerini gösterir."""
    try:
        data = get_borsa_data()
        message = format_borsa_message(data)
        if update.message is not None:
            await update.message.reply_text(message)
        else:
            print("Mesaj nesnesi bulunamadı.")
    except Exception as e:
        print(f"Borsa komutu hatası: {e}")

async def kripto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """BTC ve ETH kripto verilerini gösterir."""
    try:
        data = get_kripto_data()
        message = format_kripto_message(data)
        if update.message is not None:
            await update.message.reply_text(message)
        else:
            print("Mesaj nesnesi bulunamadı.")
    except Exception as e:
        print(f"Kripto komutu hatası: {e}")

async def all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm finansal verileri tek tek mesaj olarak gönderir."""
    try:
        if update.message is None:
            return
        
        # 1. Altın verileri
        gram_data = get_gold_data()
        tur_data = get_altin_turleri_data()
        
        au_message = "📊 Altın Fiyatları\n"
        for kaynak in KAYNAKLAR.keys():
            if kaynak in gram_data:
                info = gram_data[kaynak]
                emoji = KAYNAKLAR[kaynak]
                au_message += f"\n{emoji} {kaynak}\n"
                au_message += f"Alış: {info['alis']:.2f} TL\n"
                au_message += f"Satış: {info['satis']:.2f} TL\n"
                au_message += f"Makas: %{info['makas_yuzde']:.2f} | {info['makas_tl']:.2f} TL\n"
        for isim in ALTIN_TURLERI.keys():
            if isim in tur_data:
                info = tur_data[isim]
                au_message += f"\n {isim}\n"
                au_message += f"  Alış: {info['alis']:,.2f} TL\n"
                au_message += f"  Satış: {info['satis']:,.2f} TL\n"
                au_message += f"  Makas: %{info['makas_yuzde']:.2f} | {info['makas_tl']:,.2f} TL\n"
        await update.message.reply_text(au_message)
        
        # 2. Döviz verileri
        para_data = get_para_data()
        para_message = format_para_message(para_data)
        await update.message.reply_text(para_message)
        
        # 3. Borsa verileri
        borsa_data = get_borsa_data()
        borsa_message = format_borsa_message(borsa_data)
        await update.message.reply_text(borsa_message)
        
        # 4. Kripto verileri
        kripto_data = get_kripto_data()
        kripto_message = format_kripto_message(kripto_data)
        await update.message.reply_text(kripto_message)
        
    except Exception as e:
        print(f"All komutu hatası: {e}")

def main():
    """
    Ana fonksiyon - Botu başlatır ve 7/24 çalışmasını sağlar.
    Koyeb'de otomatik yeniden başlatma ile çalışır.
    """
    logger.info("🚀 Finans Botu başlatılıyor...")
    logger.info(f"📁 Veri dosyası: {DATA_FILE}")
    
    try:
        # Application oluştur
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handler'ları ekle
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("au", au))
        application.add_handler(CommandHandler("para", para))
        application.add_handler(CommandHandler("borsa", borsa))
        application.add_handler(CommandHandler("kripto", kripto))
        application.add_handler(CommandHandler("all", all_data))
        application.add_handler(CommandHandler("duzenle", duzenle))
        application.add_handler(CommandHandler("kasa", kasa))
        
        logger.info("✅ Bot başarıyla başlatıldı!")
        logger.info("📡 Polling modunda çalışıyor...")
        
        # Polling başlat (7/24 çalışır)
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot kullanıcı tarafından durduruldu.")
    except Exception as e:
        logger.error(f"❌ Bot hatası: {e}")
        # Koyeb'in otomatik yeniden başlatması için exit code 1
        sys.exit(1)

if __name__ == "__main__":
    main()