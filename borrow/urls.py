from django.urls import path, include
from rest_framework import routers

from borrow.views import BorrowListRetrieveViewSet

router = routers.DefaultRouter()
router.register("", BorrowListRetrieveViewSet)

app_name = "borrow"

urlpatterns = [path("", include(router.urls))]
