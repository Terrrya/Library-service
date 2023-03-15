from datetime import date
from typing import Type

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

    def validate_return_dates(
        self,
        expected_return_date: str,
        actual_return_date: str,
        borrow_date: date,
    ) -> None:
        """Check that return dates is always later than the borrow date"""
        for return_date_attr in (expected_return_date, actual_return_date):
            return_date_value = getattr(self, return_date_attr)
            if return_date_value and return_date_value < borrow_date:
                raise ValidationError(
                    f"You should take {return_date_attr} "
                    f"later than borrow date: {borrow_date}"
                )

    def clean(self):
        self.validate_return_dates(
            "expected_return_date", "actual_return_date", self.borrow_date
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
