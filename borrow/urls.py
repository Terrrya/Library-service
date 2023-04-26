from rest_framework import routers

from borrow.views import (
    BorrowViewSet,
    PaymentViewSet,
)

router = routers.DefaultRouter()
router.register("borrows", BorrowViewSet, basename="borrow")
router.register("payments", PaymentViewSet, basename="payment")

app_name = "borrow"

urlpatterns = router.urls
