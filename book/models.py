from django.db import models


class Book(models.Model):
    """Book model"""

    class CoverChoices(models.TextChoices):
        HARD = "Hard"
        SOFT = "Soft"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=10, choices=CoverChoices.choices)
    inventory = models.PositiveIntegerField(default=1)
    daily_fee = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ["title", "author", "cover"]
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title
