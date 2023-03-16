from django.urls import path, include
from rest_framework import routers

from borrow.views import BorrowViewSet

router = routers.DefaultRouter()
router.register("", BorrowViewSet)

app_name = "borrow"

urlpatterns = [path("", include(router.urls))]
