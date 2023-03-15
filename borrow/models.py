from datetime import date
from typing import Type

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from book.models import Book


class Borrow(models.Model):
    """Borrow model."""

    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True)
    book = models.ForeignKey(
        to=Book, on_delete=models.CASCADE, related_name="borrows"
    )
    user = models.ForeignKey(
        to=get_user_model(), on_delete=models.CASCADE, related_name="borrows"
    )

    @staticmethod
    def validate_return_dates(
        return_date: date,
        borrow_date: date,
    ) -> None:
        """Check that return date is always later than the borrow date"""
        if return_date < borrow_date:
            raise ValidationError(
                f"You should check date later than borrow date: {borrow_date}"
            )

    def clean(self):
        Borrow.validate_return_dates(self.actual_return_date, self.borrow_date)
        Borrow.validate_return_dates(
            self.expected_return_date, self.borrow_date
        )

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str = None,
        update_fields: list[str] = None,
    ) -> None:
        self.full_clean()
        return super().save(force_insert, force_update, using, update_fields)
