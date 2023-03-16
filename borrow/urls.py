from django.urls import path, include
from rest_framework import routers

from borrow.views import BorrowViewSet, borrow_book_return

router = routers.DefaultRouter()
router.register("", BorrowViewSet)

app_name = "borrow"

urlpatterns = [
    path("", include(router.urls)),
    path("<int:pk>/return/", borrow_book_return, name="borrow-book-return"),
]
