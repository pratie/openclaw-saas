🔑 Environment Variables (
.env
)
env
DODO_PAYMENTS_API_KEY=your_dodo_api_key_here
DODO_PRODUCT_ID=pdt_your_product_id_here
DODO_PAYMENTS_WEBHOOK_SECRET=whsec_your_webhook_secret_here
DODO_SUCCESS_URL=https://yourdomain.com/dashboard?payment=success
ENV=development  # or "production" for live_mode
📦 Dependencies (
requirements.txt
)
dodopayments>=1.0.0
standardwebhooks
🗃️ Database Model (SQLAlchemy)
The key columns on your 
User
 table:

python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    has_paid = Column(Boolean, default=False, nullable=False)
    payment_date = Column(DateTime, nullable=True)
    dodo_payment_id = Column(String, nullable=True)          # Stores Dodo's payment ID
    subscription_plan = Column(String, default="none")       # "none", "pending_monthly", "monthly"
    plan_expires_at = Column(DateTime, nullable=True)
💳 Payment Router (Single Product — Simplified)
This is the full, self-contained router you can drop into any FastAPI project:

python
# routers/payment.py
from fastapi import APIRouter, Depends, HTTPException, Request, Header, Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict
from dodopayments import DodoPayments
from standardwebhooks import Webhook
from pydantic import BaseModel, Field
from typing import Optional
import logging
import os
from dotenv import load_dotenv
# Import your own DB session + User model
from database import get_db
from models import User
from auth.router import get_current_user  # Your auth dependency
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payment", tags=["payment"])
# ── Pydantic schemas ──────────────────────────────────────
class CheckoutInput(BaseModel):
    plan: str = "monthly"  # Only one plan for single product
    datafast_visitor_id: Optional[str] = None
class CheckoutResponse(BaseModel):
    checkout_url: str
    plan: str
    price: str
# ── Config ────────────────────────────────────────────────
PRODUCT_PRICE = "$19"
PLAN_DURATION_DAYS = 30
# ── 1. GET /payment/status ────────────────────────────────
@router.get("/status")
async def get_payment_status(
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Check if current user has paid."""
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "has_paid": user.has_paid,
        "payment_date": user.payment_date,
        "subscription_plan": user.subscription_plan,
        "plan_expires_at": user.plan_expires_at,
    }
# ── 2. POST /payment/create-checkout-session ──────────────
@router.post("/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutInput,
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Dodo Payments checkout link (single product)."""
    load_dotenv(override=True)
    dodo_api_key = os.getenv("DODO_PAYMENTS_API_KEY")
    dodo_product_id = os.getenv("DODO_PRODUCT_ID")       # ← single product ID
    if not dodo_api_key or not dodo_product_id:
        raise HTTPException(status_code=500, detail="Dodo Payments not configured")
    # Initialize client
    client = DodoPayments(
        bearer_token=dodo_api_key,
        environment="test_mode" if os.getenv("ENV", "development") == "development" else "live_mode"
    )
    # Create payment
    payment = client.payments.create(
        payment_link=True,
        billing={
            "city": "New York",
            "country": "US",
            "state": "NY",
            "street": "123 Example Street",
            "zipcode": 10001,
        },
        customer={
            "email": current_user_email,
            "name": current_user_email.split("@")[0],
        },
        product_cart=[
            {"product_id": dodo_product_id, "quantity": 1}
        ],
        return_url=os.getenv("DODO_SUCCESS_URL", "http://localhost:3000/dashboard?payment=success")
    )
    # Store payment ID so webhook can match it later
    user = db.query(User).filter(User.email == current_user_email).first()
    if user and hasattr(payment, "id"):
        user.dodo_payment_id = payment.id
        user.subscription_plan = "pending_monthly"
        db.commit()
    return {
        "checkout_url": payment.payment_link,
        "plan": "monthly",
        "price": PRODUCT_PRICE,
    }
# ── 3. POST /payment/success  (called by frontend after redirect) ──
@router.post("/success")
async def payment_success(
    payment_data: dict = Body(None),
    current_user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Frontend calls this after user returns from Dodo checkout."""
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.has_paid:
        user.has_paid = True
        user.payment_date = datetime.utcnow()
        user.subscription_plan = "monthly"
        user.plan_expires_at = datetime.utcnow() + timedelta(days=PLAN_DURATION_DAYS)
        if payment_data and "paymentId" in payment_data:
            user.dodo_payment_id = payment_data["paymentId"]
        db.commit()
    return {"status": "success", "message": "Payment status updated"}
# ── 4. POST /payment/webhook/  (Dodo calls this server-to-server) ──
@router.post("/webhook/")
async def dodo_webhook(
    request: Request,
    webhook_id: str = Header(None),
    webhook_signature: str = Header(None),
    webhook_timestamp: str = Header(None),
    db: Session = Depends(get_db)
):
    """Handle Dodo Payments webhook — the authoritative payment confirmation."""
    webhook_secret = os.getenv("DODO_PAYMENTS_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    # Verify signature
    wh = Webhook(webhook_secret)
    raw_body = await request.body()
    try:
        wh.verify(raw_body, {
            "webhook-id": webhook_id,
            "webhook-signature": webhook_signature,
            "webhook-timestamp": webhook_timestamp,
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    payload = await request.json()
    event_type = payload.get("type")
    if event_type == "payment.succeeded":
        data = payload.get("data", {})
        payment_id = data.get("payment_id")
        customer_email = (data.get("customer") or {}).get("email")
        # Find user by email first, fallback to payment ID
        user = None
        if customer_email:
            user = db.query(User).filter(User.email == customer_email).first()
        if not user and payment_id:
            user = db.query(User).filter(User.dodo_payment_id == payment_id).first()
        if user:
            user.has_paid = True
            user.payment_date = datetime.utcnow()
            user.dodo_payment_id = payment_id
            user.subscription_plan = "monthly"
            user.plan_expires_at = datetime.utcnow() + timedelta(days=PLAN_DURATION_DAYS)
            db.commit()
            logger.info(f"✅ Webhook activated user: {user.email}")
    return {"status": "ok"}
🔌 Wire It Up in 
main.py
python
from routers.payment import router as payment_router
app.include_router(payment_router)
How It Works (flow)
1. Frontend calls  POST /payment/create-checkout-session
   → Backend creates a Dodo payment link, stores the payment ID on the user
   → Returns { checkout_url } to frontend
2. Frontend redirects user to checkout_url (Dodo's hosted page)
3. User pays → Dodo redirects to DODO_SUCCESS_URL
4. Frontend calls  POST /payment/success  (belt-and-suspenders confirmation)
   → Marks user as paid in DB
5. Dodo calls  POST /payment/webhook/  (server-to-server, authoritative)
   → Verifies signature with standardwebhooks
   → Finds user by email or dodo_payment_id
   → Sets has_paid=True, subscription_plan="monthly", plan_expires_at
Key IDs stored on the User:
Column	Purpose
dodo_payment_id	Links the user to their Dodo payment (set during checkout creation, confirmed by webhook)
subscription_plan	"none" → "pending_monthly" (checkout created) → "monthly" (payment confirmed)
plan_expires_at	When access expires (payment_date + 30 days)
has_paid	Simple boolean gate for feature access
This is fully self-contained — just swap out your get_current_user auth dependency, your get_db session, and your 
User
 model, and it'll work in any FastAPI SaaS. 🚀

Good
Bad





