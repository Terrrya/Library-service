from rest_framework import viewsets

from book.models import Book
from book.permissions import IsAdminOrAnyReadOnly
from book.serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    """Book CRUD endpoints"""

    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (IsAdminOrAnyReadOnly,)
