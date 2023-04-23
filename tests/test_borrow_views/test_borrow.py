from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from book.models import Book
from borrow.models import Borrow, Payment
from borrow.serializers import (
    BorrowListSerializer,
    BorrowDetailSerializer,
    BorrowCreateSerializer,
)
from user.models import TelegramChat

BORROW_URL = reverse("borrow:borrow-list")
PAGINATION_SIZE = 10
CHECKOUT_SESSION_DATA = {
    "id": "test",
    "url": "https://test.com",
}


def sample_book(**params) -> Book:
    defaults = {
        "title": "Test Book",
        "author": "Test Author",
        "cover": Book.CoverChoices.HARD,
        "inventory": 35,
        "daily_fee": Decimal(1.25),
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def sample_payment(**params) -> Payment:
    defaults = {
        "session_url": "https://test.com",
        "session_id": "test_id",
        "status": "open",
    }
    defaults.update(params)
    return Payment.objects.create(**defaults)


def sample_borrow(**params) -> Borrow:
    defaults = {
        "expected_return_date": timezone.now().date() + timedelta(days=10)
    }
    defaults.update(params)
    return Borrow.objects.create(**defaults)


def detail_borrow_url(borrow_id: int) -> str:
    return reverse("borrow:borrow-detail", args=(borrow_id,))


class UnauthenticatedBorrowTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        response = self.client.get(BORROW_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBorrowTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@library.com", "test12345"
        )

        self.client.force_authenticate(self.user)

    def test_list_borrows_return_all_borrows_if_admin_else_users_borrow(
        self,
    ) -> None:
        sample_borrow(user=self.user, book=sample_book(title="Test Book 1"))
        sample_borrow(
            user=get_user_model().objects.create_user(
                "test2@library.com", "test12345"
            ),
            book=sample_book(title="Test Book 2"),
        )

        response = self.client.get(BORROW_URL)
        borrows = Borrow.objects.filter(user=self.user)[:PAGINATION_SIZE]
        serializer = BorrowListSerializer(borrows, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_list_borrow_is_paginated(self) -> None:
        for i in range(25):
            book = sample_book(title=f"Test{i}")
            sample_borrow(user=self.user, book=book)
        borrows = Borrow.objects.all()

        response = self.client.get(BORROW_URL)
        serializer = BorrowListSerializer(borrows[:PAGINATION_SIZE], many=True)
        next_page = response.data["next"]
        next_borrows = borrows[PAGINATION_SIZE:]

        while next_page:
            self.assertEqual(response.data["results"], serializer.data)

            response = self.client.get(next_page)
            next_page = response.data["next"]
            serializer = BorrowListSerializer(
                next_borrows[:PAGINATION_SIZE], many=True
            )
            next_borrows = next_borrows[PAGINATION_SIZE:]

    def test_detail_borrow(self) -> None:
        borrow = sample_borrow(user=self.user, book=sample_book())

        response = self.client.get(detail_borrow_url(borrow.id))
        serializer = BorrowDetailSerializer(borrow)

        self.assertEqual(response.data, serializer.data)

    def test_filter_borrows_by_is_active(self):
        sample_borrow(user=self.user, book=sample_book(title="Test Book 1"))
        borrow_2 = sample_borrow(
            user=self.user,
            book=sample_book(title="Test Book 2"),
        )
        borrow_2.actual_return_date = timezone.now().date() + timedelta(days=5)
        borrow_2.save()

        response = self.client.get(BORROW_URL, {"is_active": 1})
        borrows = Borrow.objects.filter(
            user=self.user, actual_return_date__isnull=True
        )[:PAGINATION_SIZE]
        serializer = BorrowListSerializer(borrows, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_delete_borrow_not_allowed(self) -> None:
        borrow = sample_borrow(user=self.user, book=sample_book())

        response = self.client.delete(detail_borrow_url(borrow.id))

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_borrow_not_allowed(self) -> None:
        borrow = sample_borrow(user=self.user, book=sample_book())
        url = detail_borrow_url(borrow.id)
        payload = {
            "borrow_date": timezone.now().date(),
            "expected_return_date": timezone.now().date() + timedelta(days=5),
            "actual_return_date": timezone.now().date() + timedelta(days=1),
            "book": sample_book(title="Test2").id,
        }

        response = self.client.put(url, payload)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_partial_update_borrow_not_allowed(self) -> None:
        borrow = sample_borrow(user=self.user, book=sample_book())
        url = detail_borrow_url(borrow.id)
        payload = {
            "borrow_date": timezone.now().date() + timedelta(days=1),
            "book": sample_book(title="Test2").id,
        }

        response = self.client.patch(url, payload)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_can_not_create_borrow_with_expected_return_date_before_today(
        self,
    ) -> None:
        payload = {
            "expected_return_date": timezone.now().date() - timedelta(days=5),
            "book": sample_book().id,
        }

        response = self.client.post(BORROW_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_borrow_return_date_set_return_date(self) -> None:
        borrow = sample_borrow(user=self.user, book=sample_book())

        response = self.client.post(
            reverse("borrow:borrow-book-return", args=[borrow.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["actual_return_date"], str(timezone.now().date())
        )

    def test_borrow_return_date_increase_book_inventory_by_one(self) -> None:
        book_inventory = 3
        borrow = sample_borrow(
            user=self.user, book=sample_book(inventory=book_inventory)
        )

        response = self.client.post(
            reverse("borrow:borrow-book-return", args=[borrow.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["book"]["inventory"], book_inventory + 1
        )

    @mock.patch("user.management.commands.t_bot.send_msg")
    @mock.patch("borrow.utils.start_checkout_session")
    def test_create_borrow_for_logged_in_user(
        self, start_checkout_session_mock, send_msg_mock
    ):
        start_checkout_session_mock.return_value = CHECKOUT_SESSION_DATA

        book = sample_book()
        payload = {
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=10),
        }

        response = self.client.post(BORROW_URL, data=payload)
        borrow = Borrow.objects.get(id=response.data["id"])
        serializer = BorrowCreateSerializer(borrow)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.data["user"], self.user.id)

    @mock.patch("user.management.commands.t_bot.send_msg")
    @mock.patch("borrow.utils.start_checkout_session")
    def test_create_borrow_decrease_book_inventory_by_one(
        self, start_checkout_session_mock, send_msg_mock
    ):
        start_checkout_session_mock.return_value = CHECKOUT_SESSION_DATA

        book_inventory = 3
        book = sample_book(inventory=book_inventory)
        payload = {
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=10),
        }

        response = self.client.post(BORROW_URL, data=payload)
        borrow = Borrow.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(borrow.book.inventory, book_inventory - 1)

    @mock.patch("user.management.commands.t_bot.send_msg")
    @mock.patch("borrow.utils.start_checkout_session")
    def test_create_payment_and_payment_session_when_borrow_created(
        self, start_checkout_session_mock, send_msg_mock
    ):
        start_checkout_session_mock.return_value = CHECKOUT_SESSION_DATA

        book = sample_book()
        payload = {
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=10),
        }

        response = self.client.post(BORROW_URL, data=payload)
        payment = Payment.objects.get(id=response.data["payments"][0])

        start_checkout_session_mock.assert_called_once()
        self.assertEqual(
            payment.session_id,
            start_checkout_session_mock.return_value["id"],
        )
        self.assertEqual(
            payment.session_url,
            start_checkout_session_mock.return_value["url"],
        )

    @mock.patch("user.management.commands.t_bot.send_msg")
    @mock.patch("borrow.utils.start_checkout_session")
    def test_send_message_via_telegram_when_borrow_created(
        self, start_checkout_session_mock, send_msg_mock
    ):
        start_checkout_session_mock.return_value = CHECKOUT_SESSION_DATA
        book = sample_book()
        payload = {
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=10),
        }
        telegram_chat = TelegramChat.objects.create(chat_user_id=11111111)

        self.client.post(BORROW_URL, data=payload)
        text = (
            f"Book: '{book.title}' borrowing by {self.user.first_name} "
            f"{self.user.last_name} ({self.user.email}) at "
            f"{timezone.now().date()}. Expected return data is "
            f"{payload['expected_return_date']}."
        )

        send_msg_mock.assert_called_once_with(
            text=text, chat_user_id=telegram_chat.chat_user_id
        )

    @mock.patch("user.management.commands.t_bot.send_msg")
    @mock.patch("borrow.utils.start_checkout_session")
    def test_can_not_create_borrow_for_logged_in_user_if_payment_open(
        self, start_checkout_session_mock, send_msg_mock
    ):
        borrow = sample_borrow(user=self.user, book=sample_book(title="Test2"))
        sample_payment(user=self.user, borrow=borrow)
        start_checkout_session_mock.return_value = CHECKOUT_SESSION_DATA

        book = sample_book()
        payload = {
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=10),
        }

        response = self.client.post(BORROW_URL, data=payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminBorrowTests(AuthenticatedBorrowTests):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@library.com", "test12345", is_staff=True, is_superuser=True
        )

        self.client.force_authenticate(self.user)

    def test_list_borrows_return_all_borrows_if_admin_else_users_borrow(
        self,
    ) -> None:
        sample_borrow(user=self.user, book=sample_book(title="Test Book 1"))
        sample_borrow(
            user=get_user_model().objects.create_user(
                "test2@library.com", "test12345"
            ),
            book=sample_book(title="Test Book 2"),
        )

        response = self.client.get(BORROW_URL)
        borrows = Borrow.objects.all()[:PAGINATION_SIZE]
        serializer = BorrowListSerializer(borrows, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)
