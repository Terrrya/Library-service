from django.urls import path, include
from rest_framework import routers

from book.views import BookViewSet

router = routers.DefaultRouter()
router.register("", BookViewSet)

app_name = "book"

urlpatterns = [path("", include(router.urls))]
