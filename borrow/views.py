from typing import Type

import stripe
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    extend_schema_view,
    OpenApiResponse,
)
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from book.models import Book
from borrow import utils
from borrow.models import Borrow, Payment
from borrow.serializers import (
    BorrowListSerializer,
    BorrowCreateSerializer,
    BorrowDetailSerializer,
    BorrowSerializer,
    PaymentListSerializer,
    PaymentDetailSerializer,
    BorrowReturnBookSerializer,
    PaymentIsSuccessSerializer,
    PaymentSerializer,
)
from user.management.commands import t_bot
from user.models import TelegramChat


@extend_schema_view(
    create=extend_schema(
        description="Create borrow and check if pending payment exist for "
        "user. Create & add payment for borrow, & send info message about it "
        "using telegram"
    ),
    list=extend_schema(
        description="Return all borrows for admin user and self borrows for "
        "non-admin user. Can filtering borrows by user for admin user and by "
        "borrows active status for all user"
    ),
    retrieve=extend_schema(description="Return borrow detail information"),
)
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
        queryset = Borrow.objects.select_related(
            "book", "user"
        ).prefetch_related("payments")
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)

        is_active = self.request.query_params.get("is_active")
        user_ids = self.request.query_params.get("user_id")

        if is_active:
            queryset = queryset.filter(
                actual_return_date__isnull=bool(int(is_active))
            )

        if user_ids and self.request.user.is_staff:
            user_ids = self._params_to_ints(user_ids)
            queryset = queryset.filter(user_id__in=user_ids)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "is_active",
                type={"type": "number"},
                description=(
                    "Filter by borrowing returned or no "
                    "(ex. ?is_active=1). 1 == True, 0 == False"
                ),
            ),
            OpenApiParameter(
                "user_ids",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by users (ex. ?user_ids=2,7,9).",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self) -> Type[BorrowSerializer]:
        """Take different serializers for different actions"""
        if self.action == "list":
            return BorrowListSerializer
        if self.action == "retrieve":
            return BorrowDetailSerializer
        if self.action == "create":
            return BorrowCreateSerializer
        if self.action == "borrow_book_return":
            return BorrowReturnBookSerializer
        return BorrowSerializer

    def create(self, request: Request, *args: list, **kwargs: dict):
        """
        Create borrow and check if pending payment exist for user
        """
        payments = Payment.objects.filter(
            Q(user=self.request.user) & Q(status="open")
        )
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

            checkout_session = utils.start_checkout_session(borrow, payment)

            payment.session_id = checkout_session["id"]
            payment.session_url = checkout_session["url"]
            payment.save()

            borrow.payments.add(payment)
            borrow.save()

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
                async_to_sync(t_bot.send_msg)(
                    text=text, chat_user_id=chat_user_id
                )

    @extend_schema(
        request=None,
        responses=BorrowReturnBookSerializer,
    )
    @action(
        methods=["POST"],
        detail=True,
        url_name="book-return",
        url_path="return",
    )
    def borrow_book_return(self, request: Request, pk: int) -> Response:
        """Close borrow and grow up book inventory when it returns"""
        borrow = self.get_object()

        serializer = self.get_serializer(borrow, request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        description="Return list of payments for logged user "
        "and all payments is logged user is staff"
    ),
    retrieve=extend_schema(description="Return payment detail information"),
)
class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self) -> QuerySet:
        """Return all orders for admin & only self orders for non_admin user"""
        queryset = Payment.objects.select_related("user", "borrow")
        if not self.request.user.is_staff:
            return queryset.filter(user=self.request.user)

        return queryset

    def get_serializer_class(self) -> Type[PaymentSerializer]:
        """Take different serializers for different actions"""
        if self.action == "list":
            return PaymentListSerializer
        if self.action == "retrieve":
            return PaymentDetailSerializer
        if self.action == "is_success":
            return PaymentIsSuccessSerializer
        if self.action == "renew_payment":
            return PaymentDetailSerializer
        return PaymentSerializer

    @extend_schema(
        responses=PaymentListSerializer,
    )
    @action(
        methods=["GET"],
        detail=True,
        url_name="is-success",
    )
    def is_success(self, request: Request, pk: int = None) -> Response:
        """
        Check session's payment status, change Payment status if it changed and
        send message via Telegram
        """
        stripe.api_key = settings.STRIPE_API_KEY
        payment = self.get_object()
        session = stripe.checkout.Session.retrieve(payment.session_id)

        if session.status == "complete" and payment.status != "success":
            payment.status = "success"

            chat_user_id_list = TelegramChat.objects.values_list(
                "chat_user_id", flat=True
            )
            borrow = payment.borrow
            text = f"For borrowing {borrow} payment was paid"
            if chat_user_id_list:
                for chat_user_id in chat_user_id_list:
                    async_to_sync(t_bot.send_msg)(
                        text=text, chat_user_id=chat_user_id
                    )

        serializer = self.get_serializer(payment, request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses=PaymentListSerializer,
    )
    @action(
        methods=["GET"],
        detail=True,
        url_name="renew-payment",
    )
    def renew_payment(self, request: Request, pk: int = None) -> Response:
        """Renew payment"""
        payment = self.get_object()

        if payment.status == "expired":
            borrow = payment.borrow
            new_payment = Payment.objects.create(user=request.user)

            checkout_session = utils.start_checkout_session(
                borrow, new_payment
            )

            new_payment.session_id = checkout_session["id"]
            new_payment.session_url = checkout_session["url"]

            borrow.payments.add(new_payment)
            borrow.save()

            serializer = PaymentDetailSerializer(new_payment, request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)

        message = {
            "error": f"Payment status is {payment.status}. "
            "You can not renew payment if it is not expired"
        }

        return Response(message, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses=OpenApiResponse(OpenApiTypes.STR),
    )
    @action(
        methods=["GET"],
        detail=True,
        url_name="cancel-payment",
    )
    def cancel_payment(self, request: Request, pk: int = None) -> Response:
        """
        Display message to user about payment's possibilities and duration
        session
        """
        message = (
            "You can pay later, but remember, "
            "the payment must be made within 24 hours"
        )

        return Response(message, status=status.HTTP_200_OK)
