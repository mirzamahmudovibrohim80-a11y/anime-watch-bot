import requests
import random
import json
from deep_translator import GoogleTranslator
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = "8266801767:AAEQWt37jRFsq47jFBC2ckedM3rjR4rMZvY"
FAV_FILE = "favorites.json"

# ---------- ИЗБРАННОЕ ----------
def load_favorites():
    try:
        with open(FAV_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_favorites(data):
    with open(FAV_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

favorites = load_favorites()

# ---------- КЛАВИАТУРЫ ----------
main_keyboard = ReplyKeyboardMarkup(
    [
        ["🎬 Случайное аниме"],
        ["🔍 Поиск аниме"],
        ["❤️ Моё избранное"],
        ["ℹ️ О боте"]
    ],
    resize_keyboard=True
)

def anime_keyboard(page=0, total=1):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("◀️", callback_data="prev"),
                InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"),
                InlineKeyboardButton("▶️", callback_data="next")
            ],
            [
                InlineKeyboardButton("❤️ В избранное", callback_data="fav"),
                InlineKeyboardButton("🧹 Удалить", callback_data="del")
            ],
            [
                InlineKeyboardButton("🔙 Меню", callback_data="menu")
            ]
        ]
    )

# ---------- АНИМЕ ----------
def format_anime(anime):
    title = anime["title"]
    score = anime["score"]
    year = anime["year"]
    genres = ", ".join(g["name"] for g in anime["genres"])
    synopsis_en = anime["synopsis"] or "No description"

    try:
        synopsis = GoogleTranslator(source="auto", target="ru").translate(synopsis_en)
    except:
        synopsis = synopsis_en

    text = (
        f"🌸 *{title}*\n"
        f"⭐ {score} | 📅 {year}\n"
        f"🎐 {genres}\n\n"
        f"📝 {synopsis[:700]}..."
    )

    poster = anime["images"]["jpg"]["large_image_url"]
    return poster, text

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ようこそ, RaiKen 雷 🌸\nВыбирай 👇",
        reply_markup=main_keyboard
    )

# ---------- СЛУЧАЙНОЕ ----------
async def random_anime(update, context):
    page = random.randint(1, 20)
    data = requests.get(f"https://api.jikan.moe/v4/anime?page={page}").json()["data"]
    context.user_data["list"] = data
    context.user_data["index"] = 0
    await show_anime(update, context)

# ---------- ПОКАЗ ----------
async def show_anime(update, context):
    anime = context.user_data["list"][context.user_data["index"]]
    poster, text = format_anime(anime)

    context.user_data["last"] = text
    total = len(context.user_data["list"])
    page = context.user_data["index"]

    if isinstance(update, Update) and update.message:
        await update.message.reply_photo(
            photo=poster,
            caption=text,
            parse_mode="Markdown",
            reply_markup=anime_keyboard(page, total)
        )
    else:
        await update.callback_query.message.edit_media(
            media={
                "type": "photo",
                "media": poster,
                "caption": text,
                "parse_mode": "Markdown"
            },
            reply_markup=anime_keyboard(page, total)
        )

# ---------- ТЕКСТ ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🎬 Случайное аниме":
        await random_anime(update, context)

    elif text == "🔍 Поиск аниме":
        context.user_data["search"] = True
        await update.message.reply_text("Введите название аниме 🔎")

    elif context.user_data.get("search"):
        context.user_data["search"] = False
        q = update.message.text
        data = requests.get(f"https://api.jikan.moe/v4/anime?q={q}").json()["data"]

        if not data:
            await update.message.reply_text("Ничего не найдено 😢")
            return

        context.user_data["list"] = data
        context.user_data["index"] = 0
        await show_anime(update, context)

    elif text == "❤️ Моё избранное":
        uid = str(update.message.from_user.id)
        favs = favorites.get(uid)

        if not favs:
            await update.message.reply_text("Избранное пусто 😢")
            return

        await update.message.reply_text(
            "❤️ *Твоё избранное:*\n\n" + "\n\n".join(favs),
            parse_mode="Markdown"
        )

    elif text == "ℹ️ О боте":
        await update.message.reply_text(
            "🌸 Anime Watch Bot\n"
            "Данные: MyAnimeList\n"
            "Создан RaiKen 雷 ✨"
        )

# ---------- INLINE ----------
async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = str(q.from_user.id)
    await q.answer()

    if q.data == "next":
        context.user_data["index"] = (context.user_data["index"] + 1) % len(context.user_data["list"])
        await show_anime(update, context)

    elif q.data == "prev":
        context.user_data["index"] = (context.user_data["index"] - 1) % len(context.user_data["list"])
        await show_anime(update, context)

    elif q.data == "fav":
        favorites.setdefault(uid, [])
        if context.user_data["last"] not in favorites[uid]:
            favorites[uid].append(context.user_data["last"])
            save_favorites(favorites)
            await q.answer("Добавлено ❤️", show_alert=True)
        else:
            await q.answer("Уже есть ❤️", show_alert=True)

    elif q.data == "del":
        if uid in favorites and context.user_data["last"] in favorites[uid]:
            favorites[uid].remove(context.user_data["last"])
            save_favorites(favorites)
            await q.answer("Удалено 🧹", show_alert=True)

    elif q.data == "menu":
        await q.message.reply_text("Меню 👇", reply_markup=main_keyboard)

# ---------- ЗАПУСК ----------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(CallbackQueryHandler(inline_handler))
app.run_polling()
