# ==========================================
#   معالج الدفع والتحويل - payments.py
#   النجوم → TON تلقائياً مع خصم العمولة
# ==========================================

import aiohttp
import asyncio
import logging
from config import (
    TON_API_KEY, TON_WALLET_ADDRESS, TON_NETWORK,
    STAR_TO_TON_RATE, TON_TO_STAR_RATE, COMMISSION_PERCENT,
    OWNER_WALLET_ADDRESS  # محفظة صاحب البوت لاستلام العمولة
)
import database as db

logger = logging.getLogger(__name__)

TONCENTER_BASE = (
    "https://toncenter.com/api/v2"
    if TON_NETWORK == "mainnet"
    else "https://testnet.toncenter.com/api/v2"
)


# ==========================================
#  حساب التحويلات
# ==========================================

def calc_stars_to_ton(stars: int, commission_override: int = None) -> dict:
    """
    حساب قيمة النجوم بالـ TON مع العمولة.
    commission_override: تجاوز نسبة العمولة من قاعدة البيانات
    """
    # جلب العمولة من قاعدة البيانات (أو الافتراضية)
    commission = commission_override
    if commission is None:
        try:
            commission = int(db.get_setting("commission_percent", str(COMMISSION_PERCENT)))
        except Exception:
            commission = COMMISSION_PERCENT

    rate = float(db.get_setting("star_to_ton_rate", str(STAR_TO_TON_RATE)))
    gross_ton   = stars * rate
    commission_ton = gross_ton * (commission / 100)
    net_ton     = round(gross_ton - commission_ton, 6)

    return {
        "stars":          stars,
        "rate":           rate,
        "gross_ton":      round(gross_ton, 6),
        "commission":     round(commission_ton, 6),
        "commission_pct": commission,
        "net_ton":        net_ton,
    }


def calc_ton_to_stars(ton: float) -> dict:
    """حساب عدد النجوم مقابل TON مع العمولة"""
    try:
        ton_rate   = int(db.get_setting("ton_to_star_rate",   str(TON_TO_STAR_RATE)))
        commission = int(db.get_setting("commission_percent", str(COMMISSION_PERCENT)))
    except Exception:
        ton_rate   = TON_TO_STAR_RATE
        commission = COMMISSION_PERCENT

    gross_stars = int(ton * ton_rate)
    commission_ton  = ton * (commission / 100)
    net_ton     = round(ton - commission_ton, 6)
    stars_after = int(net_ton * ton_rate)
    return {
        "ton":                    ton,
        "gross_stars":            gross_stars,
        "stars_after_commission": stars_after,
        "commission_ton":         round(commission_ton, 6),
        "rate":                   ton_rate,
    }


def format_ton(amount: float) -> str:
    return f"{amount:.4f}"


# ==========================================
#  الإرسال التلقائي للـ TON (القلب الرئيسي)
# ==========================================

async def process_stars_payment(order_id: int, stars_paid: int, bot=None) -> dict:
    """
    المعالج الكامل بعد استلام النجوم:
    1. حساب التوزيع (عمولة صاحب البوت + صافي للمستخدم)
    2. إرسال صافي TON لمحفظة المستخدم تلقائياً
    3. (اختياري) تسجيل العمولة في السجلات

    الإرجاع: dict يحتوي على نتيجة العملية
    """
    from ton_wallet import auto_send_ton

    order = db.get_sell_order(order_id)
    if not order:
        return {"success": False, "error": f"الطلب #{order_id} غير موجود"}

    if order["status"] not in ("pending", "stars_received"):
        return {
            "success": False,
            "error": f"الطلب #{order_id} في حالة غير قابلة للمعالجة: {order['status']}"
        }

    user_wallet = order["ton_wallet"]
    net_ton     = float(order["net_ton"])
    commission  = float(order["commission"])

    if not user_wallet:
        db.update_sell_order_status(order_id, "error_no_wallet")
        return {"success": False, "error": "لا توجد محفظة للمستخدم"}

    # ── الخطوة 1: تحديث الحالة إلى "قيد المعالجة"
    db.update_sell_order_status(order_id, "processing")
    logger.info(f"[PAY] معالجة الطلب #{order_id} | {stars_paid}⭐ → {net_ton} TON → {user_wallet}")

    # ── الخطوة 2: إرسال صافي TON للمستخدم
    memo = f"Stars-Order-{order_id}"
    result = await auto_send_ton(
        to_address = user_wallet,
        amount_ton = net_ton,
        memo       = memo
    )

    if result["success"]:
        # ── الخطوة 3: تحديث الحالة إلى "مكتمل"
        db.update_sell_order_status(order_id, "completed", tx_hash=result.get("tx_hash", "auto"))
        db.log_action(order["user_id"], "auto_ton_sent",
                      f"order={order_id} net_ton={net_ton} tx={result.get('tx_hash','')}")

        # ── الخطوة 4: تسجيل العمولة
        db.log_action(0, "commission_earned",
                      f"order={order_id} commission={commission} ton owner_wallet={OWNER_WALLET_ADDRESS}")

        logger.info(f"[PAY] ✅ أُرسل {net_ton} TON → {user_wallet} | عمولة: {commission} TON")
        return {
            "success":    True,
            "tx_hash":    result.get("tx_hash", ""),
            "net_ton":    net_ton,
            "commission": commission,
            "to_wallet":  user_wallet
        }

    elif result.get("manual_required"):
        # ── الإرسال التلقائي غير مضبوط - البوت يُنبّه الأدمن
        db.update_sell_order_status(order_id, "stars_received")
        logger.warning(f"[PAY] ⚠️ الإرسال اليدوي مطلوب للطلب #{order_id}")
        return {
            "success":        False,
            "manual_required": True,
            "error":          result["error"],
            "order_id":       order_id,
            "net_ton":        net_ton,
            "to_wallet":      user_wallet
        }
    else:
        # ── خطأ في الإرسال
        db.update_sell_order_status(order_id, "error_send_failed")
        db.log_action(order["user_id"], "auto_ton_failed",
                      f"order={order_id} error={result.get('error','')}")
        logger.error(f"[PAY] ❌ فشل إرسال TON للطلب #{order_id}: {result.get('error')}")
        return {
            "success": False,
            "error":   result.get("error", "خطأ في إرسال TON"),
            "order_id": order_id
        }


# ==========================================
#  TON Blockchain API
# ==========================================

async def get_wallet_balance(address: str) -> float:
    """الحصول على رصيد محفظة TON"""
    try:
        url    = f"{TONCENTER_BASE}/getAddressBalance"
        params = {"address": address, "api_key": TON_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if data.get("ok"):
                    nano = int(data["result"])
                    return nano / 1e9
    except Exception as e:
        logger.warning(f"[TON] خطأ في الحصول على الرصيد: {e}")
    return 0.0


async def verify_ton_payment(wallet: str, amount: float, memo: str) -> dict:
    """التحقق من استلام دفعة TON"""
    try:
        url    = f"{TONCENTER_BASE}/getTransactions"
        params = {
            "address": TON_WALLET_ADDRESS,
            "limit":   20,
            "api_key": TON_API_KEY,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    return {"verified": False, "error": "API error"}
                txs = data.get("result", [])
                for tx in txs:
                    in_msg  = tx.get("in_msg", {})
                    src     = in_msg.get("source", "")
                    value   = int(in_msg.get("value", 0)) / 1e9
                    comment = ""
                    if in_msg.get("msg_data", {}).get("@type") == "msg.dataText":
                        comment = in_msg["msg_data"].get("text", "")
                    if (abs(value - amount) < 0.01) and (memo in comment or comment in memo):
                        return {
                            "verified": True,
                            "tx_hash":  tx.get("transaction_id", {}).get("hash", ""),
                            "from":     src,
                            "amount":   value,
                        }
        return {"verified": False, "error": "لم يتم العثور على معاملة مطابقة"}
    except Exception as e:
        return {"verified": False, "error": str(e)}


async def validate_ton_address(address: str) -> bool:
    """التحقق من صحة عنوان TON"""
    try:
        url    = f"{TONCENTER_BASE}/detectAddress"
        params = {"address": address, "api_key": TON_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                return data.get("ok", False)
    except Exception:
        return False


# ==========================================
#  نجوم تيليغرام (Telegram Stars)
# ==========================================

def create_stars_invoice(title: str, description: str, stars_amount: int, payload: str) -> dict:
    """إنشاء فاتورة لاستقبال نجوم من المستخدم"""
    return {
        "title":       title,
        "description": description,
        "payload":     payload,
        "currency":    "XTR",  # XTR = Telegram Stars
        "prices":      [{"label": title, "amount": stars_amount}],
    }


def verify_stars_payment(pre_checkout_query) -> bool:
    """التحقق من صحة طلب الدفع بالنجوم"""
    return True


# ==========================================
#  مساعدات عامة
# ==========================================

def generate_payment_memo(order_id: int, user_id: int) -> str:
    """توليد memo فريد لكل معاملة"""
    return f"ORDER-{order_id}-USER-{user_id}"


def parse_payment_memo(memo: str) -> dict:
    """تحليل الـ memo لاستخراج order_id و user_id"""
    try:
        parts    = memo.split("-")
        order_id = int(parts[1])
        user_id  = int(parts[3])
        return {"order_id": order_id, "user_id": user_id}
    except Exception:
        return {}
