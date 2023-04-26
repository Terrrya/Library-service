from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from book.serializers import (
    BookSerializer,
    BookTelegramSerializer,
)
from borrow import utils
from borrow.models import Borrow, Payment
from user.serializers import UserSerializer, UserTelegramSerializer


class BorrowSerializer(serializers.ModelSerializer):
    borrow_date = serializers.DateField(
        default=timezone.now().date(), read_only=True
    )

    class Meta:
        model = Borrow
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "book",
            "user",
            "payments",
        )

    def validate(self, attrs: dict) -> dict:
        """Validation return dates from model class"""
        data = super().validate(attrs)
        try:
            Borrow(**data).clean()
        except ValidationError as error:
            raise serializers.ValidationError(error.message_dict)
        return data


class BorrowListSerializer(BorrowSerializer):
    book = BookSerializer(many=False, read_only=True)

    class Meta:
        model = Borrow
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "payments",
        )


class BorrowCreateSerializer(BorrowSerializer):
    user = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="id"
    )
    payments = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="id"
    )

    def validate(self, attrs: dict) -> dict:
        """Validate borrow book inventory"""
        data = super().validate(attrs)
        book = data["book"]
        if book.inventory <= 0:
            raise serializers.ValidationError(
                {
                    "book": "There are no left book: "
                    f"{book.title} in the library"
                }
            )
        return data

    def create(self, validated_data: dict) -> Borrow:
        """Remove 1 book from book inventory when book is borrowed"""
        book = validated_data["book"]
        book.inventory -= 1
        book.save()
        return super().create(validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "borrow",
            "created_at",
            "session_url",
            "session_id",
            "status",
        )


class BorrowDetailSerializer(BorrowListSerializer):
    user = UserSerializer(many=False, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)


class PaymentListSerializer(PaymentSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "borrow",
            "created_at",
            "session_url",
            "session_id",
            "status",
            "user",
        )


class BorrowPaymentSerializer(BorrowListSerializer):
    class Meta:
        model = Borrow
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
        )


class PaymentDetailSerializer(PaymentListSerializer):
    user = UserSerializer(many=False, read_only=True)
    borrow = BorrowPaymentSerializer(many=False, read_only=True)


class BorrowTelegramSerializer(serializers.ModelSerializer):
    user = UserTelegramSerializer(many=False, read_only=True)
    book = BookTelegramSerializer(many=False, read_only=True)

    class Meta:
        model = Borrow
        fields = (
            "borrow_date",
            "expected_return_date",
            "book",
            "user",
        )


class BorrowReturnBookSerializer(BorrowSerializer):
    actual_return_date = serializers.DateField(read_only=True)

    class Meta:
        model = Borrow
        fields = ("id", "actual_return_date")

    def validate(self, attrs: dict) -> dict:
        """Validate data when borrow book returned"""
        data = super().validate(attrs)

        borrow = self.instance
        book = borrow.book

        if borrow.actual_return_date:
            raise serializers.ValidationError(
                {
                    "actual_return_date": "The Borrow already closed and book "
                    "returned to library"
                }
            )
        borrow.actual_return_date = timezone.now().date()
        book.inventory += 1
        book.save()

        if borrow.actual_return_date > borrow.expected_return_date:
            payment = Payment.objects.create(user=borrow.user)

            checkout_session = utils.start_checkout_session(borrow, payment, 2)

            payment.session_id = checkout_session["id"]
            payment.session_url = checkout_session["url"]
            payment.save()

            borrow.payments.add(payment)

        return data


class PaymentIsSuccessSerializer(PaymentSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Payment
        fields = ("id", "status")
