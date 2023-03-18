import asyncio
import os
from typing import Type

import telegram
from django.contrib.auth import get_user_model
from dotenv import load_dotenv
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import api_view
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from book.models import Book
from borrow.models import Borrow
from borrow.serializers import (
    BorrowListSerializer,
    BorrowCreateSerializer,
    BorrowDetailSerializer,
    BorrowSerializer,
)
from user.models import TelegramChat

load_dotenv()


async def send_message(text: str, chat_user_id: int) -> None:
    bot_api = (
        f"{os.getenv('BOT_API')}"
        if os.getenv("BOT_API")
        else "6106391819:AAHtjwZ4TTLgeOUi_rSl58as8pqMq5HlHSY"
    )
    bot = telegram.Bot(bot_api)
    async with bot:
        await bot.send_message(text=text, chat_id=chat_user_id)


class BorrowViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Borrow View"""

    permission_classes = (IsAuthenticated,)

    @staticmethod
    def _params_to_ints(qs: str) -> list[int]:
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self) -> QuerySet:
        """Return all borrows for admin user and self borrows for non-admin
        user. Filtering borrows by user ids for admin user and borrows active
        status"""
        queryset = Borrow.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)

        is_active = self.request.query_params.get("is_active")
        user_ids = self.request.query_params.get("user_id")

        if is_active:
            is_active = self._params_to_ints(is_active)[0]
            queryset = queryset.filter(
                actual_return_date__isnull=bool(is_active)
            )

        if user_ids and self.request.user.is_staff:
            user_ids = self._params_to_ints(user_ids)
            queryset = queryset.filter(user_id__in=user_ids)

        return queryset

    def get_serializer_class(self) -> Type[BorrowSerializer]:
        """Take different serializers for different actions"""
        if self.action == "list":
            return BorrowListSerializer
        if self.action == "retrieve":
            return BorrowDetailSerializer
        if self.action == "create":
            return BorrowCreateSerializer

    def perform_create(self, serializer: BorrowSerializer) -> None:
        """Add current user to borrowing & send message by telegram"""
        serializer.save(user=self.request.user)
        chat_user_id_list = TelegramChat.objects.values_list(
            "chat_user_id", flat=True
        )
        data = serializer.data
        book = Book.objects.get(id=data["book"])
        user = get_user_model().objects.get(id=data["user"])
        text = (
            f"Book: '{book.title}' borrowing by {user.first_name} "
            f"{user.last_name} ({user.email}) at {data['borrow_date']}. "
            f"Expected return data is {data['expected_return_date']}."
        )
        if chat_user_id_list:
            for chat_user_id in chat_user_id_list:
                asyncio.run(send_message(text=text, chat_user_id=chat_user_id))


@api_view(["POST"])
def borrow_book_return(request: Request, pk: int) -> Response:
    """Close borrow and grow up book inventory when it returns"""
    borrow = get_object_or_404(Borrow, id=pk)
    book = borrow.book
    if borrow.actual_return_date:
        raise ValidationError(
            {
                "actual_return_date": "The Borrow already closed and book "
                "returned to library"
            }
        )
    borrow.actual_return_date = timezone.now().date()
    book.inventory += 1
    book.save()
    borrow.save()
    serializer = BorrowDetailSerializer(borrow)
    return Response(serializer.data, status=status.HTTP_200_OK)
