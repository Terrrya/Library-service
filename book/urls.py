from rest_framework import routers

from book.views import BookViewSet

router = routers.DefaultRouter()
router.register("", BookViewSet)

app_name = "book"

urlpatterns = router.urls
