# ==========================================
#   إرسال TON تلقائياً - ton_wallet.py
#   يستخدم tonsdk + toncenter API
# ==========================================

import aiohttp
import asyncio
import base64
import os
import json
import time
import logging
from config import (
    TON_API_KEY, TON_WALLET_ADDRESS, TON_NETWORK,
    COMMISSION_PERCENT
)

logger = logging.getLogger(__name__)

TONCENTER_BASE = (
    "https://toncenter.com/api/v2"
    if TON_NETWORK == "mainnet"
    else "https://testnet.toncenter.com/api/v2"
)

# ==========================================
#  إرسال TON عبر tonsdk (إذا توفر المفتاح الخاص)
# ==========================================

async def auto_send_ton(to_address: str, amount_ton: float, memo: str = "") -> dict:
    """
    إرسال TON تلقائياً من محفظة البوت إلى عنوان المستخدم.
    يتطلب: TON_MNEMONIC أو TON_PRIVATE_KEY في متغيرات البيئة.
    """
    mnemonic = os.getenv("TON_MNEMONIC", "")
    
    if not mnemonic:
        logger.warning("[TON SEND] لا يوجد TON_MNEMONIC - الإرسال اليدوي مطلوب")
        return {
            "success": False,
            "error": "TON_MNEMONIC غير مضبوط في ملف .env",
            "manual_required": True,
            "to": to_address,
            "amount": amount_ton,
            "memo": memo
        }

    try:
        # محاولة استخدام tonsdk للإرسال التلقائي
        from tonsdk.contract.wallet import WalletVersionEnum, Wallets
        from tonsdk.utils import to_nano
        import tonsdk.utils

        words = mnemonic.strip().split()
        mnemonics, pub_key, priv_key, wallet = Wallets.from_mnemonics(
            words, WalletVersionEnum.v4r2, workchain=0
        )

        # الحصول على seqno
        wallet_address = wallet.address.to_string(True, True, True)
        seqno = await _get_seqno(wallet_address)

        # بناء معاملة الإرسال
        nano_amount = to_nano(amount_ton, "ton")
        payload_bytes = _encode_comment(memo) if memo else b""

        transfer = wallet.create_transfer_message(
            to_addr=to_address,
            amount=nano_amount,
            seqno=seqno,
            payload=payload_bytes,
        )

        boc = transfer["message"].to_boc(False)
        boc_b64 = base64.b64encode(boc).decode()

        # إرسال المعاملة
        result = await _broadcast_boc(boc_b64)

        if result.get("ok"):
            logger.info(f"[TON SEND] ✅ أُرسل {amount_ton} TON → {to_address}")
            return {
                "success": True,
                "tx_hash": result.get("result", ""),
                "to": to_address,
                "amount": amount_ton,
                "memo": memo
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "خطأ غير معروف"),
                "to": to_address,
                "amount": amount_ton
            }

    except ImportError:
        logger.error("[TON SEND] tonsdk غير مثبّت - جرّب: pip install tonsdk")
        return {
            "success": False,
            "error": "مكتبة tonsdk غير مثبّتة. شغّل: pip install tonsdk",
            "manual_required": True,
            "to": to_address,
            "amount": amount_ton
        }
    except Exception as e:
        logger.error(f"[TON SEND] خطأ: {e}")
        return {
            "success": False,
            "error": str(e),
            "to": to_address,
            "amount": amount_ton
        }


async def _get_seqno(wallet_address: str) -> int:
    """الحصول على seqno من blockchain"""
    try:
        url = f"{TONCENTER_BASE}/runGetMethod"
        payload = {
            "address": wallet_address,
            "method": "seqno",
            "stack": []
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                params={"api_key": TON_API_KEY},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    stack = data["result"].get("stack", [])
                    if stack:
                        return int(stack[0][1], 16)
    except Exception as e:
        logger.warning(f"[SEQNO] خطأ: {e}")
    return 0


async def _broadcast_boc(boc_b64: str) -> dict:
    """بث معاملة TON"""
    try:
        url = f"{TONCENTER_BASE}/sendBoc"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"boc": boc_b64},
                params={"api_key": TON_API_KEY},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                return await resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _encode_comment(text: str) -> bytes:
    """تشفير تعليق المعاملة"""
    try:
        from tonsdk.boc import Cell
        cell = Cell()
        cell.bits.write_uint(0, 32)
        cell.bits.write_bytes(text.encode("utf-8"))
        return cell.to_boc(False)
    except Exception:
        return text.encode("utf-8")


# ==========================================
#  حساب توزيع العمولة
# ==========================================

def calculate_distribution(gross_ton: float, commission_percent: int) -> dict:
    """
    حساب كيفية توزيع TON المستلم:
    - commission_ton: حصة البوت (صاحب البوت)
    - user_ton: حصة المستخدم
    """
    commission_ton = round(gross_ton * (commission_percent / 100), 6)
    user_ton = round(gross_ton - commission_ton, 6)
    return {
        "gross_ton": gross_ton,
        "commission_ton": commission_ton,
        "user_ton": user_ton,
        "commission_percent": commission_percent
    }


async def get_bot_wallet_balance() -> float:
    """الحصول على رصيد محفظة البوت"""
    try:
        url = f"{TONCENTER_BASE}/getAddressBalance"
        params = {"address": TON_WALLET_ADDRESS, "api_key": TON_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if data.get("ok"):
                    nano = int(data["result"])
                    return nano / 1e9
    except Exception as e:
        logger.warning(f"[BALANCE] خطأ: {e}")
    return 0.0
