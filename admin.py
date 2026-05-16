# ==========================================
#   لوحة الأدمن - admin.py
# ==========================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import database as db
from config import ADMIN_IDS, STAR_TO_TON_RATE, TON_TO_STAR_RATE, COMMISSION_PERCENT

admin_router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ==========================================
#  حالات الأدمن (FSM)
# ==========================================

class AdminStates(StatesGroup):
    waiting_broadcast      = State()
    waiting_complete_order = State()
    waiting_ban_user       = State()
    waiting_rate_update    = State()
    waiting_ton_send       = State()


# ==========================================
#  لوحة التحكم الرئيسية
# ==========================================

def admin_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 الإحصائيات",    callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 المستخدمون",    callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton(text="📥 طلبات البيع",   callback_data="admin_sell_orders"),
            InlineKeyboardButton(text="📤 طلبات الشراء",  callback_data="admin_buy_orders"),
        ],
        [
            InlineKeyboardButton(text="⚙️ تحديث الأسعار", callback_data="admin_update_rates"),
            InlineKeyboardButton(text="📢 بث رسالة",       callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="🚫 حظر مستخدم",    callback_data="admin_ban"),
            InlineKeyboardButton(text="✅ رفع حظر",        callback_data="admin_unban"),
        ],
        [
            InlineKeyboardButton(text="💸 إرسال TON يدوي", callback_data="admin_send_ton"),
        ],
    ])


@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ ليس لديك صلاحية الوصول.")
        return
    stats = db.get_stats()
    text = (
        "🛡 <b>لوحة تحكم الأدمن</b>\n\n"
        f"👥 المستخدمون: <b>{stats['total_users']}</b>\n"
        f"✅ النشطون: <b>{stats['active_users']}</b>\n"
        f"⏳ طلبات بيع معلقة: <b>{stats['pending_sell_orders']}</b>\n"
        f"⏳ طلبات شراء معلقة: <b>{stats['pending_buy_orders']}</b>\n"
        f"💰 إجمالي العمولات: <b>{stats['total_commission']:.4f} TON</b>"
    )
    await message.answer(text, reply_markup=admin_main_keyboard(), parse_mode="HTML")


# ==========================================
#  الإحصائيات
# ==========================================

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    stats = db.get_stats()
    text = (
        "📊 <b>إحصائيات البوت</b>\n\n"
        f"👥 إجمالي المستخدمين: <b>{stats['total_users']}</b>\n"
        f"✅ مستخدمون نشطون: <b>{stats['active_users']}</b>\n\n"
        f"✅ طلبات بيع مكتملة: <b>{stats['completed_sell_orders']}</b>\n"
        f"⭐ إجمالي النجوم المباعة: <b>{stats['total_stars_sold']}</b>\n"
        f"💎 إجمالي TON المدفوع: <b>{stats['total_ton_paid']:.4f}</b>\n\n"
        f"⏳ طلبات بيع معلقة: <b>{stats['pending_sell_orders']}</b>\n"
        f"⏳ طلبات شراء معلقة: <b>{stats['pending_buy_orders']}</b>\n\n"
        f"💰 إجمالي العمولات: <b>{stats['total_commission']:.4f} TON</b>"
    )
    back_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_back")]
    ])
    await call.message.edit_text(text, reply_markup=back_btn, parse_mode="HTML")


# ==========================================
#  إدارة طلبات البيع
# ==========================================

@admin_router.callback_query(F.data == "admin_sell_orders")
async def admin_sell_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    orders = db.get_pending_sell_orders()
    if not orders:
        await call.answer("✅ لا توجد طلبات بيع معلقة", show_alert=True)
        return

    buttons = []
    for order in orders[:10]:
        buttons.append([
            InlineKeyboardButton(
                text=f"#{order['order_id']} | ⭐{order['stars_amount']} → {order['net_ton']:.4f} TON",
                callback_data=f"admin_sell_{order['order_id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_back")])
    await call.message.edit_text(
        f"📥 <b>طلبات البيع المعلقة ({len(orders)})</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@admin_router.callback_query(F.data.startswith("admin_sell_"))
async def admin_view_sell_order(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split("_")[2])
    order    = db.get_sell_order(order_id)
    if not order:
        await call.answer("❌ الطلب غير موجود", show_alert=True)
        return

    user = db.get_user(order['user_id'])
    uname = f"@{user['username']}" if user and user.get('username') else f"ID:{order['user_id']}"

    text = (
        f"📋 <b>تفاصيل الطلب #{order_id}</b>\n\n"
        f"👤 المستخدم: {uname}\n"
        f"⭐ النجوم: <b>{order['stars_amount']}</b>\n"
        f"💎 TON الإجمالي: <b>{order['ton_amount']:.4f}</b>\n"
        f"💰 العمولة: <b>{order['commission']:.4f}</b>\n"
        f"✅ TON الصافي: <b>{order['net_ton']:.4f}</b>\n"
        f"👜 المحفظة: <code>{order['ton_wallet']}</code>\n"
        f"📅 التاريخ: {order['created_at']}"
    )
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ اعتماد الطلب",  callback_data=f"approve_sell_{order_id}"),
            InlineKeyboardButton(text="❌ رفض الطلب",     callback_data=f"reject_sell_{order_id}"),
        ],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_sell_orders")]
    ])
    await call.message.edit_text(text, reply_markup=buttons, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("approve_sell_"))
async def approve_sell_order(call: CallbackQuery, bot):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split("_")[2])
    order    = db.get_sell_order(order_id)
    if not order or order['status'] != 'pending':
        await call.answer("❌ الطلب غير صالح أو مكتمل مسبقاً", show_alert=True)
        return

    # تحديث حالة الطلب
    db.update_sell_order_status(order_id, "completed", tx_hash="manual_by_admin")
    db.log_action(call.from_user.id, "approve_sell", f"order_id={order_id}")

    # إشعار المستخدم
    try:
        user = db.get_user(order['user_id'])
        await bot.send_message(
            order['user_id'],
            f"✅ <b>تم إتمام طلبك #{order_id}</b>\n\n"
            f"⭐ النجوم: <b>{order['stars_amount']}</b>\n"
            f"💎 تم إرسال <b>{order['net_ton']:.4f} TON</b> إلى محفظتك\n"
            f"🏦 المحفظة: <code>{order['ton_wallet']}</code>\n\n"
            f"شكراً لاستخدامك البوت! 🙏",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[NOTIFY] خطأ إشعار المستخدم: {e}")

    await call.answer("✅ تم اعتماد الطلب وإشعار المستخدم", show_alert=True)
    await call.message.edit_text(
        f"✅ تم اعتماد الطلب #{order_id} بنجاح",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_sell_orders")]
        ])
    )


@admin_router.callback_query(F.data.startswith("reject_sell_"))
async def reject_sell_order(call: CallbackQuery, bot):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split("_")[2])
    order    = db.get_sell_order(order_id)
    if not order:
        await call.answer("❌ الطلب غير موجود", show_alert=True)
        return

    db.update_sell_order_status(order_id, "rejected")
    db.log_action(call.from_user.id, "reject_sell", f"order_id={order_id}")

    try:
        await bot.send_message(
            order['user_id'],
            f"❌ <b>تم رفض طلبك #{order_id}</b>\n\n"
            f"يرجى التواصل مع الدعم لمعرفة السبب.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.answer("❌ تم رفض الطلب", show_alert=True)


# ==========================================
#  بث الرسائل
# ==========================================

@admin_router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await call.message.edit_text(
        "📢 <b>أرسل الرسالة التي تريد بثها لجميع المستخدمين:</b>\n\n"
        "يمكنك إرسال نص، صورة، أو فيديو.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_back")]
        ]),
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.waiting_broadcast)
async def send_broadcast(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    users       = db.get_all_users()
    success_cnt = 0
    fail_cnt    = 0
    status_msg  = await message.answer(f"📢 جاري الإرسال لـ {len(users)} مستخدم...")

    for user in users:
        if user['is_banned']:
            continue
        try:
            await message.copy_to(user['user_id'])
            success_cnt += 1
        except Exception:
            fail_cnt += 1
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>تم إرسال البث بنجاح</b>\n\n"
        f"✅ وصل لـ: <b>{success_cnt}</b> مستخدم\n"
        f"❌ فشل لـ: <b>{fail_cnt}</b> مستخدم",
        parse_mode="HTML"
    )


# ==========================================
#  تحديث الأسعار
# ==========================================

@admin_router.callback_query(F.data == "admin_update_rates")
async def update_rates_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    text = (
        "⚙️ <b>الأسعار الحالية</b>\n\n"
        f"⭐ سعر النجمة: <b>{STAR_TO_TON_RATE} TON</b>\n"
        f"💎 سعر TON: <b>{TON_TO_STAR_RATE} نجمة</b>\n"
        f"💰 العمولة: <b>{COMMISSION_PERCENT}%</b>\n\n"
        "لتعديل السعر، أرسل:\n"
        "<code>/setrate star 0.013</code>\n"
        "<code>/setrate ton 77</code>\n"
        "<code>/setrate commission 5</code>"
    )
    await call.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_back")]
        ]),
        parse_mode="HTML"
    )


@admin_router.message(Command("setrate"))
async def set_rate_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ الاستخدام: /setrate [star|ton|commission] [value]")
        return
    key   = parts[1].lower()
    value = parts[2]
    if key == "star":
        db.set_setting("star_to_ton_rate", value)
        await message.answer(f"✅ تم تحديث سعر النجمة إلى {value} TON")
    elif key == "ton":
        db.set_setting("ton_to_star_rate", value)
        await message.answer(f"✅ تم تحديث سعر TON إلى {value} نجمة")
    elif key == "commission":
        db.set_setting("commission_percent", value)
        await message.answer(f"✅ تم تحديث العمولة إلى {value}%")
    else:
        await message.answer("❌ مفتاح غير معروف. استخدم: star, ton, commission")


# ==========================================
#  حظر / رفع حظر المستخدمين
# ==========================================

@admin_router.callback_query(F.data == "admin_ban")
async def ban_user_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_ban_user)
    await state.update_data(ban_action="ban")
    await call.message.edit_text(
        "🚫 أرسل معرف المستخدم (ID) الذي تريد حظره:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_back")]
        ])
    )


@admin_router.callback_query(F.data == "admin_unban")
async def unban_user_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_ban_user)
    await state.update_data(ban_action="unban")
    await call.message.edit_text(
        "✅ أرسل معرف المستخدم (ID) الذي تريد رفع حظره:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_back")]
        ])
    )


@admin_router.message(AdminStates.waiting_ban_user)
async def process_ban_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    action = data.get("ban_action", "ban")
    await state.clear()
    try:
        uid = int(message.text.strip())
        db.ban_user(uid, ban=(action == "ban"))
        icon = "🚫" if action == "ban" else "✅"
        verb = "حظر" if action == "ban" else "رفع حظر"
        await message.answer(f"{icon} تم {verb} المستخدم {uid} بنجاح.")
        db.log_action(message.from_user.id, action, f"target={uid}")
    except ValueError:
        await message.answer("❌ معرف غير صالح. أرسل رقماً فقط.")


# ==========================================
#  إرسال TON يدوي
# ==========================================

@admin_router.callback_query(F.data == "admin_send_ton")
async def admin_send_ton_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_ton_send)
    await call.message.edit_text(
        "💸 أرسل تفاصيل التحويل بالصيغة:\n\n"
        "<code>WALLET AMOUNT NOTE</code>\n\n"
        "مثال:\n"
        "<code>EQD...xyz 1.5 دفع طلب #42</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_back")]
        ]),
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.waiting_ton_send)
async def process_send_ton(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("❌ صيغة غير صحيحة. مثال: <code>WALLET AMOUNT NOTE</code>", parse_mode="HTML")
        return
    wallet = parts[0]
    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("❌ المبلغ غير صالح.")
        return
    note = parts[2] if len(parts) > 2 else ""
    await message.answer(
        f"📋 <b>تأكيد التحويل</b>\n\n"
        f"📬 إلى: <code>{wallet}</code>\n"
        f"💎 المبلغ: <b>{amount} TON</b>\n"
        f"📝 ملاحظة: {note}\n\n"
        f"⚠️ يرجى إجراء التحويل يدوياً من محفظتك ثم تأكيد الطلب في البوت.",
        parse_mode="HTML"
    )
    db.log_action(message.from_user.id, "manual_send_ton", f"to={wallet} amount={amount} note={note}")


# ==========================================
#  رجوع للقائمة الرئيسية
# ==========================================

@admin_router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.clear()
    stats = db.get_stats()
    text = (
        "🛡 <b>لوحة تحكم الأدمن</b>\n\n"
        f"👥 المستخدمون: <b>{stats['total_users']}</b>\n"
        f"✅ النشطون: <b>{stats['active_users']}</b>\n"
        f"⏳ طلبات بيع معلقة: <b>{stats['pending_sell_orders']}</b>\n"
        f"⏳ طلبات شراء معلقة: <b>{stats['pending_buy_orders']}</b>\n"
        f"💰 إجمالي العمولات: <b>{stats['total_commission']:.4f} TON</b>"
    )
    await call.message.edit_text(text, reply_markup=admin_main_keyboard(), parse_mode="HTML")


import asyncio
