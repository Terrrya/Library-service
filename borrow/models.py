from datetime import date
from typing import Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from book.models import Book


class Borrow(models.Model):
    """Borrow model."""

    borrow_date = models.DateField(default=timezone.now().date())
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(
        to=Book, on_delete=models.CASCADE, related_name="borrows"
    )
    user = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="borrows"
    )

    def _validate_return_dates(
        self,
        expected_return_date: str,
        actual_return_date: str,
        borrow_date: date,
    ) -> None:
        """Validate that return dates is later than the borrow date"""
        for return_date_attr in (expected_return_date, actual_return_date):
            return_date_value = getattr(self, return_date_attr)
            if return_date_value and return_date_value < borrow_date:
                raise ValidationError(
                    {
                        return_date_attr: "You should take "
                        f"{return_date_attr.replace('_', ' ')} later than "
                        f"borrow date: {borrow_date}"
                    }
                )

    def clean(self) -> None:
        self._validate_return_dates(
            "expected_return_date",
            "actual_return_date",
            self.borrow_date,
        )

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[list[str]] = None,
    ) -> None:
        self.full_clean()
        return super().save(force_insert, force_update, using, update_fields)

    def __str__(self) -> str:
        return str(self.borrow_date) + " " + self.book.title


class Payment(models.Model):
    """Order model."""

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="payments"
    )
    session_url = models.TextField(max_length=255, blank=True)
    session_id = models.TextField(max_length=255, blank=True)
    status = models.TextField(max_length=20, default="open")
    borrow = models.ForeignKey(
        to=Borrow,
        on_delete=models.CASCADE,
        related_name="payments",
        blank=True,
        null=True,
    )
