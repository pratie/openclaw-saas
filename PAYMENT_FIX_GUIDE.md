# Dodo Payments Fix Guide

## Critical Bug Fixed ✅

I've fixed the **root cause** of your "Product id does not exist" 404 errors.

### The Problem

Your code was using `client.payments.create()` which is designed for **one-time payments only**. When you tried to use it with a subscription product ID, Dodo's API returned 404 because:

- Subscription products can only be used with `checkout_sessions.create()`
- One-time products can only be used with `payments.create()`
- Using the wrong method makes the API reject valid product IDs

### The Fix

Changed from:
```python
payment = client.payments.create(
    payment_link=True,
    billing={...},
    ...
)
return {'checkout_url': payment.payment_link}
```

To:
```python
checkout_session = client.checkout_sessions.create(
    product_cart=[...],
    billing_address={...},
    ...
)
return {'checkout_url': checkout_session.checkout_url}
```

## Next Steps: Update Railway Environment Variables

### 1. Copy Your Product ID

From your Dodo Payments dashboard screenshot, your product ID is:
```
pdt_0NYLeyWCKUSHjSGrFV3EC
```

### 2. Update Railway Variables

Go to your Railway dashboard:

1. Open your project
2. Go to the **Variables** tab
3. Update or add these variables:

```
DODO_PRODUCT_ID=pdt_0NYLeyWCKUSHjSGrFV3EC
DODO_PAYMENTS_API_KEY=lp5JfYjLaguBQcWe.q6NNxmR6OQeASKBYXI3Vr7Oa2WGaqomB2Is069QbZMsw4JH2
DODO_PAYMENTS_WEBHOOK_SECRET=(your webhook secret from Dodo dashboard)
DODO_SUCCESS_URL=https://open-claw.space/?payment=success
```

**IMPORTANT**: Make sure the `DODO_PAYMENTS_API_KEY` is for **Live Mode**, not Test Mode. Check in your Dodo dashboard under Developer → API Keys.

### 3. Verify Product is in Live Mode

In your Dodo Payments dashboard:

1. Make sure you're in **Live Mode** (toggle at top of dashboard)
2. Go to **Products** section
3. Confirm `pdt_0NYLeyWCKUSHjSGrFV3EC` exists there
4. If it only exists in Test Mode, you need to create it in Live Mode

### 4. Deploy and Test

After updating Railway variables:

1. Railway will automatically redeploy
2. Wait for deployment to complete
3. Test the payment flow by clicking "TRY OPENCLAW RISK-FREE"
4. Check Railway logs for any errors

## About Daily Subscriptions ⚠️

**Important Discovery**: Dodo Payments documentation only mentions:
- Monthly billing intervals
- Yearly billing intervals

**Daily subscriptions are not documented as a supported feature.**

If your $3/day subscription doesn't work even after this fix, you may need to:
- Contact Dodo Payments support to ask if daily billing is supported
- Consider switching to monthly billing ($90/month instead of $3/day)
- Explore if they support usage-based pricing as an alternative

## Testing Checklist

After deploying:

- [ ] Railway deployment completes successfully
- [ ] No errors in Railway logs about product not found
- [ ] Payment modal opens when clicking the CTA button
- [ ] Email submission creates checkout link
- [ ] Checkout page loads from Dodo Payments
- [ ] Can complete test payment (if in test mode)
- [ ] Webhook receives payment confirmation
- [ ] User's has_paid status updates in database

## If You Still Get Errors

Check these:

1. **Product ID Mismatch**: Verify `DODO_PRODUCT_ID` in Railway matches your dashboard
2. **API Key Mode**: Ensure API key is for Live Mode if product is in Live Mode
3. **Daily Billing**: Contact Dodo support to confirm daily subscriptions are supported
4. **Webhook Secret**: Make sure `DODO_PAYMENTS_WEBHOOK_SECRET` is set correctly

## Summary of Changes Made

**File**: `app.py` (line 400-424)

- ✅ Changed API method from `payments.create()` to `checkout_sessions.create()`
- ✅ Updated billing parameter from `billing={}` to `billing_address={}`
- ✅ Fixed response field from `payment.payment_link` to `checkout_session.checkout_url`
- ✅ Fixed zipcode type from int to string
- ✅ Removed unnecessary `payment_link=True` parameter

The code is now using the correct Dodo Payments API for subscription products!
