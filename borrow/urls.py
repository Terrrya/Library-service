from django.urls import path, include
from rest_framework import routers

from borrow.views import BorrowViewSet, borrow_book_return, PaymentViewSet

router = routers.DefaultRouter()
router.register("borrows", BorrowViewSet, basename="borrow")
router.register("payments", PaymentViewSet, basename="payment")

app_name = "borrow"

urlpatterns = [
    path("", include(router.urls)),
    path("<int:pk>/return/", borrow_book_return, name="borrow-book-return"),
]
