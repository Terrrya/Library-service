import asyncio

from django.db.models import Q
from django.utils import timezone
from rest_framework.utils import json

from borrow.models import Borrow
from borrow.serializers import BorrowDetailSerializer
from user.management.commands.t_bot import send_msg
from user.models import TelegramChat


def inform_borrowing_overdue() -> None:
    """
    Task in Django-Q witch send message about borrowing overdue through
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
            serializer = BorrowDetailSerializer(borrow)
            text += json.dumps(serializer.data, indent=4) + "\n"

    for chat_user_id in TelegramChat.objects.values_list(
        "chat_user_id", flat=True
    ):
        asyncio.run(send_msg(text=text, chat_user_id=chat_user_id))
