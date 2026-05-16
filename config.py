# ==========================================
#   إعدادات البوت - config.py
# ==========================================

import os

# ---- إعدادات البوت الأساسية ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "8885723867:AAGjNuEut3QooCwCvwb8em7cyFGMAhH0F3Q")

# ---- معرفات الأدمن ----
ADMIN_IDS = [
    6721652980,   # ضع معرف الأدمن هنا
]

# ---- إعدادات TON ----
# محفظة البوت الرئيسية (تستقبل النجوم وترسل منها TON)
TON_WALLET_ADDRESS = os.getenv("TON_WALLET_ADDRESS", "UQAC6yaR6e4MLGWCBuRW2sLrvSgGPkdKYUnBtyPjrVQNzpdH")
# ✅ محفظة صاحب البوت لاستلام العمولة تلقائياً
OWNER_WALLET_ADDRESS = os.getenv("OWNER_WALLET_ADDRESS", "UQApKGqh6CnfHwmEfJMaUSzp0FsRR7y-nXk_0TDp2xV2TueD")

# مفتاح Toncenter API
TON_API_KEY = os.getenv("TON_API_KEY", "43e16bbb40b73f4ef9a7273a6cd6943e2a7e49413d6215521ca5f0e58fd4f5e4")

# الشبكة: mainnet أو testnet
TON_NETWORK = os.getenv("TON_NETWORK", "mainnet")

# ✅ العبارة السرية لمحفظة البوت (لازمة للإرسال التلقائي)
# 24 كلمة مفصولة بمسافات - احتفظ بها سرية تماماً!
# TON_MNEMONIC="word1 word2 word3 ... word24"
TON_MNEMONIC = os.getenv("TON_MNEMONIC", "lyrics mouse resist brother inflict label spray valve uncover animal avocado mass device sad vast car rely approve improve citizen pattern swamp shoot release")
# ---- أسعار التحويل ----
# سعر النجمة الواحدة بالـ TON
STAR_TO_TON_RATE = 0.0050       # 1 نجمة = 0.050 TON (غيّر حسب السعر الحالي)
TON_TO_STAR_RATE =  172         # 1 TON = 172 نجمة  (غيّر حسب السعر الحالي)

# ---- العمولات ----
COMMISSION_PERCENT = 3         # نسبة عمولة البوت (%)
MIN_STARS_SELL = 10            # الحد الأدنى لبيع النجوم
MAX_STARS_SELL = 10000         # الحد الأقصى لبيع النجوم
MIN_TON_BUY = 0.1             # الحد الأدنى لشراء TON

# ---- إعدادات الدفع بالنجوم ----
STARS_PROVIDER_TOKEN = "8885723867:AAGjNuEut3QooCwCvwb8em7cyFGMAhH0F3Q"      # مزود دفع النجوم (Telegram Stars) - يُترك فارغاً

# ---- قاعدة البيانات ----
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

# ---- رسائل البوت ----
BOT_USERNAME    = os.getenv("BOT_USERNAME",    "@L_P_50")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@L_P_50")
CHANNEL_LINK    = os.getenv("CHANNEL_LINK",    "https://t.me/L_P_50")

# ---- إعدادات Fragment API (لبيع النجوم) ----
FRAGMENT_API_URL = "https://fragment.com/api"
FRAGMENT_HASH    = os.getenv("FRAGMENT_HASH", "8c0901c864d8d21ee601fab8204fc74d8c0901d28c090cbc18fb81a81fa24bd24d8aa")

# ---- روابط مفيدة ----
TON_EXPLORER = "https://tonscan.org/address/"
