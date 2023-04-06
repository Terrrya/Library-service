from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from user.serializers import UserSerializer


class CreateUserView(generics.CreateAPIView):
    """Create new user"""

    serializer_class = UserSerializer


@extend_schema_view(
    get=extend_schema(description="Return logged-in user information"),
    put=extend_schema(description="Update logged-in user information"),
    patch=extend_schema(
        description="Partial update logged-in user information"
    ),
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    """Update user witch already login"""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
