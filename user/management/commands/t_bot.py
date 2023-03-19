import logging

import telegram
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management import BaseCommand
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from user.models import TelegramChat

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def send_msg(text: str, chat_user_id: int) -> None:
    """Send message through telegram bot"""
    bot = telegram.Bot(settings.BOT_API)
    async with bot:
        await bot.send_message(text=text, chat_id=chat_user_id)


@sync_to_async
def save_chat_id(chat_user_id: int, first_name: str) -> str:
    """
    Save in DB new chat_user_id and return string witch will be sent to user
    """
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
    """Delete chat_user_id from DB and return string about it"""
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle command "start" in telegram chat with user & call function to
    save chat user id in DB
    """
    text = await save_chat_id(
        update.effective_user.id, update.effective_user.first_name
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle command "stop" in telegram chat with user & call function to
    delete chat user id in DB
    """
    text = await delete_chat_id(update.effective_user.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


class Command(BaseCommand):
    def handle(self, *args: list, **kwargs: dict) -> None:
        """The actual logic of the command to run telegram bot server"""
        application = ApplicationBuilder().token(settings.BOT_API).build()
        start_handler = CommandHandler("start", start)
        stop_handler = CommandHandler("stop", stop)

        application.add_handler(start_handler)
        application.add_handler(stop_handler)

        application.run_polling()
