"""Stripe billing endpoints for Quantum MCP Relayer.

Provides checkout session creation, webhook handling for subscription
upgrades, and customer portal access.
"""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.auth import Tier
from src.api.routes_auth import _get_current_user
from src.config import get_settings
from src.models.schemas import CheckoutRequest
from src.models.user import User, user_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

# ---------------------------------------------------------------------------
# Tier → Stripe Price mapping
# ---------------------------------------------------------------------------

_TIER_PRICES: dict[str, str] = {}  # populated lazily from settings


def _get_price_id(tier_name: str) -> str:
    """Resolve a tier name to a Stripe Price ID, raising 400 on failure."""
    if not _TIER_PRICES:
        settings = get_settings()
        _TIER_PRICES.update({
            "starter": settings.stripe_price_starter,
            "pro": settings.stripe_price_pro,
            "business": settings.stripe_price_business,
        })

    price_id = _TIER_PRICES.get(tier_name)
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier '{tier_name}'. Choose starter, pro, or business.",
        )
    return price_id


def _stripe_api_key() -> str:
    key = get_settings().stripe_secret_key
    if not key:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")
    return key


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/create-checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(_get_current_user),
) -> dict:
    """Create a Stripe Checkout session for upgrading the user's tier.

    Returns ``{"checkout_url": "https://checkout.stripe.com/..."}``
    """
    price_id = _get_price_id(body.tier)
    stripe.api_key = _stripe_api_key()

    # Ensure the user has a Stripe Customer object
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": user.id},
        )
        user_store.set_stripe_customer_id(user.id, customer.id)
        customer_id = customer.id
    else:
        customer_id = user.stripe_customer_id

    settings = get_settings()
    # Determine success/cancel URLs based on environment
    if settings.environment == "production":
        base_url = "https://quantumrelayer.com"
    else:
        base_url = "http://localhost:5173"

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{base_url}/dashboard?checkout=success",
        cancel_url=f"{base_url}/pricing?checkout=cancelled",
        metadata={"user_id": user.id, "tier": body.tier},
    )

    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Handle Stripe webhook events.

    Verifies the webhook signature, then processes ``checkout.session.completed``
    to upgrade the user's tier.
    """
    settings = get_settings()
    stripe.api_key = _stripe_api_key()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if settings.stripe_webhook_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload.")
    else:
        # Dev mode — no signature verification (never do this in prod)
        import json
        event = json.loads(payload)
        logger.warning("stripe_webhook_no_signature_verification")

    event_type = event.get("type") if isinstance(event, dict) else event["type"]

    if event_type == "checkout.session.completed":
        session_data = (
            event.get("data", {}).get("object", {})
            if isinstance(event, dict)
            else event["data"]["object"]
        )

        user_id = session_data.get("metadata", {}).get("user_id")
        tier_name = session_data.get("metadata", {}).get("tier")
        customer_id = session_data.get("customer")

        if user_id and tier_name:
            tier_map = {
                "starter": Tier.starter,
                "pro": Tier.pro,
                "business": Tier.business,
            }
            tier = tier_map.get(tier_name)
            if tier:
                user_store.update_tier(user_id, tier)
                if customer_id:
                    user_store.set_stripe_customer_id(user_id, customer_id)
                logger.info(
                    "tier_upgraded",
                    user_id=user_id,
                    tier=tier_name,
                )
            else:
                logger.warning("unknown_tier_in_webhook", tier=tier_name)
        else:
            logger.warning("missing_metadata_in_webhook", session=session_data.get("id"))
    else:
        logger.debug("unhandled_stripe_event", event_type=event_type)

    return {"received": True}


@router.get("/portal")
async def customer_portal(user: User = Depends(_get_current_user)) -> dict:
    """Create a Stripe Customer Portal session for managing subscriptions.

    Returns ``{"portal_url": "https://billing.stripe.com/..."}``
    """
    stripe.api_key = _stripe_api_key()

    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No active subscription. Create a checkout session first.",
        )

    settings = get_settings()
    if settings.environment == "production":
        return_url = "https://quantumrelayer.com/dashboard"
    else:
        return_url = "http://localhost:5173/dashboard"

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )

    return {"portal_url": session.url}
