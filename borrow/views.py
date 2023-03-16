from django.shortcuts import render
from rest_framework import mixins, viewsets

from borrow.models import Borrow
from borrow.serializers import BorrowSerializer, BorrowListSerializer


class BorrowListRetrieveViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrow.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowListSerializer
        if self.action == "retrieve":
            return BorrowListSerializer
        return BorrowSerializer
