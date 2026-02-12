#!/usr/bin/env python3
"""
Test script to verify Dodo Payments API and fetch products
"""
import requests
import json

API_KEY = "lp5JfYjLaguBQcWe.q6NNxmR6OQeASKBYXI3Vr7Oa2WGaqomB2Is069QbZMsw4JH2"

# Dodo Payments uses Bearer token authentication
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print("🔍 Testing Dodo Payments API Connection...")
print("=" * 60)

# Test 1: Fetch all products
print("\n1️⃣ Fetching all products...")
try:
    response = requests.get(
        "https://api.dodopayments.com/products",
        headers=headers,
        timeout=10
    )
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        products = response.json()
        print(f"✅ Found {len(products)} products")
        print("\nProducts:")
        for product in products:
            print(f"  - ID: {product.get('product_id', 'N/A')}")
            print(f"    Name: {product.get('name', 'N/A')}")
            print(f"    Price: ${product.get('price', {}).get('amount', 'N/A')}")
            print(f"    Type: {product.get('type', 'N/A')}")
            if product.get('recurring'):
                print(f"    Recurring: {product['recurring']}")
            print()
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Request failed: {str(e)}")

# Test 2: Try to fetch specific product ID
print("\n2️⃣ Testing specific product ID from logs...")
product_id = "pdt_0NYLeyWCKUSHjSGrFV3EC"
try:
    response = requests.get(
        f"https://api.dodopayments.com/products/{product_id}",
        headers=headers,
        timeout=10
    )
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        product = response.json()
        print(f"✅ Product found!")
        print(f"Details: {json.dumps(product, indent=2)}")
    else:
        print(f"❌ Product not found: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Request failed: {str(e)}")

# Test 3: Check API key info
print("\n3️⃣ Checking API key information...")
try:
    # Try to get account/business info
    response = requests.get(
        "https://api.dodopayments.com/businesses",
        headers=headers,
        timeout=10
    )
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        business = response.json()
        print(f"✅ Business info retrieved")
        print(f"Business: {json.dumps(business, indent=2)}")
    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Request failed: {str(e)}")

print("\n" + "=" * 60)
print("✅ API Test Complete")
