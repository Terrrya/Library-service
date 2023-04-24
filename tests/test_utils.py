from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from django.utils import timezone

from book.models import Book
from borrow.models import Payment
from rest_framework.test import APIClient

from borrow.utils import start_checkout_session
from tests.test_book_views import sample_book
from tests.test_borrow_views.test_borrow import sample_borrow, sample_payment


HOST = settings.HOST


def payment_is_success_url(payment_id: int) -> str:
    return reverse("borrow:payment-is-success", args=[payment_id])


def cancel_payment_url(payment_id: int) -> str:
    return reverse("borrow:cancel-payment", args=[payment_id])


class UtilsTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@library.com", "test12345"
        )
        self.client.force_authenticate(self.user)

    @mock.patch("stripe.checkout.Session.create")
    def test_start_checkout_session_without_fine_multiplier(
        self, session_mock
    ) -> None:
        borrow = sample_borrow(
            user=self.user,
            book=sample_book(),
            expected_return_date=timezone.now().date() + timedelta(days=5),
            actual_return_date=timezone.now().date() + timedelta(days=3),
        )
        payment = sample_payment(user=self.user, borrow=borrow)
        days_count = borrow.expected_return_date - borrow.borrow_date
        amount = Decimal(borrow.book.daily_fee) * Decimal(
            days_count / timedelta(days=1)
        )

        start_checkout_session(borrow, payment)

        session_mock.assert_called_once_with(
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(amount * 100),
                        "product_data": {
                            "name": borrow.book.title,
                            "description": "borrowing "
                            f"at {borrow.borrow_date}",
                        },
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=str(
                HOST + payment_is_success_url(payment_id=payment.id)
            ),
            cancel_url=str(HOST + cancel_payment_url(payment_id=payment.id)),
        )

    @mock.patch("stripe.checkout.Session.create")
    def test_start_checkout_session_with_fine_multiplier(
        self, session_mock
    ) -> None:
        borrow = sample_borrow(
            user=self.user,
            book=sample_book(),
            expected_return_date=timezone.now().date() + timedelta(days=5),
            actual_return_date=timezone.now().date() + timedelta(days=15),
        )
        payment = sample_payment(user=self.user, borrow=borrow)
        days_count = borrow.actual_return_date - borrow.expected_return_date
        amount = (
            2
            * Decimal(borrow.book.daily_fee)
            * Decimal(days_count / timedelta(days=1))
        )

        start_checkout_session(borrow, payment, fine_multiplier=2)

        session_mock.assert_called_once_with(
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(amount * 100),
                        "product_data": {
                            "name": borrow.book.title,
                            "description": "borrowing "
                            f"at {borrow.borrow_date}",
                        },
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=str(
                HOST + payment_is_success_url(payment_id=payment.id)
            ),
            cancel_url=str(HOST + cancel_payment_url(payment_id=payment.id)),
        )
