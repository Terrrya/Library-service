from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from borrow.models import Payment
from borrow.serializers import (
    PaymentListSerializer,
    PaymentDetailSerializer,
)
from tests.test_book_views import sample_book
from tests.test_borrow_views.test_borrow import sample_borrow, sample_payment
from user.models import TelegramChat

PAYMENT_URL = reverse("borrow:payment-list")
PAGINATION_SIZE = 10


def detail_payment_url(payment_id: int) -> str:
    return reverse("borrow:payment-detail", args=(payment_id,))


class UnauthenticatedPaymentTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        response = self.client.get(PAYMENT_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedPaymentTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@library.com", "test12345"
        )
        self.client.force_authenticate(self.user)

    def test_list_payments_return_all_payments_if_admin_else_user_payments(
        self,
    ) -> None:
        sample_payment(session_url="https://test1.com", user=self.user)
        sample_payment(
            session_url="https://test2.com",
            user=get_user_model().objects.create_user(
                "test2@library.com", "test12345"
            ),
        )

        response = self.client.get(PAYMENT_URL)
        payments = Payment.objects.filter(user=self.user)
        serializer = PaymentListSerializer(payments, many=True)

        self.assertEqual(response.data["results"], serializer.data)

    def test_detail_payment(self) -> None:
        payment = sample_payment(user=self.user)

        response = self.client.get(detail_payment_url(payment.id))
        serializer = PaymentDetailSerializer(payment)

        self.assertEqual(response.data, serializer.data)

    def test_create_payment_for_logged_in_user(self) -> None:
        payload = {
            "session_url": "https://test.com",
            "session_id": "test_id",
            "status": "open",
        }

        response = self.client.post(PAYMENT_URL, payload)
        payment = Payment.objects.get(id=response.data["id"])
        serializer = PaymentListSerializer(payment)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.data["user"], self.user.id)

    def test_update_payment_not_allowed(self) -> None:
        sample_payment(user=self.user)
        payload = {
            "session_url": "https://test2.com",
            "session_id": "test_id2",
            "status": "success",
        }

        response = self.client.put(PAYMENT_URL, payload)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_partial_update_payment_not_allowed(self) -> None:
        sample_payment(user=self.user)
        payload = {
            "status": "success",
        }

        response = self.client.patch(PAYMENT_URL, payload)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_payment_not_allowed(self) -> None:
        payment = sample_payment(user=self.user)

        response = self.client.delete(detail_payment_url(payment.id))

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_list_payment_is_paginated(self) -> None:
        for i in range(25):
            sample_payment(session_url=f"https://test{i}.com", user=self.user)
        payments = Payment.objects.all()

        response = self.client.get(PAYMENT_URL)
        serializer = PaymentListSerializer(
            payments[:PAGINATION_SIZE], many=True
        )
        next_page = response.data["next"]
        next_payments = payments[PAGINATION_SIZE:]

        while next_page:
            self.assertEqual(response.data["results"], serializer.data)

            response = self.client.get(next_page)
            next_page = response.data["next"]
            serializer = PaymentListSerializer(
                next_payments[:PAGINATION_SIZE], many=True
            )
            next_payments = next_payments[PAGINATION_SIZE:]

    @mock.patch("user.management.commands.t_bot.send_msg")
    @mock.patch("stripe.checkout.Session.retrieve")
    def test_is_success_action_set_status_success_and_send_msg_via_telegram(
        self, session_mock, send_msg_mock
    ) -> None:
        borrow = sample_borrow(user=self.user, book=sample_book())
        payment = sample_payment(user=self.user, borrow=borrow)
        session_mock.return_value.status = "complete"
        telegram_chat = TelegramChat.objects.create(chat_user_id=11111111)
        text = f"For borrowing {borrow} payment was paid"

        response = self.client.get(
            reverse("borrow:payment-is-success", args=[payment.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        session_mock.assert_called_once_with(payment.session_id)
        send_msg_mock.assert_called_once_with(
            text=text, chat_user_id=telegram_chat.chat_user_id
        )

    def test_cancel_payment_return_message(self) -> None:
        payment = sample_payment(user=self.user)
        text = (
            "You can pay later, but remember, "
            "the payment must be made within 24 hours"
        )

        response = self.client.get(
            reverse("borrow:cancel-payment", args=[payment.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, text)

    @mock.patch("borrow.utils.start_checkout_session")
    def test_renew_payment_create_new_payment_for_borrow(
        self, start_checkout_session_mock
    ) -> None:
        borrow = sample_borrow(user=self.user, book=sample_book())
        payment = sample_payment(user=self.user, borrow=borrow)
        start_checkout_session_mock.return_value = {
            "id": "test_id",
            "url": "test_url",
        }

        response = self.client.get(
            reverse("borrow:renew-payment", args=[payment.id])
        )
        new_payment = Payment.objects.get(id=response.data["id"])
        serializer = PaymentListSerializer(new_payment)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        self.assertIn(new_payment, borrow.payments.all())
        start_checkout_session_mock.assert_called_once_with(
            borrow, new_payment
        )


class AdminPaymentTests(AuthenticatedPaymentTests):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@library.com", "test12345", is_staff=True, is_superuser=True
        )
        self.client.force_authenticate(self.user)

    def test_list_payments_return_all_payments_if_admin_else_user_payments(
        self,
    ) -> None:
        sample_payment(session_url="https://test1.com", user=self.user)
        sample_payment(
            session_url="https://test2.com",
            user=get_user_model().objects.create_user(
                "test2@library.com", "test12345"
            ),
        )

        response = self.client.get(PAYMENT_URL)
        payments = Payment.objects.all()
        serializer = PaymentListSerializer(payments, many=True)

        self.assertEqual(response.data["results"], serializer.data)
