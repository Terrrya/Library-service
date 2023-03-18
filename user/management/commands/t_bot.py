import logging

from asgiref.sync import sync_to_async
from django.core.management import BaseCommand
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from user.models import TelegramChat

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


@sync_to_async
def save_chat_id(chat_id: int) -> None:
    if chat_id not in list(
        TelegramChat.objects.values_list("chat_id", flat=True)
    ):
        TelegramChat.objects.create(chat_id=chat_id)


@sync_to_async
def delete_chat_id(chat_id) -> None:
    if chat_id in list(TelegramChat.objects.values_list("chat_id", flat=True)):
        chat_obj = TelegramChat.objects.get(chat_id=chat_id)
        chat_obj.delete()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_chat_id(update.effective_chat.id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"Hi {update.effective_user.first_name}. "
            f"Your id: {update.effective_user.id}"
        ),
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_chat_id(update.effective_chat.id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Bye, bye!"
    )


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        application = (
            ApplicationBuilder()
            .token("6106391819:AAHtjwZ4TTLgeOUi_rSl58as8pqMq5HlHSY")
            .build()
        )

        start_handler = CommandHandler("start", start)
        stop_handler = CommandHandler("stop", stop)
        application.add_handler(start_handler)
        application.add_handler(stop_handler)

        application.run_polling()
