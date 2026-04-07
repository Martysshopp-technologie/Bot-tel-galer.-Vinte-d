import requests
import asyncio
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")

users = {}
seen = set()

menu = [["🔍 Recherche"], ["🛑 Stop"]]
markup = ReplyKeyboardMarkup(menu, resize_keyboard=True)

def estimate_resale(price):
    return round(price * 2)

def is_good_deal(price):
    return price <= 15

def get_items(query, price):
    url = "https://www.vinted.fr/api/v2/catalog/items"

    params = {
        "search_text": query,
        "price_to": price,
        "order": "newest_first",
        "per_page": 10
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, params=params, headers=headers)
    data = r.json()

    items = []
    for item in data["items"]:
        items.append({
            "id": item["id"],
            "title": item["title"],
            "price": float(item["price"]),
            "url": item["url"],
            "img": item["photo"]["url"]
        })

    return items

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Bot Vinted ELITE", reply_markup=markup)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "🔍 Recherche":
        users[user_id] = {"step": "query"}
        await update.message.reply_text("Mot clé ? (ex: nike)")

    elif text == "🛑 Stop":
        if user_id in users:
            users[user_id]["active"] = False
        await update.message.reply_text("❌ Recherche arrêtée")

    elif user_id in users and users[user_id].get("step") == "query":
        users[user_id]["query"] = text
        users[user_id]["step"] = "price"
        await update.message.reply_text("Prix max ?")

    elif user_id in users and users[user_id].get("step") == "price":
        users[user_id]["price"] = int(text)
        users[user_id]["active"] = True

        await update.message.reply_text("🚀 Scan lancé")

        asyncio.create_task(scan_loop(user_id, context))

async def scan_loop(user_id, context):
    chat_id = user_id

    while users.get(user_id, {}).get("active", False):
        query = users[user_id]["query"]
        price = users[user_id]["price"]

        try:
            items = get_items(query, price)

            for item in items:
                if item["id"] not in seen:
                    seen.add(item["id"])

                    resale = estimate_resale(item["price"])
                    deal = "🔥 BON DEAL" if is_good_deal(item["price"]) else ""

                    msg = (
                        f"{deal}\n"
                        f"👕 {item['title']}\n"
                        f"💰 {item['price']}€\n"
                        f"📈 Revente: {resale}€\n"
                        f"👉 {item['url']}"
                    )

                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=item["img"],
                        caption=msg
                    )

            await asyncio.sleep(3)

        except Exception as e:
            print(e)
            await asyncio.sleep(10)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
