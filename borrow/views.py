from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

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
    """Borrow View"""

    queryset = Borrow.objects.all()
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Return all borrows for admin user and self borrows for non-admin
        user. Filtering borrows by user ids for admin user and borrows active
        status"""
        queryset = self.queryset
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)

        is_active = self.request.query_params.get("is_active")
        user_ids = self.request.query_params.get("user_id")

        if is_active:
            is_active = self._params_to_ints(is_active)[0]
            queryset = queryset.filter(
                actual_return_date__isnull=bool(is_active)
            )

        if user_ids and self.request.user.is_staff:
            user_ids = self._params_to_ints(user_ids)
            queryset = queryset.filter(user_id__in=user_ids)

        return queryset

    def get_serializer_class(self):
        """Take different serializers for different actions"""
        if self.action == "list":
            return BorrowListSerializer
        if self.action == "retrieve":
            return BorrowDetailSerializer
        if self.action == "create":
            return BorrowCreateSerializer

    def perform_create(self, serializer):
        """Add current user to borrowing"""
        serializer.save(user=self.request.user)
