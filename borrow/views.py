import asyncio
from datetime import timedelta
from decimal import Decimal
from typing import Type, Optional

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet, Q
from django.urls import reverse
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from book.models import Book
from book.permissions import IsAdminOrAnyReadOnly
from borrow.models import Borrow, Payment
from borrow.serializers import (
    BorrowListSerializer,
    BorrowCreateSerializer,
    BorrowDetailSerializer,
    BorrowSerializer,
    PaymentSerializer,
)
from user.management.commands.t_bot import send_msg
from user.models import TelegramChat


def start_checkout_session(
    borrow: Borrow, payment: Payment, fine_multiplier: int = 1
) -> Optional[Response]:
    """
    Start checkout session for payment at borrow with fine multiplier.
    If fine multiplier == 1 borrow is created or payment is renewed, else
    borrow is returned
    """
    stripe.api_key = settings.STRIPE_API_KEY
    action_url = reverse("borrow:checkout-success", args=[payment.id])
    cancel_url = reverse("borrow:cancel-payment", args=[payment.id])
    host = settings.HOST
    if fine_multiplier == 1:
        days_count = borrow.expected_return_date - borrow.borrow_date
    else:
        days_count = borrow.actual_return_date - borrow.expected_return_date
    amount = (
        fine_multiplier
        * Decimal(borrow.book.daily_fee)
        * Decimal(days_count / timedelta(days=1))
    )

    try:
        checkout_session = stripe.checkout.Session.create(
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
            success_url=str(host + action_url),
            cancel_url=str(host + cancel_url),
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    print(checkout_session)
    payment.session_id = checkout_session["id"]
    payment.session_url = checkout_session["url"]
    payment.save()
    borrow.payments.add(payment)
    borrow.save()


class BorrowViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def _params_to_ints(qs: str) -> list[int]:
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self) -> QuerySet:
        """
        Return all borrows for admin user and self borrows for non-admin
        user. Filtering borrows by user ids for admin user and borrows active
        status
        """
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

    def create(self, request: Request, *args: list, **kwargs: dict):
        """
        Create borrow and check if pending payment exist for user
        """
        payments = Payment.objects.filter(
            Q(user=self.request.user) & Q(status__in=("open", "expired"))
        )
        print(payments)
        if payments:
            return Response(
                {"error": "You did not pay all of your payments"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, args, kwargs)

    def perform_create(self, serializer: BorrowSerializer) -> None:
        """
        Save borrow serializer, create & add payment for borrow, & send
        info message about it by telegram
        """
        with transaction.atomic():
            payment = Payment.objects.create(
                user=self.request.user,
            )

            serializer.save(user=self.request.user, payments=[payment])
            data = serializer.data

            borrow = get_object_or_404(Borrow, id=data["id"])
            start_checkout_session(borrow, payment)

        chat_user_id_list = TelegramChat.objects.values_list(
            "chat_user_id", flat=True
        )
        book = Book.objects.get(id=data["book"])
        user = get_user_model().objects.get(id=data["user"])
        text = (
            f"Book: '{book.title}' borrowing by {user.first_name} "
            f"{user.last_name} ({user.email}) at {data['borrow_date']}. "
            f"Expected return data is {data['expected_return_date']}."
        )
        if chat_user_id_list:
            for chat_user_id in chat_user_id_list:
                asyncio.run(send_msg(text=text, chat_user_id=chat_user_id))


class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PaymentSerializer
    permission_classes = (IsAdminOrAnyReadOnly,)

    def get_queryset(self) -> QuerySet:
        """Return all orders for admin & only self orders for non_admin user"""
        queryset = Payment.objects.all()
        if not self.request.user.is_staff:
            return queryset.filter(user=self.request.user)

        return queryset

    def perform_create(self, serializer: PaymentSerializer) -> None:
        """Save borrow serializer & send info message about it by telegram"""
        serializer.save(user=self.request.user)

    @action(
        methods=["GET"],
        detail=True,
        url_path="payment-success",
    )
    def is_payment_success(self, request: Request, pk: int = None) -> Response:
        """
        Check session's payment status & change Payment status if it changed
        """
        stripe.api_key = settings.STRIPE_API_KEY
        payment = self.get_object()
        session = stripe.checkout.Session.retrieve(payment.session_id)

        if session.status == "complete":
            payment.status = "success"
            payment.save()

        serializer = self.get_serializer(payment)

        return Response(serializer.data, status=status.HTTP_200_OK)


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

    if borrow.actual_return_date > borrow.expected_return_date:
        payment = Payment.objects.create(user=request.user)
        start_checkout_session(borrow, payment, 2)

    serializer = BorrowDetailSerializer(borrow)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def cancel_payment(request: Request, pk: int = None) -> Response:
    """
    Display massage to user about payment's possibilities and duration session
    """
    message = (
        "You can pay later, but remember, "
        "the payment must be made within 24 hours"
    )

    return Response(message, status=status.HTTP_200_OK)


@api_view(["GET"])
def renew_payment(request: Request, pk: int = None) -> Response:
    """Renew payment"""
    payment = get_object_or_404(Payment, id=pk)
    borrow = payment.borrow
    payment = Payment.objects.create(user=request.user)
    start_checkout_session(borrow, payment)

    serializer = PaymentSerializer(payment)
    return Response(serializer.data, status=status.HTTP_200_OK)
