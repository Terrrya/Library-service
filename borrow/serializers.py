from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from book.serializers import BookSerializer
from borrow.models import Borrow
from user.serializers import UserSerializer


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
        )


class BorrowDetailSerializer(BorrowListSerializer):
    user = UserSerializer(many=False, read_only=True)


class BorrowCreateSerializer(BorrowSerializer):
    user = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="id"
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

    def create(self, validated_data):
        """Remove 1 book from book inventory when book is borrowed"""
        book = validated_data["book"]
        book.inventory -= 1
        book.save()
        return super().create(validated_data)
