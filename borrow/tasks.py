import asyncio
from datetime import timedelta

from asgiref.sync import async_to_sync
from django.db.models import Q
from django.utils import timezone
from rest_framework.utils import json

from borrow.models import Borrow, Payment
from borrow.serializers import (
    BorrowTelegramSerializer,
)
from user.management.commands import t_bot
from user.models import TelegramChat


def inform_borrowing_overdue() -> None:
    """
    Task in Django-Q witch send message about borrowing overdue using
    Telegram bot
    """
    text = "No borrowings overdue today!"
    tomorrow_day = timezone.now().date() + timezone.timedelta(days=1)
    borrow_overdue_list = Borrow.objects.filter(
        Q(expected_return_date__lte=tomorrow_day) & Q(actual_return_date=None)
    )

    if borrow_overdue_list:
        text = "Today borrowings overdue are:\n"
        for borrow in borrow_overdue_list:
            serializer = BorrowTelegramSerializer(borrow)
            text += json.dumps(serializer.data, indent=4) + "\n"

    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            for chat_user_id in TelegramChat.objects.values_list(
                "chat_user_id", flat=True
            ):
                async_to_sync(t_bot.send_msg)(
                    text=text[i : i + 4096], chat_user_id=chat_user_id
                )

    else:
        for chat_user_id in TelegramChat.objects.values_list(
            "chat_user_id", flat=True
        ):
            async_to_sync(t_bot.send_msg)(text=text, chat_user_id=chat_user_id)


def check_payment_session_duration() -> None:
    payments = Payment.objects.filter(status="open")
    for payment in payments:
        if timezone.now() - payment.created_at >= timedelta(days=1):
            payment.status = "expired"
            payment.save()
