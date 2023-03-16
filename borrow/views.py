from rest_framework import mixins, viewsets

from borrow.models import Borrow
from borrow.serializers import (
    BorrowListSerializer,
    BorrowCreateSerializer,
    BorrowDetailSerializer,
)


class BorrowViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrow.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowListSerializer
        if self.action == "retrieve":
            return BorrowDetailSerializer
        if self.action == "create":
            return BorrowCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
