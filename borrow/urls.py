from django.urls import path, include
from rest_framework import routers

from borrow.views import (
    BorrowViewSet,
    borrow_book_return,
    PaymentViewSet,
    cancel_payment,
    # create_checkout_session,
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
        "payments/<int:pk>/success-payment/",
        PaymentViewSet.as_view({"get": "is_payment_success"}),
        name="checkout-success",
    ),
    path(
        "payments/<int:pk>/cancel-payment/",
        cancel_payment,
        name="cancel-payment",
    ),
]
