from datetime import timedelta
from decimal import Decimal

import stripe
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response

from borrow.models import Borrow, Payment


def start_checkout_session(
    borrow: Borrow, payment: Payment, fine_multiplier: int = 1
) -> dict | Response:
    """
    Start checkout session for payment at borrow with fine multiplier.
    If fine multiplier == 1 borrow is created or payment is renewed, else
    borrow is returned
    """
    stripe.api_key = settings.STRIPE_API_KEY
    action_url = reverse("borrow:payment-is-success", args=[payment.id])
    cancel_url = reverse("borrow:payment-cancel-payment", args=[payment.id])
    host = settings.HOST
    if fine_multiplier == 1:
        days_count = borrow.expected_return_date - borrow.borrow_date
    else:
        days_count = borrow.actual_return_date - borrow.expected_return_date
    amount = (
        fine_multiplier
        * Decimal(borrow.book.daily_fee)
        * Decimal(days_count / timedelta(days=1))
    )

    try:
        return stripe.checkout.Session.create(
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(amount * 100),
                        "product_data": {
                            "name": borrow.book.title,
                            "description": "borrowing "
                            f"at {borrow.borrow_date}",
                        },
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=str(host + action_url),
            cancel_url=str(host + cancel_url),
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
