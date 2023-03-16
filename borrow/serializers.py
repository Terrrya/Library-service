from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from book.serializers import BookSerializer
from borrow.models import Borrow


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
            "actual_return_date",
            "book",
            "user",
        )

    def validate(self, attrs: dict) -> dict:
        """Call validate return dates from model class"""
        data = super().validate(attrs)
        try:
            Borrow(**data).clean()
        except ValidationError as error:
            raise serializers.ValidationError(error.message_dict)
        return data


class BorrowListSerializer(BorrowSerializer):
    book = BookSerializer(many=False, read_only=True)
