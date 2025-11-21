# Coupon Management System

Project Overview
This project is a Coupon Management API built for an e-commerce use case. It allows administrators to create coupons with complex eligibility rules (user attributes, cart content, dates) and provides a "Best Coupon" calculation service that automatically determines the highest-value discount for a customer's specific cart.

 Tech Stack
•	Language:  Python 3.10+
•	Framework:  FastAPI (for high-performance API handling)
•	Server:  Uvicorn (ASGI server)
•	Libraries:  Pydantic (Data validation)

How to Run
Prerequisites
 Python 3.9 or higher installed.

Setup Steps
•	Clone the repository.
•	Install dependencies:   pip install fastapi uvicorn
   

Start the Service
•	Run the following command in the terminal:    uvicorn main:app --reload


Testing the API (Sample Data)
You can test the API using Postman, cURL, or the built-in Swagger UI at http://127.0.0.1:8000/docs.

Step 1: Create a Coupon
Endpoint: POST /coupons

Description: Creates a coupon code "SUMMER2025" that gives 10% off if the user buys Electronics worth at least ₹100.

JSON Input:

JSON

{
  "code": "SUMMER2025",
  "description": "10% off on Electronics for Gold users",
  "discountType": "PERCENT",
  "discountValue": 10,
  "maxDiscountAmount": 500,
  "startDate": "2023-01-01",
  "endDate": "2025-12-31",
  "eligibility": {
    "allowedUserTiers": [
      "GOLD",
      "PLATINUM"
    ],
    "minCartValue": 100,
    "applicableCategories": [
      "electronics"
    ]
  }
}
Step 2: Get Best Coupon (Cart Analysis)
Endpoint: POST /best-coupon

Description: Submits a user (Gold Tier) and a Cart (containing Electronics). The system calculates the total value (2000 + 1000 = 3000) and applies the "SUMMER2025" coupon because requirements are met.

JSON Input:

JSON

{
  "user": {
    "userId": "user_99",
    "userTier": "GOLD",
    "country": "IN",
    "lifetimeSpend": 5000,
    "ordersPlaced": 10
  },
  "cart": {
    "items": [
      {
        "productId": "p101",
        "category": "electronics",
        "unitPrice": 2000,
        "quantity": 1
      },
      {
        "productId": "p102",
        "category": "books",
        "unitPrice": 500,
        "quantity": 2
      }
    ]
  }
}
