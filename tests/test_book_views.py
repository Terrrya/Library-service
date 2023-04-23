from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from book.models import Book
from book.serializers import BookSerializer

BOOK_URL = reverse("book:book-list")
PAGINATION_SIZE = 10


def sample_book(**params) -> Book:
    default = {
        "title": "Test Book",
        "author": "Test Author",
        "cover": Book.CoverChoices.HARD,
        "inventory": 25,
        "daily_fee": 1.45,
    }
    default.update(params)
    return Book.objects.create(**default)


def detail_book_url(book_id: int) -> str:
    return reverse("book:book-detail", kwargs={"pk": book_id})


class UnauthenticatedBookApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_list_book(self) -> None:
        sample_book()
        books = Book.objects.all()[:10]

        response = self.client.get(BOOK_URL)
        serializer = BookSerializer(books, many=True)

        self.assertEqual(response.data["results"], serializer.data)

    def test_list_book_is_paginated(self) -> None:
        for i in range(25):
            sample_book(title=f"Test{i}")
        books = Book.objects.all()

        response = self.client.get(BOOK_URL)
        serializer = BookSerializer(books[:PAGINATION_SIZE], many=True)
        next_page = response.data["next"]
        next_books = books[PAGINATION_SIZE:]

        while next_page:
            self.assertEqual(response.data["results"], serializer.data)

            response = self.client.get(next_page)
            next_page = response.data["next"]
            serializer = BookSerializer(
                next_books[:PAGINATION_SIZE], many=True
            )
            next_books = next_books[PAGINATION_SIZE:]

    def test_retrieve_book(self) -> None:
        book = sample_book()

        response = self.client.get(detail_book_url(book.id))
        serializer = BookSerializer(book)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_book_not_allowed(self) -> None:
        payload = {
            "title": "Test Book",
            "author": "Test Author",
            "cover": Book.CoverChoices.HARD,
            "inventory": 25,
            "daily_fee": 1.45,
        }

        response = self.client.post(BOOK_URL, data=payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_book_not_allowed(self) -> None:
        payload = {
            "title": "Test2 Book",
            "author": "Test2 Author",
            "cover": Book.CoverChoices.SOFT,
            "inventory": 125,
            "daily_fee": 1.00,
        }
        book = sample_book()

        response = self.client.put(detail_book_url(book.id), payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_book_not_allowed(self) -> None:
        payload = {
            "title": "New Test Book",
            "inventory": 225,
        }
        book = sample_book()

        response = self.client.patch(detail_book_url(book.id), payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_book_not_allowed(self) -> None:
        book = sample_book()

        response = self.client.delete(detail_book_url(book.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBookApiTests(UnauthenticatedBookApiTests):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test12345"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_book_not_allowed(self) -> None:
        payload = {
            "title": "Test Book",
            "author": "Test Author",
            "cover": Book.CoverChoices.HARD,
            "inventory": 25,
            "daily_fee": 1.45,
        }

        response = self.client.post(BOOK_URL, data=payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_book_not_allowed(self) -> None:
        payload = {
            "title": "Test2 Book",
            "author": "Test2 Author",
            "cover": Book.CoverChoices.SOFT,
            "inventory": 125,
            "daily_fee": 1.00,
        }
        book = sample_book()

        response = self.client.put(detail_book_url(book.id), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_book_not_allowed(self) -> None:
        payload = {
            "title": "New Test Book",
            "inventory": 225,
        }
        book = sample_book()

        response = self.client.patch(detail_book_url(book.id), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_book_not_allowed(self) -> None:
        book = sample_book()

        response = self.client.delete(detail_book_url(book.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test12345",
            is_staff=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_book(self) -> None:
        sample_book()
        books = Book.objects.all()[:10]

        response = self.client.get(BOOK_URL)
        serializer = BookSerializer(books, many=True)

        self.assertEqual(response.data["results"], serializer.data)

    def test_retrieve_book(self) -> None:
        book = sample_book()

        response = self.client.get(detail_book_url(book.id))
        serializer = BookSerializer(book)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_book(self) -> None:
        payload = {
            "title": "Test Book",
            "author": "Test Author",
            "cover": Book.CoverChoices.HARD,
            "inventory": 25,
            "daily_fee": 1.45,
        }

        response = self.client.post(BOOK_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_book(self) -> None:
        payload = {
            "title": "Test2 Book",
            "author": "Test2 Author",
            "cover": Book.CoverChoices.SOFT,
            "inventory": 125,
            "daily_fee": 1.00,
        }
        book = sample_book()

        response = self.client.put(detail_book_url(book.id), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partial_update_book(self) -> None:
        payload = {
            "title": "New Test Book",
            "inventory": 225,
        }
        book = sample_book()

        response = self.client.patch(detail_book_url(book.id), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_book(self) -> None:
        book = sample_book()

        response = self.client.delete(detail_book_url(book.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
