# ==========================================
#   البوت الرئيسي - bot.py
#   بوت تيليغرام لتحويل النجوم ↔ TON
# ==========================================

import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, SuccessfulPayment, ReplyKeyboardMarkup,
    KeyboardButton, ReplyKeyboardRemove
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
import payments as pay
from config import (
    BOT_TOKEN, ADMIN_IDS, MIN_STARS_SELL, MAX_STARS_SELL,
    MIN_TON_BUY, TON_WALLET_ADDRESS, SUPPORT_USERNAME,
    CHANNEL_LINK, BOT_USERNAME, COMMISSION_PERCENT,
    STAR_TO_TON_RATE, TON_TO_STAR_RATE,
    OWNER_WALLET_ADDRESS
)
from admin import admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

main_router = Router()


# ==========================================
#  حالات المحادثة (FSM)
# ==========================================

class SellStars(StatesGroup):
    waiting_stars_amount = State()
    waiting_ton_wallet   = State()
    confirm_sell         = State()


class BuyStars(StatesGroup):
    waiting_stars_amount = State()
    confirm_buy          = State()
    waiting_payment      = State()


class TransferTON(StatesGroup):
    waiting_recipient    = State()
    waiting_amount       = State()
    waiting_note         = State()
    confirm_transfer     = State()


class SetWallet(StatesGroup):
    waiting_wallet = State()


# ==========================================
#  لوحة المفاتيح الرئيسية
# ==========================================

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⭐ بيع نجوم   ←  TON 💎"),
             KeyboardButton(text="💎 شراء نجوم  ←  TON ⭐")],
            [KeyboardButton(text="📊 أسعار الصرف"),
             KeyboardButton(text="💼 محفظتي")],
            [KeyboardButton(text="📋 طلباتي"),
             KeyboardButton(text="💸 تحويل TON")],
            [KeyboardButton(text="👜 ربط محفظة TON"),
             KeyboardButton(text="🆘 الدعم")],
        ],
        resize_keyboard=True
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ إلغاء")]],
        resize_keyboard=True
    )


def confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأكيد", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data="confirm_no"),
        ]
    ])


# ==========================================
#  /start
# ==========================================

@main_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    if user.get("is_banned"):
        await message.answer("🚫 تم حظرك من استخدام البوت. تواصل مع الدعم.")
        return

    text = (
        f"👋 أهلاً <b>{message.from_user.first_name}</b>!\n\n"
        "🤖 <b>بوت تحويل النجوم والـ TON</b>\n\n"
        "🌟 يمكنك من خلال هذا البوت:\n"
        "  ⭐ <b>بيع نجومك</b> مقابل TON في محفظتك\n"
        "  💎 <b>شراء نجوم</b> بـ TON\n"
        "  💸 <b>تحويل TON</b> لأي شخص\n\n"
        "اختر من القائمة أدناه 👇"
    )
    await message.answer(text, reply_markup=main_keyboard(), parse_mode="HTML")


# ==========================================
#  /help و الدعم
# ==========================================

@main_router.message(Command("help"))
@main_router.message(F.text == "🆘 الدعم")
async def cmd_help(message: Message):
    text = (
        "🆘 <b>المساعدة والدعم</b>\n\n"
        f"📞 للتواصل مع الدعم: {SUPPORT_USERNAME}\n"
        f"📢 قناتنا: {CHANNEL_LINK}\n\n"
        "❓ <b>الأسئلة الشائعة:</b>\n\n"
        "🔹 <b>كيف أبيع نجومي؟</b>\n"
        "   اضغط 'بيع نجوم' وأدخل الكمية ومحفظتك\n\n"
        "🔹 <b>كيف أشتري نجوماً؟</b>\n"
        "   اضغط 'شراء نجوم' وادفع بـ TON\n\n"
        "🔹 <b>متى يصل الـ TON؟</b>\n"
        "   خلال 15-60 دقيقة بعد التحقق\n\n"
        "🔹 <b>ما هي العمولة؟</b>\n"
        f"   {COMMISSION_PERCENT}% من قيمة كل عملية\n\n"
        "🔹 <b>ما الحد الأدنى للبيع؟</b>\n"
        f"   {MIN_STARS_SELL} نجمة كحد أدنى"
    )
    await message.answer(text, parse_mode="HTML")


# ==========================================
#  عرض أسعار الصرف
# ==========================================

@main_router.message(F.text == "📊 أسعار الصرف")
async def show_rates(message: Message):
    # جلب الأسعار من قاعدة البيانات (إذا عدّلها الأدمن) أو الافتراضية
    star_rate  = float(db.get_setting("star_to_ton_rate",  str(STAR_TO_TON_RATE)))
    ton_rate   = int(db.get_setting("ton_to_star_rate",    str(TON_TO_STAR_RATE)))
    commission = int(db.get_setting("commission_percent",  str(COMMISSION_PERCENT)))

    examples = ""
    for stars in [50, 100, 500, 1000]:
        calc     = pay.calc_stars_to_ton(stars)
        examples += f"  ⭐ {stars:>5} نجمة → 💎 <b>{calc['net_ton']:.4f} TON</b>\n"

    text = (
        "📊 <b>أسعار الصرف الحالية</b>\n\n"
        f"⭐ النجمة الواحدة = <b>{star_rate:.4f} TON</b>\n"
        f"💎 الـ TON الواحد = <b>{ton_rate} نجمة</b>\n"
        f"💰 العمولة = <b>{commission}%</b>\n\n"
        "📋 <b>أمثلة (بعد العمولة):</b>\n"
        f"{examples}\n"
        "⚡ الأسعار قابلة للتغيير في أي وقت."
    )
    await message.answer(text, parse_mode="HTML")


# ==========================================
#  عرض المحفظة
# ==========================================

@main_router.message(F.text == "💼 محفظتي")
async def show_wallet(message: Message):
    user = db.get_or_create_user(message.from_user.id)
    wallet = user.get("ton_wallet") or "❌ لم تقم بربط محفظة بعد"
    text = (
        "💼 <b>محفظتي</b>\n\n"
        f"👤 الاسم: <b>{message.from_user.full_name}</b>\n"
        f"🆔 المعرف: <code>{message.from_user.id}</code>\n\n"
        f"👜 محفظة TON: <code>{wallet}</code>\n\n"
        "لتغيير أو ربط محفظة TON، اضغط:\n👜 ربط محفظة TON"
    )
    await message.answer(text, parse_mode="HTML")


# ==========================================
#  ربط محفظة TON
# ==========================================

@main_router.message(F.text == "👜 ربط محفظة TON")
async def link_wallet_start(message: Message, state: FSMContext):
    await state.set_state(SetWallet.waiting_wallet)
    await message.answer(
        "👜 <b>أرسل عنوان محفظة TON الخاصة بك:</b>\n\n"
        "مثال:\n<code>EQD2NmD_lH5f5u1Kj3KfGyTvhZSX0Eg6qp2a5IQUKXxOG3So</code>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@main_router.message(SetWallet.waiting_wallet)
async def link_wallet_receive(message: Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer("❌ تم الإلغاء.", reply_markup=main_keyboard())
        return

    wallet = message.text.strip()
    valid  = await pay.validate_ton_address(wallet)
    if not valid and not wallet.startswith("EQ") and not wallet.startswith("UQ"):
        await message.answer(
            "❌ عنوان المحفظة غير صالح. تأكد من العنوان وحاول مجدداً.\n"
            "يبدأ العنوان بـ EQ أو UQ"
        )
        return

    db.update_user_wallet(message.from_user.id, wallet)
    await state.clear()
    await message.answer(
        f"✅ <b>تم ربط محفظتك بنجاح!</b>\n\n"
        f"👜 العنوان: <code>{wallet}</code>",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )
    db.log_action(message.from_user.id, "link_wallet", wallet)


# ==========================================
#  بيع النجوم مقابل TON
# ==========================================

@main_router.message(F.text == "⭐ بيع نجوم   ←  TON 💎")
async def sell_stars_start(message: Message, state: FSMContext):
    user = db.get_or_create_user(message.from_user.id)
    if user.get("is_banned"):
        await message.answer("🚫 تم حظرك من استخدام البوت.")
        return

    star_rate  = float(db.get_setting("star_to_ton_rate",  str(STAR_TO_TON_RATE)))
    commission = int(db.get_setting("commission_percent",  str(COMMISSION_PERCENT)))

    await state.set_state(SellStars.waiting_stars_amount)
    await message.answer(
        "⭐ <b>بيع النجوم مقابل TON</b>\n\n"
        f"💱 السعر: <b>1 نجمة = {star_rate:.4f} TON</b>\n"
        f"💰 العمولة: <b>{commission}%</b>\n\n"
        f"أدخل عدد النجوم التي تريد بيعها:\n"
        f"(الحد الأدنى: {MIN_STARS_SELL} | الحد الأقصى: {MAX_STARS_SELL})",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@main_router.message(SellStars.waiting_stars_amount)
async def sell_stars_amount(message: Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer("❌ تم الإلغاء.", reply_markup=main_keyboard())
        return
    try:
        stars = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً.")
        return

    if stars < MIN_STARS_SELL:
        await message.answer(f"❌ الحد الأدنى هو {MIN_STARS_SELL} نجمة.")
        return
    if stars > MAX_STARS_SELL:
        await message.answer(f"❌ الحد الأقصى هو {MAX_STARS_SELL} نجمة.")
        return

    calc = pay.calc_stars_to_ton(stars)
    await state.update_data(stars=stars, calc=calc)

    user = db.get_user(message.from_user.id)
    if user and user.get("ton_wallet"):
        # لديه محفظة محفوظة - اعرض خياراً للاستخدامها
        await state.set_state(SellStars.waiting_ton_wallet)
        await message.answer(
            f"💰 <b>ملخص البيع</b>\n\n"
            f"⭐ النجوم: <b>{stars}</b>\n"
            f"💎 TON الإجمالي: <b>{calc['gross_ton']:.4f}</b>\n"
            f"💸 العمولة: <b>{calc['commission']:.4f}</b>\n"
            f"✅ TON الصافي: <b>{calc['net_ton']:.4f}</b>\n\n"
            f"📬 محفظتك المحفوظة:\n<code>{user['ton_wallet']}</code>\n\n"
            "اضغط ✅ لاستخدامها أو أرسل محفظة جديدة:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ استخدام المحفظة المحفوظة",
                                      callback_data="use_saved_wallet")],
                [InlineKeyboardButton(text="📝 إدخال محفظة أخرى",
                                      callback_data="enter_new_wallet")],
                [InlineKeyboardButton(text="❌ إلغاء", callback_data="confirm_no")],
            ]),
            parse_mode="HTML"
        )
    else:
        await state.set_state(SellStars.waiting_ton_wallet)
        await message.answer(
            f"💰 <b>ملخص البيع</b>\n\n"
            f"⭐ النجوم: <b>{stars}</b>\n"
            f"💎 TON الإجمالي: <b>{calc['gross_ton']:.4f}</b>\n"
            f"💸 العمولة: <b>{calc['commission']:.4f}</b>\n"
            f"✅ TON الصافي: <b>{calc['net_ton']:.4f}</b>\n\n"
            "📬 أرسل عنوان محفظة TON لاستلام المبلغ:",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )


@main_router.callback_query(F.data == "use_saved_wallet")
async def use_saved_wallet(call: CallbackQuery, state: FSMContext):
    user = db.get_user(call.from_user.id)
    if not user or not user.get("ton_wallet"):
        await call.answer("❌ لا توجد محفظة محفوظة", show_alert=True)
        return
    await state.update_data(ton_wallet=user["ton_wallet"])
    await state.set_state(SellStars.confirm_sell)
    data = await state.get_data()
    calc = data['calc']
    await call.message.edit_text(
        f"📋 <b>تأكيد طلب البيع</b>\n\n"
        f"⭐ النجوم: <b>{data['stars']}</b>\n"
        f"💎 TON الصافي: <b>{calc['net_ton']:.4f}</b>\n"
        f"📬 المحفظة: <code>{user['ton_wallet']}</code>\n\n"
        "⚠️ بعد التأكيل ستحتاج لإرسال النجوم عبر الدفع بالبوت.\n"
        "هل تريد المتابعة؟",
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


@main_router.callback_query(F.data == "enter_new_wallet")
async def enter_new_wallet(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "📬 أرسل عنوان محفظة TON الجديدة:",
        reply_markup=None
    )


@main_router.message(SellStars.waiting_ton_wallet)
async def sell_stars_wallet(message: Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer("❌ تم الإلغاء.", reply_markup=main_keyboard())
        return

    wallet = message.text.strip()
    if not (wallet.startswith("EQ") or wallet.startswith("UQ")) or len(wallet) < 48:
        await message.answer("❌ عنوان المحفظة غير صالح. تأكد وحاول مجدداً.")
        return

    await state.update_data(ton_wallet=wallet)
    await state.set_state(SellStars.confirm_sell)
    data = await state.get_data()
    calc = data['calc']

    await message.answer(
        f"📋 <b>تأكيد طلب البيع</b>\n\n"
        f"⭐ النجوم: <b>{data['stars']}</b>\n"
        f"💎 TON الصافي: <b>{calc['net_ton']:.4f}</b>\n"
        f"📬 المحفظة: <code>{wallet}</code>\n\n"
        "هل تريد المتابعة؟",
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


@main_router.callback_query(F.data == "confirm_yes", SellStars.confirm_sell)
async def confirm_sell_stars(call: CallbackQuery, state: FSMContext, bot: Bot):
    data   = await state.get_data()
    await state.clear()
    calc   = data['calc']
    wallet = data['ton_wallet']
    stars  = data['stars']

    order_id = db.create_sell_order(
        user_id      = call.from_user.id,
        stars_amount = stars,
        ton_amount   = calc['gross_ton'],
        commission   = calc['commission'],
        net_ton      = calc['net_ton'],
        ton_wallet   = wallet
    )
    db.log_action(call.from_user.id, "sell_order_created", f"order={order_id} stars={stars}")

    # إشعار الأدمن
    for admin_id in ADMIN_IDS:
        try:
            uname = f"@{call.from_user.username}" if call.from_user.username else f"ID:{call.from_user.id}"
            await bot.send_message(
                admin_id,
                f"🔔 <b>طلب بيع جديد #{order_id}</b>\n\n"
                f"👤 المستخدم: {uname}\n"
                f"⭐ النجوم: <b>{stars}</b>\n"
                f"💎 TON الصافي: <b>{calc['net_ton']:.4f}</b>\n"
                f"📬 المحفظة: <code>{wallet}</code>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ اعتماد", callback_data=f"approve_sell_{order_id}"),
                     InlineKeyboardButton(text="❌ رفض",    callback_data=f"reject_sell_{order_id}")]
                ]),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"فشل إشعار الأدمن {admin_id}: {e}")

    await call.message.edit_text(
        f"✅ <b>تم إنشاء طلب البيع #{order_id}</b>\n\n"
        f"⭐ النجوم: <b>{stars}</b>\n"
        f"💎 ستستلم: <b>{calc['net_ton']:.4f} TON</b>\n"
        f"📬 على المحفظة: <code>{wallet}</code>\n\n"
        "📤 <b>الخطوة التالية:</b>\n"
        f"أرسل <b>{stars} نجمة</b> إلى البوت عبر الضغط على الزر أدناه\n\n"
        "⏳ سيتم مراجعة طلبك وإرسال TON خلال 15-60 دقيقة.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"⭐ إرسال {stars} نجمة للبوت",
                callback_data=f"pay_stars_{order_id}_{stars}"
            )],
            [InlineKeyboardButton(text="📋 طلباتي", callback_data="my_orders")],
        ]),
        parse_mode="HTML"
    )


# ==========================================
#  دفع النجوم (Telegram Stars Invoice)
# ==========================================

@main_router.callback_query(F.data.startswith("pay_stars_"))
async def send_stars_invoice(call: CallbackQuery, bot: Bot):
    parts    = call.data.split("_")
    order_id = int(parts[2])
    stars    = int(parts[3])

    try:
        await bot.send_invoice(
            chat_id     = call.from_user.id,
            title       = f"⭐ دفع {stars} نجمة",
            description = f"إرسال {stars} نجمة لإتمام طلب البيع #{order_id}",
            payload     = f"sell_stars_{order_id}",
            provider_token = "",          # فارغ لـ Telegram Stars
            currency    = "XTR",
            prices      = [LabeledPrice(label=f"⭐ {stars} نجمة", amount=stars)],
        )
        await call.answer("📨 تم إرسال فاتورة الدفع بالنجوم!")
    except Exception as e:
        logger.error(f"خطأ في إنشاء الفاتورة: {e}")
        await call.answer(f"❌ خطأ: {e}", show_alert=True)


@main_router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    """قبول جميع طلبات الدفع المسبق"""
    await query.answer(ok=True)


@main_router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    """
    معالجة الدفع الناجح بالنجوم.
    ✅ فور استلام النجوم:
       1. يُسجَّل الطلب
       2. يُخصم العمولة لمحفظة صاحب البوت (تلقائياً عبر الحساب)
       3. يُرسَل صافي TON لمحفظة المستخدم تلقائياً
    """
    payment    = message.successful_payment
    payload    = payment.invoice_payload   # مثلاً: sell_stars_42
    stars_paid = payment.total_amount      # عدد النجوم

    if payload.startswith("sell_stars_"):
        order_id = int(payload.split("_")[2])
        order    = db.get_sell_order(order_id)

        if not order:
            await message.answer("⚠️ الطلب غير موجود. تواصل مع الدعم.", parse_mode="HTML")
            return

        # ── تحديث الحالة: تم استلام النجوم ──
        db.update_sell_order_status(
            order_id, "stars_received",
            tx_hash=payment.telegram_payment_charge_id
        )
        db.log_action(message.from_user.id, "stars_payment_received",
                      f"order={order_id} stars={stars_paid} charge={payment.telegram_payment_charge_id}")

        net_ton    = float(order['net_ton'])
        commission = float(order['commission'])

        # ── إشعار المستخدم: النجوم استُلمت، جاري التحويل ──
        await message.answer(
            f"✅ <b>تم استلام {stars_paid} نجمة!</b>\n\n"
            f"📋 رقم الطلب: <b>#{order_id}</b>\n"
            f"💎 TON الصافي: <b>{net_ton:.4f} TON</b>\n"
            f"💰 العمولة: <b>{commission:.4f} TON</b>\n"
            f"📬 المحفظة: <code>{order['ton_wallet']}</code>\n\n"
            f"⚡ <b>جاري التحويل التلقائي...</b>",
            parse_mode="HTML"
        )

        # ── إرسال TON تلقائياً ──
        logger.info(f"[AUTO-SEND] بدء إرسال {net_ton} TON للطلب #{order_id}")
        result = await pay.process_stars_payment(order_id, stars_paid, bot=bot)

        if result["success"]:
            # ✅ الإرسال التلقائي نجح
            await message.answer(
                f"🎉 <b>تم تحويل TON بنجاح!</b>\n\n"
                f"💎 <b>{net_ton:.4f} TON</b> أُرسل إلى:\n"
                f"<code>{order['ton_wallet']}</code>\n\n"
                f"🔗 Hash: <code>{result.get('tx_hash', 'N/A')}</code>\n\n"
                f"شكراً لاستخدامك البوت! 🙏",
                parse_mode="HTML"
            )
            # إشعار الأدمن بالإتمام التلقائي
            for admin_id in ADMIN_IDS:
                try:
                    uname = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
                    await bot.send_message(
                        admin_id,
                        f"✅ <b>إرسال تلقائي مكتمل - الطلب #{order_id}</b>\n\n"
                        f"👤 المستخدم: {uname}\n"
                        f"⭐ النجوم: {stars_paid}\n"
                        f"💎 TON المُرسَل: {net_ton:.4f}\n"
                        f"💰 عمولتك: {commission:.4f} TON\n"
                        f"📬 إلى: <code>{order['ton_wallet']}</code>\n"
                        f"🔗 Tx: <code>{result.get('tx_hash', 'N/A')}</code>",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"فشل إشعار الأدمن: {e}")

        elif result.get("manual_required"):
            # ⚠️ الإرسال التلقائي غير مضبوط - تنبيه الأدمن
            await message.answer(
                f"✅ <b>تم استلام {stars_paid} نجمة!</b>\n\n"
                f"💎 ستستلم <b>{net_ton:.4f} TON</b> قريباً\n"
                f"⏳ المدة المتوقعة: 15-60 دقيقة\n\n"
                f"📋 رقم طلبك: <b>#{order_id}</b>",
                parse_mode="HTML"
            )
            # تنبيه الأدمن لإرسال TON يدوياً
            for admin_id in ADMIN_IDS:
                try:
                    uname = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
                    await bot.send_message(
                        admin_id,
                        f"⭐ <b>نجوم مستلمة - مطلوب إرسال TON يدوياً</b>\n\n"
                        f"📋 الطلب: <b>#{order_id}</b>\n"
                        f"👤 المستخدم: {uname}\n"
                        f"⭐ النجوم: {stars_paid}\n"
                        f"💎 TON الصافي: <b>{net_ton:.4f}</b>\n"
                        f"💰 عمولتك: <b>{commission:.4f} TON</b>\n"
                        f"📬 المحفظة: <code>{order['ton_wallet']}</code>\n\n"
                        f"⚠️ الإرسال التلقائي غير مفعّل\n"
                        f"💡 لتفعيله: أضف TON_MNEMONIC في .env",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ تأكيد الإرسال اليدوي",
                                                  callback_data=f"approve_sell_{order_id}")]
                        ]),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"فشل إشعار الأدمن: {e}")

        else:
            # ❌ خطأ في الإرسال
            await message.answer(
                f"✅ <b>تم استلام {stars_paid} نجمة!</b>\n\n"
                f"⚠️ حدث خطأ في التحويل التلقائي.\n"
                f"سيقوم الفريق بإرسال <b>{net_ton:.4f} TON</b> يدوياً قريباً.\n\n"
                f"📋 رقم طلبك: <b>#{order_id}</b>",
                parse_mode="HTML"
            )
            # تنبيه الأدمن بالخطأ
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"❌ <b>خطأ في الإرسال التلقائي - الطلب #{order_id}</b>\n\n"
                        f"💎 TON المطلوب: {net_ton:.4f}\n"
                        f"📬 المحفظة: <code>{order['ton_wallet']}</code>\n"
                        f"🔴 الخطأ: {result.get('error', 'غير معروف')}\n\n"
                        f"⚡ يرجى الإرسال يدوياً!",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ تأكيد الإرسال اليدوي",
                                                  callback_data=f"approve_sell_{order_id}")]
                        ]),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"فشل إشعار الأدمن: {e}")

    elif payload.startswith("buy_stars_"):
        order_id = int(payload.split("_")[2])
        db.update_buy_order_status(order_id, "stars_sent",
                                   payment_id=payment.telegram_payment_charge_id)
        db.log_action(message.from_user.id, "stars_purchase_completed", f"order={order_id}")
        await message.answer(
            f"✅ <b>تم إرسال النجوم بنجاح!</b>\n"
            f"📋 الطلب #{order_id} مكتمل.",
            parse_mode="HTML"
        )


# ==========================================
#  شراء النجوم بـ TON
# ==========================================

@main_router.message(F.text == "💎 شراء نجوم  ←  TON ⭐")
async def buy_stars_start(message: Message, state: FSMContext):
    user = db.get_or_create_user(message.from_user.id)
    if user.get("is_banned"):
        await message.answer("🚫 تم حظرك من استخدام البوت.")
        return

    ton_rate   = int(db.get_setting("ton_to_star_rate",  str(TON_TO_STAR_RATE)))
    commission = int(db.get_setting("commission_percent", str(COMMISSION_PERCENT)))

    await state.set_state(BuyStars.waiting_stars_amount)
    await message.answer(
        "💎 <b>شراء نجوم بـ TON</b>\n\n"
        f"💱 السعر: <b>1 TON = {ton_rate} نجمة</b>\n"
        f"💰 العمولة: <b>{commission}%</b>\n\n"
        f"الحد الأدنى: <b>{MIN_TON_BUY} TON</b>\n\n"
        "أدخل عدد النجوم التي تريد شراءها:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@main_router.message(BuyStars.waiting_stars_amount)
async def buy_stars_amount(message: Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer("❌ تم الإلغاء.", reply_markup=main_keyboard())
        return
    try:
        stars = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً.")
        return

    if stars < 50:
        await message.answer("❌ الحد الأدنى للشراء هو 50 نجمة.")
        return

    calc = pay.calc_ton_to_stars(stars / float(db.get_setting("ton_to_star_rate", str(TON_TO_STAR_RATE))))
    ton_needed = round(stars / int(db.get_setting("ton_to_star_rate", str(TON_TO_STAR_RATE))), 4)
    ton_with_commission = round(ton_needed * (1 + int(db.get_setting("commission_percent", str(COMMISSION_PERCENT))) / 100), 6)

    await state.update_data(stars=stars, ton_needed=ton_with_commission)
    await state.set_state(BuyStars.confirm_buy)

    memo = f"BUY-STARS-{message.from_user.id}"
    await message.answer(
        f"💰 <b>ملخص الشراء</b>\n\n"
        f"⭐ النجوم: <b>{stars}</b>\n"
        f"💎 المبلغ المطلوب: <b>{ton_with_commission} TON</b>\n"
        f"  (يشمل العمولة)\n\n"
        f"📤 <b>لإتمام الشراء، أرسل:</b>\n"
        f"💎 <b>{ton_with_commission} TON</b>\n"
        f"📬 إلى المحفظة:\n<code>{TON_WALLET_ADDRESS}</code>\n\n"
        f"📝 <b>مع الملاحظة (مهم!):</b>\n<code>{memo}</code>\n\n"
        "بعد الإرسال اضغط تأكيد:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ أرسلت TON، تأكيد", callback_data=f"confirm_buy_{stars}_{ton_with_commission}")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="confirm_no")],
        ]),
        parse_mode="HTML"
    )


@main_router.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy_stars(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    parts  = call.data.split("_")
    stars  = int(parts[2])
    ton    = float(parts[3])

    commission = round(ton - (stars / int(db.get_setting("ton_to_star_rate", str(TON_TO_STAR_RATE)))), 6)
    order_id = db.create_buy_order(call.from_user.id, stars, ton, commission)
    db.log_action(call.from_user.id, "buy_order_created", f"order={order_id} stars={stars} ton={ton}")

    for admin_id in ADMIN_IDS:
        try:
            uname = f"@{call.from_user.username}" if call.from_user.username else f"ID:{call.from_user.id}"
            await bot.send_message(
                admin_id,
                f"🔔 <b>طلب شراء جديد #{order_id}</b>\n\n"
                f"👤 المستخدم: {uname}\n"
                f"⭐ النجوم المطلوبة: <b>{stars}</b>\n"
                f"💎 TON المرسل: <b>{ton}</b>\n"
                f"📝 تحقق من استلام TON ثم أرسل النجوم.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ إرسال النجوم", callback_data=f"send_stars_buy_{order_id}")]
                ]),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"فشل إشعار الأدمن: {e}")

    await call.message.edit_text(
        f"✅ <b>تم إنشاء طلب الشراء #{order_id}</b>\n\n"
        f"⭐ النجوم: <b>{stars}</b>\n"
        f"⏳ جاري التحقق من استلام <b>{ton} TON</b>\n\n"
        "سيتم إرسال النجوم إلى حسابك خلال 15-60 دقيقة بعد التحقق.",
        parse_mode="HTML"
    )


# ==========================================
#  تحويل TON لشخص آخر
# ==========================================

@main_router.message(F.text == "💸 تحويل TON")
async def transfer_ton_start(message: Message, state: FSMContext):
    await state.set_state(TransferTON.waiting_recipient)
    await message.answer(
        "💸 <b>تحويل TON لشخص آخر</b>\n\n"
        "أرسل معرف تيليغرام (@username) أو ID الشخص المستقبل:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@main_router.message(TransferTON.waiting_recipient)
async def transfer_ton_recipient(message: Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer("❌ تم الإلغاء.", reply_markup=main_keyboard())
        return

    recipient = message.text.strip().lstrip("@")
    await state.update_data(recipient=recipient)
    await state.set_state(TransferTON.waiting_amount)
    await message.answer(
        f"📬 المستقبل: <b>@{recipient}</b>\n\n"
        "💎 أدخل مقدار TON المراد تحويله:",
        parse_mode="HTML"
    )


@main_router.message(TransferTON.waiting_amount)
async def transfer_ton_amount(message: Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer("❌ تم الإلغاء.", reply_markup=main_keyboard())
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً مثل: 1.5")
        return
    if amount < 0.1:
        await message.answer("❌ الحد الأدنى للتحويل 0.1 TON")
        return

    await state.update_data(amount=amount)
    await state.set_state(TransferTON.waiting_note)
    await message.answer(
        f"💎 المبلغ: <b>{amount} TON</b>\n\n"
        "📝 أضف ملاحظة للتحويل (اختياري - أو أرسل -):",
        parse_mode="HTML"
    )


@main_router.message(TransferTON.waiting_note)
async def transfer_ton_note(message: Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer("❌ تم الإلغاء.", reply_markup=main_keyboard())
        return
    note = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(note=note)
    await state.set_state(TransferTON.confirm_transfer)

    data = await state.get_data()
    await message.answer(
        f"📋 <b>تأكيد التحويل</b>\n\n"
        f"📬 إلى: <b>@{data['recipient']}</b>\n"
        f"💎 المبلغ: <b>{data['amount']} TON</b>\n"
        f"📝 ملاحظة: {note or 'لا توجد'}\n\n"
        "هل تريد المتابعة؟",
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


@main_router.callback_query(F.data == "confirm_yes", TransferTON.confirm_transfer)
async def confirm_transfer_ton(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    # هذه عملية يدوية - الأدمن يتولى التحويل الفعلي
    for admin_id in ADMIN_IDS:
        try:
            uname = f"@{call.from_user.username}" if call.from_user.username else f"ID:{call.from_user.id}"
            await bot.send_message(
                admin_id,
                f"💸 <b>طلب تحويل TON جديد</b>\n\n"
                f"👤 من: {uname} (ID: {call.from_user.id})\n"
                f"📬 إلى: @{data['recipient']}\n"
                f"💎 المبلغ: <b>{data['amount']} TON</b>\n"
                f"📝 ملاحظة: {data.get('note') or 'لا توجد'}\n\n"
                "⚠️ يرجى التحقق وإجراء التحويل.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"فشل إشعار الأدمن: {e}")

    db.log_action(call.from_user.id, "transfer_ton_requested",
                  f"to={data['recipient']} amount={data['amount']}")

    await call.message.edit_text(
        f"✅ <b>تم إرسال طلب التحويل!</b>\n\n"
        f"📬 إلى: <b>@{data['recipient']}</b>\n"
        f"💎 المبلغ: <b>{data['amount']} TON</b>\n\n"
        "⏳ سيتم تنفيذ التحويل خلال 15-60 دقيقة.",
        parse_mode="HTML"
    )


# ==========================================
#  إلغاء عام
# ==========================================

@main_router.callback_query(F.data == "confirm_no")
async def confirm_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ تم الإلغاء.")
    await call.message.answer("القائمة الرئيسية:", reply_markup=main_keyboard())


@main_router.message(F.text == "❌ إلغاء")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ تم الإلغاء.", reply_markup=main_keyboard())


# ==========================================
#  عرض طلبات المستخدم
# ==========================================

@main_router.message(F.text == "📋 طلباتي")
@main_router.callback_query(F.data == "my_orders")
async def my_orders(event, state: FSMContext = None):
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        send    = event.message.answer
    else:
        user_id = event.from_user.id
        send    = event.answer

    sell_orders = db.get_user_sell_orders(user_id, limit=5)
    text = "📋 <b>آخر طلباتك</b>\n\n"

    if not sell_orders:
        text += "لا توجد طلبات بعد."
    else:
        status_map = {
            "pending":        "⏳ معلق",
            "stars_received": "⭐ نجوم مستلمة",
            "completed":      "✅ مكتمل",
            "rejected":       "❌ مرفوض",
        }
        for o in sell_orders:
            status = status_map.get(o['status'], o['status'])
            text += (
                f"🔹 #{o['order_id']} | ⭐{o['stars_amount']} → 💎{o['net_ton']:.4f} TON\n"
                f"   الحالة: {status} | {o['created_at'][:10]}\n\n"
            )

    await send(text, parse_mode="HTML", reply_markup=main_keyboard())


# ==========================================
#  تشغيل البوت
# ==========================================

async def main():
    db.init_db()
    bot        = Bot(token=BOT_TOKEN, parse_mode=None)
    storage    = MemoryStorage()
    dp         = Dispatcher(storage=storage)

    dp.include_router(admin_router)
    dp.include_router(main_router)

    logger.info("🚀 البوت يعمل...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
