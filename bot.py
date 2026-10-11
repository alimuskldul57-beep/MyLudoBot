from pathlib import Path
import os
import logging
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 8819614706

PRODUCTS = {
    "online": {
        "name": "Online Version",
        "price": 600,
        "size": "96 MB",
        "link": "https://drive.google.com/file/d/1EZvc-S0UmOcosikT6Dv_Obp-6egnn4fm/view?usp=drivesdk",
    },
    "new": {
        "name": "New Version",
        "price": 300,
        "size": "253 MB",
        "link": "https://drive.google.com/file/d/132-Xuar9gLdV2R_ePfPScz44JVsEbhBr/view?usp=drivesdk",
    },
    "old": {
        "name": "Old Version",
        "price": 200,
        "size": "56 MB",
        "link": "https://drive.google.com/file/d/1glk6wOH_JHOK5sJTH_HwG4o8I3GuoSSa/view?usp=drivesdk",
    },
}


def main_menu():
    buttons = [
        [InlineKeyboardButton(
            f"Online Version — ₹{PRODUCTS['online']['price']}",
            callback_data="buy:online"
        )],
        [InlineKeyboardButton(
            f"New Version — ₹{PRODUCTS['new']['price']}",
            callback_data="buy:new"
        )],
        [InlineKeyboardButton(
            f"Old Version — ₹{PRODUCTS['old']['price']}",
            callback_data="buy:old"
        )],
    ]
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎮 Aapka swagat hai!\n\n"
        "Neeche apni pasand ka APK chunein.\n\n"
        "💳 Payment Admin khud check karega.\n"
        "Payment confirm hone ke baad hi download link milega."
    )

    await update.effective_message.reply_text(
        text,
        reply_markup=main_menu()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Madad ke liye yahan message bhejein.\n"
        "APK kharidne ke liye /start dabayein."
    )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    if data.startswith("buy:"):
        key = data.split(":", 1)[1]

        if key not in PRODUCTS:
            await query.message.reply_text("यह विकल्प उपलब्ध नहीं है।")
            return

        product = PRODUCTS[key]

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "Maine Payment Kar Diya",
                callback_data=f"paid:{key}"
            )],
            [InlineKeyboardButton(
                "Doosra APK Chunein",
                callback_data="menu"
            )],
        ])

        qr_files = {
            "online": "qr_codes/qr_200.png",
            "new": "qr_codes/qr_300.png",
            "old": "qr_codes/qr_600.png",
        }
        qr_path = Path(__file__).resolve().parent / qr_files[key]

        caption = (
            f"📦 APK: {product['name']}\\n"
            f"💰 कीमत: ₹{product['price']}\\n"
            f"📁 साइज़: {product['size']}\\n\\n"
            "Payment karne ke liye upar diya gaya QR code scan karein.\n"
            "Payment karne ke baad 'Maine Payment Kar Diya' dabayein.\n"
            "Admin payment check karne ke baad download link bhejega."
        )

        with qr_path.open("rb") as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard
            )
        return

    if data == "menu":
        await query.message.reply_text(
            "Apna APK chunein:",
            reply_markup=main_menu()
        )
        return

    if data.startswith("paid:"):
        key = data.split(":", 1)[1]

        if key not in PRODUCTS:
            await query.message.reply_text("यह विकल्प उपलब्ध नहीं है।")
            return

        user = query.from_user
        product = PRODUCTS[key]

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ सही पेमेंट",
                    callback_data=f"approve:{user.id}:{key}"
                ),
                InlineKeyboardButton(
                    "❌ पेमेंट नहीं आया",
                    callback_data=f"reject:{user.id}:{key}"
                ),
            ]
        ])

        admin_text = (
            "💳 नया पेमेंट अनुरोध\n\n"
            f"नाम: {user.full_name}\n"
            f"यूज़र ID: {user.id}\n"
            f"यूज़रनेम: @{user.username or 'नहीं है'}\n"
            f"APK: {product['name']}\n"
            f"रकम: ₹{product['price']}\n\n"
            "Google Pay में भुगतान स्वयं जाँचें।"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=keyboard
            )
            await query.message.reply_text(
                "आपका अनुरोध Admin को भेज दिया गया है।\n"
                "भुगतान की पुष्टि होने तक डाउनलोड लिंक नहीं मिलेगा।"
            )
        except Exception:
            logging.exception("Admin को अनुरोध भेजने में समस्या")
            await query.message.reply_text(
                "अभी अनुरोध नहीं भेजा जा सका। बाद में कोशिश करें।"
            )
        return

    if data.startswith("approve:") or data.startswith("reject:"):
        if query.from_user.id != ADMIN_ID:
            await query.answer(
                "यह बटन केवल Admin इस्तेमाल कर सकता है।",
                show_alert=True
            )
            return

        parts = data.split(":")
        if len(parts) != 3:
            return

        action, user_id_text, key = parts

        if key not in PRODUCTS:
            await query.message.reply_text("APK की जानकारी नहीं मिली।")
            return

        try:
            customer_id = int(user_id_text)
        except ValueError:
            await query.message.reply_text("यूज़र ID गलत है।")
            return

        product = PRODUCTS[key]

        if action == "approve":
            try:
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=(
                        ""
                        f"📦 APK: {product['name']}\n"
                        f"📁 साइज़: {product['size']}\n\n"
                        f"⬇️ डाउनलोड लिंक:\n{product['link']}\n\n"
                        ""
                    )
                )
                await query.message.reply_text(
                    "✅ डाउनलोड लिंक ग्राहक को भेज दिया गया।"
                )
            except Exception:
                logging.exception("ग्राहक को लिंक भेजने में समस्या")
                await query.message.reply_text(
                    "लिंक नहीं भेजा जा सका। ग्राहक से पहले बॉट खोलने को कहें।"
                )

        elif action == "reject":
            try:
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=(
                        "❌ अभी आपके भुगतान की पुष्टि नहीं हुई है।\n\n"
                        "कृपया भुगतान की स्थिति जाँचें और Admin से संपर्क करें।"
                    )
                )
                await query.message.reply_text(
                    "ग्राहक को सूचना भेज दी गई।"
                )
            except Exception:
                logging.exception("ग्राहक को सूचना भेजने में समस्या")
                await query.message.reply_text(
                    "ग्राहक को सूचना नहीं भेजी जा सकी।"
                )


async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.effective_message.reply_text(
        "APK खरीदने या विकल्प देखने के लिए /start दबाएँ।\n"
        "मदद के लिए अपना संदेश लिखें।"
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN सेट नहीं है।"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    print("Bot चालू हो रहा है...")
    app.run_polling()


if __name__ == "__main__":
    main()
