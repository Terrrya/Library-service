from django.urls import path, include
from rest_framework import routers

from borrow.views import (
    BorrowViewSet,
    borrow_book_return,
    PaymentViewSet,
    create_checkout_session,
    # create_payment,
)

router = routers.DefaultRouter()
router.register("borrows", BorrowViewSet, basename="borrow")
router.register("payments", PaymentViewSet, basename="payment")


app_name = "borrow"

urlpatterns = [
    path("", include(router.urls)),
    path(
        "borrows/<int:pk>/return/",
        borrow_book_return,
        name="borrow-book-return",
    ),
    path(
        "borrows/<int:pk>/checkout/create",
        create_checkout_session,
        name="checkout-create",
    ),
]
