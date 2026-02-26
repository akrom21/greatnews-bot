# ===== Great News Academy Telegram Bot =====
# pip install -U aiogram aiosqlite python-dotenv

import os
import asyncio
from dataclasses import dataclass

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@GreatNews_academy")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@akrom_GN")
OFFICE_MAP_URL = os.getenv("OFFICE_MAP_URL", "https://maps.app.goo.gl/L5PAc4TSfgpcAveA7")
ADMIN_IDS = set(int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip())

DB_PATH = "greatnews.db"

BRAND = "Great News Academy"
TAGLINE = "Kurslar TEKIN. Depozit qilib birga ishlaymiz — foyda 50/50."

ABOUT_TEXT = (
    f"ℹ️ *{BRAND}*\n"
    f"{TAGLINE}\n\n"
    "📌 Nima qilamiz?\n"
    "• Bepul ta’lim (0 dan)\n"
    "• Amaliyot + risk-management\n"
    "• Depozit bilan birga savdo\n"
    "• Foyda: *50/50*\n\n"
    f"📣 Kanal: {CHANNEL_USERNAME}\n"
    f"🧑‍💻 Support: {SUPPORT_USERNAME}"
)

COURSE_TEXT = (
    "📚 *Bepul ta’lim + Hamkorlik*\n\n"
    "*Great News Academy*’da barcha kurslar **mutlaqo bepul**.\n"
    "Siz treydingni **0 dan boshlab** o‘rganasiz va amaliyot qilasiz.\n\n"
    "📈 Bilim yetarli darajaga chiqqach,\n"
    "siz **depozit qilib biz bilan birga savdo qilishingiz** mumkin.\n\n"
    "💼 Hamkorlik ikki shaklda olib boriladi:\n"
    "— 🏢 **Ofisga kelib**\n"
    "— 🌐 **Onlayn tarzda**\n\n"
    "💰 Savdo hamkorlik asosida olib boriladi,\n"
    "**foyda 50/50** tarzida bo‘linadi.\n\n"
    "🎯 Maqsad — **o‘rganish, tajriba va real natija**."
)

WORK_TEXT = (
    "💼 *Depozit bilan ishlash (50/50)*\n\n"
    "Siz depozit qilasiz, biz strategiya va risk-management bilan birga savdo qilamiz.\n"
    "✅ Foyda: *50/50*\n\n"
    "Ariza qoldirsangiz, admin siz bilan bog‘lanadi."
)

RESULTS_TEXT = (
    "🏆 *Natijalar / Proof*\n\n"
    "Real natijalar va case’lar joylanadi.\n"
    f"📣 Kanal: {CHANNEL_USERNAME}"
)

# ---------- FSM ----------
class Apply(StatesGroup):
    name = State()
    age = State()
    experience = State()
    deposit = State()
    mode = State()
    contact = State()

@dataclass
class AppData:
    name: str
    age: str
    experience: str
    deposit: str
    mode: str
    contact: str

# ---------- DB ----------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def save_user(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users(user_id, username, first_name)
            VALUES (?, ?, ?)
        """, (message.from_user.id, message.from_user.username, message.from_user.first_name))
        await db.commit()

async def save_application(user_id: int, username: str | None, data_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO applications(user_id, username, data)
            VALUES (?, ?, ?)
        """, (user_id, username, data_text))
        await db.commit()

async def get_user_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return row[0]

# ---------- Keyboards ----------
def main_menu_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📚 Bepul ta’lim + Hamkorlik")
    kb.button(text="💼 Depozit bilan ishlash (50/50)")
    kb.button(text="📝 Hamkorlik uchun ariza")
    kb.button(text="🏢 Ofis / Onlayn qabul")
    kb.button(text="🏆 Natijalar")
    kb.button(text="🧑‍💻 Support")
    kb.button(text="ℹ️ Academy haqida")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def subscribe_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📣 Kanalga o‘tish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
    kb.button(text="✅ Obuna bo‘ldim", callback_data="check_sub")
    kb.adjust(1, 1)
    return kb.as_markup()

def apply_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Ariza boshlash", callback_data="apply_start")
    kb.adjust(1)
    return kb.as_markup()

def cancel_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="❌ Bekor qilish")
    return kb.as_markup(resize_keyboard=True)

def office_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📍 Ofis lokatsiya (Maps)", url=OFFICE_MAP_URL)
    kb.button(text="🧑‍💻 Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")
    kb.adjust(1, 1)
    return kb.as_markup()

# ---------- Bot ----------
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

async def ensure_access(message: Message) -> bool:
    if CHANNEL_USERNAME and not await is_subscribed(message.from_user.id):
        await message.answer(
            f"👋 Xush kelibsiz *{BRAND}* botiga!\n\n"
            "Botdan foydalanish uchun avval kanalga obuna bo‘ling 👇",
            reply_markup=subscribe_kb(),
            parse_mode="Markdown"
        )
        return False
    return True

@dp.message(CommandStart())
async def start(message: Message):
    await save_user(message)
    if not await ensure_access(message):
        return
    await message.answer(
        f"👋 Xush kelibsiz *{BRAND}*!\n{TAGLINE}\n\nBo‘limni tanlang 👇",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub(cb: CallbackQuery):
    if CHANNEL_USERNAME and not await is_subscribed(cb.from_user.id):
        await cb.answer("Hali obuna bo‘lmagansiz ❌", show_alert=True)
        return
    await cb.message.answer("✅ Obuna tasdiqlandi! Menyudan foydalaning 👇", reply_markup=main_menu_kb())
    await cb.answer()

@dp.message(F.text == "📚 Bepul ta’lim + Hamkorlik")
async def courses(message: Message):
    if not await ensure_access(message):
        return
    await message.answer(COURSE_TEXT, parse_mode="Markdown", reply_markup=apply_kb())

@dp.message(F.text == "💼 Depozit bilan ishlash (50/50)")
async def work(message: Message):
    if not await ensure_access(message):
        return
    await message.answer(WORK_TEXT, parse_mode="Markdown", reply_markup=apply_kb())

@dp.message(F.text == "🏢 Ofis / Onlayn qabul")
async def office_info(message: Message):
    if not await ensure_access(message):
        return
    await message.answer(
        "🏢 *Ofis / Onlayn qabul*\n\n"
        "Hamkorlikka qiziqqanlar:\n"
        "— 🏢 Ofisga kelib ham\n"
        "— 🌐 Onlayn tarzda ham qabul qilinadi.\n\n"
        "📍 Ofis lokatsiyasi: pastdagi tugma orqali.",
        parse_mode="Markdown",
        reply_markup=office_kb()
    )

@dp.message(F.text == "🏆 Natijalar")
async def results(message: Message):
    if not await ensure_access(message):
        return
    await message.answer(RESULTS_TEXT, parse_mode="Markdown")

@dp.message(F.text == "🧑‍💻 Support")
async def support(message: Message):
    if not await ensure_access(message):
        return
    await message.answer(f"🧑‍💻 Support: {SUPPORT_USERNAME}", parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Academy haqida")
async def about(message: Message):
    if not await ensure_access(message):
        return
    await message.answer(ABOUT_TEXT, parse_mode="Markdown")

# ----- Application flow -----
@dp.message(F.text == "📝 Hamkorlik uchun ariza")
async def apply_entry(message: Message, state: FSMContext):
    if not await ensure_access(message):
        return
    await state.clear()
    await message.answer("📝 Ariza qoldirish uchun tugmani bosing 👇", reply_markup=apply_kb())

@dp.callback_query(F.data == "apply_start")
async def apply_start(cb: CallbackQuery, state: FSMContext):
    if CHANNEL_USERNAME and not await is_subscribed(cb.from_user.id):
        await cb.answer("Avval kanalga obuna bo‘ling ❌", show_alert=True)
        return
    await state.set_state(Apply.name)
    await cb.message.answer("Ismingiz va familiyangiz?", reply_markup=cancel_kb())
    await cb.answer()

@dp.message(F.text == "❌ Bekor qilish")
async def apply_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi ✅", reply_markup=main_menu_kb())

@dp.message(Apply.name)
async def apply_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(Apply.age)
    await message.answer("Yoshingiz nechida?", reply_markup=cancel_kb())

@dp.message(Apply.age)
async def apply_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text.strip())
    await state.set_state(Apply.experience)
    
@dp.message(Apply.experience)
async def apply_experience(message: Message, state: FSMContext):
    await state.update_data(experience=message.text.strip())
    await state.set_state(Apply.deposit)
    await message.answer("Depozit miqdori (taxminan)?", reply_markup=cancel_kb())
kb = InlineKeyboardBuilder()
kb.button(text="🟢 Yangi", callback_data="exp_new")
kb.button(text="🟡 O‘rtacha", callback_data="exp_mid")
kb.button(text="🔴 Professional", callback_data="exp_pro")
kb.adjust(1)

await message.answer(
    "📊 Treyding darajangizni tanlang:",
    reply_markup=kb.as_markup()
)
@dp.callback_query(lambda c: c.data.startswith("exp_"))
async def set_experience(call: CallbackQuery, state: FSMContext):
    mapping = {
        "exp_new": "Yangi",
        "exp_mid": "O‘rtacha",
        "exp_pro": "Professional",
    }
    await state.update_data(experience=mapping[call.data])
    await state.set_state(Apply.deposit)
    await call.message.answer("💰 Depozit miqdorini yozing:")
    await call.answer()
@dp.message(Apply.deposit)
async def apply_deposit(message: Message, state: FSMContext):
    await state.update_data(deposit=message.text.strip())
    await state.set_state(Apply.mode)

    kb = ReplyKeyboardBuilder()
    kb.button(text="🏢 Ofisga kelaman")
    kb.button(text="🌐 Onlayn")
    kb.button(text="❌ Bekor qilish")
    kb.adjust(2, 1)

    await message.answer("Hamkorlik shakli: ofis yoki onlayn?", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Apply.mode)
async def apply_mode(message: Message, state: FSMContext):
    if message.text not in ["🏢 Ofisga kelaman", "🌐 Onlayn"]:
        await message.answer("Iltimos, tugmalardan birini tanlang.")
        return

    await state.update_data(mode=message.text)
    if message.text == "🏢 Ofisga kelaman":
        await message.answer("📍 Ofis lokatsiyasi:", reply_markup=office_kb())

    await state.set_state(Apply.contact)
    await message.answer("Aloqa uchun Telegram yoki telefon raqam", reply_markup=cancel_kb())

@dp.message(Apply.contact)
import re

@dp.message(Apply.contact)
async def apply_contact(message: Message, state: FSMContext):
    phone = message.text.strip()

    if not re.fullmatch(r"\+998\d{9}", phone):
        await message.answer(
            "❌ Telefon raqam noto‘g‘ri formatda.\n\n"
            "To‘g‘ri format:\n"
            "+998123456789"
        )
        return

    await state.update_data(contact=phone)
    data = await state.get_data()

    await message.answer(
        "✅ Ariza qabul qilindi!\n\n"
        f"👤 Ism: {data['name']}\n"
        f"🎂 Yosh: {data['age']}\n"
        f"📊 Daraja: {data['experience']}\n"
        f"💰 Depozit: {data['deposit']}\n"
        f"📞 Aloqa: {data['contact']}"
    )
    await state.clear()
    data = await state.get_data()
    summary = (
        "📝 *Yangi ariza*\n\n"
        f"👤 Ism: {data.get('name')}\n"
        f"🎂 Yosh: {data.get('age')}\n"
        f"📈 Tajriba: {data.get('experience')}\n"
        f"💰 Depozit: {data.get('deposit')}\n"
        f"📍 Format: {data.get('mode')}\n"
        f"📞 Aloqa: {message.text}\n\n"
        + (f"User: @{message.from_user.username}" if message.from_user.username else f"User ID: {message.from_user.id}")
    )

    await save_application(message.from_user.id, message.from_user.username, summary)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, summary, parse_mode="Markdown")
        except Exception:
            pass

    await message.answer("✅ Ariza qabul qilindi! Admin bog‘lanadi.", reply_markup=main_menu_kb())
    await state.clear()

# ---- Admin ----
@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id in ADMIN_IDS:
        cnt = await get_user_count()
        await message.answer(f"📊 Users: {cnt}")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo‘q")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
