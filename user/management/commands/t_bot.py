import logging
import os

from asgiref.sync import sync_to_async
from django.core.management import BaseCommand
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from user.models import TelegramChat

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


@sync_to_async
def save_chat_id(chat_user_id: int, first_name: str) -> str:
    if chat_user_id not in TelegramChat.objects.values_list(
        "chat_user_id", flat=True
    ):
        TelegramChat.objects.create(chat_user_id=chat_user_id)
        return (
            f"Hi {first_name}. Your id: {chat_user_id}. You started "
            f"receive messages from Library borrow service"
        )
    return "You are already receiving messages"


@sync_to_async
def delete_chat_id(chat_user_id: int) -> str:
    if chat_user_id in TelegramChat.objects.values_list(
        "chat_user_id", flat=True
    ):
        chat_obj = TelegramChat.objects.get(chat_user_id=chat_user_id)
        chat_obj.delete()
        return (
            "You stopped receiving messages from "
            "Library borrow service. Bye, bye"
        )
    return (
        "You are already stopped receiving messages from "
        "Library borrow service. "
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await save_chat_id(
        update.effective_user.id, update.effective_user.first_name
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await delete_chat_id(update.effective_user.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        bot_api = (
            f"{os.getenv('BOT_API')}"
            if os.getenv("BOT_API")
            else "6106391819:AAHtjwZ4TTLgeOUi_rSl58as8pqMq5HlHSY"
        )
        application = ApplicationBuilder().token(bot_api).build()

        start_handler = CommandHandler("start", start)
        stop_handler = CommandHandler("stop", stop)
        application.add_handler(start_handler)
        application.add_handler(stop_handler)

        application.run_polling()
