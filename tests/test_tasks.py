from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.utils import json

from borrow.models import Payment
from borrow.serializers import BorrowTelegramSerializer
from borrow.tasks import (
    inform_borrowing_overdue,
    check_payment_session_duration,
)
from tests.test_book_views import sample_book
from tests.test_borrow_views.test_borrow import sample_borrow, sample_payment
from user.models import TelegramChat


class InformBorrowingOverdueUtilTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            "test@library.com", "test12345"
        )
        self.borrow = sample_borrow(
            user=self.user,
            book=sample_book(),
            expected_return_date=timezone.now().date() + timedelta(days=5),
            actual_return_date=timezone.now().date() + timedelta(days=3),
        )
        self.telegram_chat_id = TelegramChat.objects.create(
            chat_user_id=11111111
        )

    @mock.patch("user.management.commands.t_bot.send_msg")
    def test_with_no_overdue(self, send_msg_mock) -> None:
        text = "No borrowings overdue today!"

        inform_borrowing_overdue()

        send_msg_mock.assert_called_once_with(
            text=text, chat_user_id=self.telegram_chat_id.chat_user_id
        )

    @mock.patch("user.management.commands.t_bot.send_msg")
    def test_with_tomorrow_overdue(self, send_msg_mock) -> None:
        borrow = sample_borrow(
            user=self.user,
            book=sample_book(title="Test2"),
            expected_return_date=timezone.now().date() + timedelta(days=1),
        )
        text = "Today borrowings overdue are:\n"
        serializer = BorrowTelegramSerializer(borrow)
        text += json.dumps(serializer.data, indent=4) + "\n"

        inform_borrowing_overdue()

        send_msg_mock.assert_called_once_with(
            text=text, chat_user_id=self.telegram_chat_id.chat_user_id
        )

    @mock.patch("user.management.commands.t_bot.send_msg")
    def test_with_some_overdue(self, send_msg_mock) -> None:
        borrow_with_tomorrow_overdue = sample_borrow(
            user=self.user,
            book=sample_book(title="Test2"),
            expected_return_date=timezone.now().date() + timedelta(days=1),
        )
        borrow_with_overdue_1 = sample_borrow(
            user=self.user,
            book=sample_book(title="Test3"),
            expected_return_date=timezone.now().date() - timedelta(days=1),
            borrow_date=timezone.now().date() - timedelta(days=10),
        )
        borrow_with_overdue_2 = sample_borrow(
            user=self.user,
            book=sample_book(title="Test4"),
            expected_return_date=timezone.now().date() - timedelta(days=5),
            borrow_date=timezone.now().date() - timedelta(days=10),
        )
        text = "Today borrowings overdue are:\n"
        for borrow in (
            borrow_with_tomorrow_overdue,
            borrow_with_overdue_1,
            borrow_with_overdue_2,
        ):
            serializer = BorrowTelegramSerializer(borrow)
            text += json.dumps(serializer.data, indent=4) + "\n"

        inform_borrowing_overdue()

        send_msg_mock.assert_called_once_with(
            text=text, chat_user_id=self.telegram_chat_id.chat_user_id
        )


class CheckPaymentSessionDurationUtilTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            "test@library.com", "test12345"
        )
        self.payment = sample_payment(user=self.user, status="open")

    def test_with_duration_payment_session_lte_one_day(self) -> None:
        check_payment_session_duration()

        self.assertEqual(self.payment.status, "open")

    def test_with_duration_payment_session_gte_one_day(self) -> None:
        payment = sample_payment(
            user=self.user,
            status="open",
            created_at=timezone.now() - timedelta(days=2),
        )
        payment.created_at = timezone.now() - timedelta(days=2)
        payment.save()

        check_payment_session_duration()
        expired_payment = Payment.objects.get(id=payment.id)

        self.assertEqual(expired_payment.status, "expired")
