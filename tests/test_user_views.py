from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from user.serializers import UserSerializer

USER_REGISTER = reverse("user:create")
USER_RPROFILE = reverse("user:manage")


class UnauthenticatedUserApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_create_new_user_without_username(self) -> None:
        payload = {
            "email": "test@test.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "test12345",
        }

        response = self.client.post(USER_REGISTER, data=payload)
        user = get_user_model().objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            if key != "password":
                self.assertEqual(payload[key], getattr(user, key))
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("username", payload.keys())

    def test_manage_profile_not_allowed(self) -> None:
        response = self.client.get(USER_RPROFILE)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_email_required(self) -> None:
        payload = {
            "username": "test@test.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "test12345",
        }

        response = self.client.post(USER_REGISTER, data=payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthenticatedUserApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            first_name="Test",
            last_name="User",
            password="test12345",
        )
        self.client.force_authenticate(self.user)

    def test_manage_profile_user(self) -> None:
        response = self.client.get(USER_RPROFILE)
        serializer = UserSerializer(self.user)

        self.assertEqual(response.data, serializer.data)

    def test_user_can_manage_only_self_profile(self) -> None:
        another_user = get_user_model().objects.create_user(
            email="test2@test.com",
            first_name="Test2",
            last_name="User",
            password="test12345",
        )

        response = self.client.get(USER_RPROFILE)
        serializer = UserSerializer(another_user)

        self.assertNotEqual(response.data, serializer.data)
