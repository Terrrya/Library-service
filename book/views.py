from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from book.models import Book
from book.permissions import IsAdminOrAnyReadOnly
from book.serializers import BookSerializer


@extend_schema_view(
    create=extend_schema(
        description="Crate new book. Only staff user can create"
    ),
    list=extend_schema(description="Return list of all books"),
    retrieve=extend_schema(description="Return book detail information"),
    update=extend_schema(
        description="Update book. Only staff user can update"
    ),
    partial_update=extend_schema(
        description="Partial update book. Only staff user can partial update"
    ),
    destroy=extend_schema(
        description="Delete book. Only staff user can delete"
    ),
)
class BookViewSet(viewsets.ModelViewSet):
    """Book CRUD endpoints"""

    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (IsAdminOrAnyReadOnly,)
