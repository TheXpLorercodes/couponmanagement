import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from datetime import datetime, date


app = FastAPI(
    title="Coupon Management API",
    description="A simple coupon system for e-commerce use cases.",
    version="1.0.0"
)

# Data Models 

class Eligibility(BaseModel):
    allowedUserTiers: Optional[List[str]] = None  # ["NEW", "OLD"]
    minLifetimeSpend: Optional[float] = None
    minOrdersPlaced: Optional[int] = None
    firstOrderOnly: Optional[bool] = False
    allowedCountries: Optional[List[str]] = None
    minCartValue: Optional[float] = None
    applicableCategories: Optional[List[str]] = None # Valid if cart has at least one item from these
    excludedCategories: Optional[List[str]] = None   # Invalid if cart has any item from these
    minItemsCount: Optional[int] = None

class Coupon(BaseModel):
    code: str = Field(..., description="Unique coupon code")
    description: Optional[str] = None
    discountType: Literal["FLAT", "PERCENT"]
    discountValue: float
    maxDiscountAmount: Optional[float] = None # for percent
    startDate: date
    endDate: date
    usageLimitPerUser: Optional[int] = None
    eligibility: Optional[Eligibility] = Field(default_factory=Eligibility)

class CartItem(BaseModel):
    productId: str
    category: str
    unitPrice: float
    quantity: int

class Cart(BaseModel):
    items: List[CartItem]

    @property
    def total_value(self) -> float:
        return sum(item.unitPrice * item.quantity for item in self.items)

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def unique_categories(self) -> set:
        return {item.category for item in self.items}

class UserContext(BaseModel):
    userId: str
    userTier: Optional[str] = None # e.g. "NEW", "OLD"
    country: Optional[str] = None
    lifetimeSpend: Optional[float] = 0.0
    ordersPlaced: Optional[int] = 0

class BestCouponRequest(BaseModel):
    user: UserContext
    cart: Cart

class BestCouponResponse(BaseModel):
    couponCode: str
    discountAmount: float
    description: str

# In-Memory Storage 
# Using a dictionary 
COUPON_DB = {}


def check_eligibility(coupon: Coupon, user: UserContext, cart: Cart) -> bool:
    """
    Evaluates if a coupon is valid based on 2.2 Supported Eligibility Attributes.
    """
    rules = coupon.eligibility
    if not rules:
        return True

    
    if rules.allowedUserTiers and (user.userTier not in rules.allowedUserTiers):
        return False
    
    if rules.minLifetimeSpend and (user.lifetimeSpend < rules.minLifetimeSpend):
        return False
        
    if rules.minOrdersPlaced and (user.ordersPlaced < rules.minOrdersPlaced):
        return False
        
    if rules.firstOrderOnly and (user.ordersPlaced > 0):
        return False
        
    if rules.allowedCountries and (user.country not in rules.allowedCountries):
        return False

    
    if rules.minCartValue and (cart.total_value < rules.minCartValue):
        return False
        
    if rules.minItemsCount and (cart.total_items < rules.minItemsCount):
        return False
        
    cart_cats = cart.unique_categories
    
    # Valid if at least one item in cart is from these categories
    if rules.applicableCategories:
        if not any(cat in cart_cats for cat in rules.applicableCategories):
            return False
            

    if rules.excludedCategories:
        if any(cat in cart_cats for cat in rules.excludedCategories):
            return False

    return True

def calculate_discount(coupon: Coupon, cart_value: float) -> float:
    """Computes discount based on FLAT or PERCENT rules """
    if coupon.discountType == "FLAT":
        return min(coupon.discountValue, cart_value) # Cannot discount more than total price
    
    elif coupon.discountType == "PERCENT":
        discount = (coupon.discountValue / 100) * cart_value
        if coupon.maxDiscountAmount:
            discount = min(discount, coupon.maxDiscountAmount)
        return discount
    
    return 0.0

# API Endpoints 

@app.post("/coupons", status_code=201)
def create_coupon(coupon: Coupon):
    """
    4.1 Create Coupon API [cite: 74]
    Stores the coupon in memory.
    """
    if coupon.code in COUPON_DB:
        # Documented choice: Reject duplicates 
        raise HTTPException(status_code=400, detail=f"Coupon code '{coupon.code}' already exists.")
    
    COUPON_DB[coupon.code] = coupon
    return {"message": "Coupon created successfully", "code": coupon.code}

@app.get("/coupons")
def list_coupons():
    """Optional: Debug endpoint to view all coupons [cite: 78]"""
    return list(COUPON_DB.values())

@app.post("/best-coupon", response_model=Optional[BestCouponResponse])
def get_best_coupon(request: BestCouponRequest):
    """
    4.2 Best Coupon API [cite: 79]
    Evaluates all coupons and returns the best match.
    """
    user = request.user
    cart = request.cart
    today = date.today()
    
    eligible_coupons = []

    # Evaluate all coupons 
    for coupon in COUPON_DB.values():
        
        # Validity Dates 
        if not (coupon.startDate <= today <= coupon.endDate):
            continue
            
        # check Usage Limit 
        # if coupon.usageLimitPerUser and user_usage_count >= coupon.usageLimitPerUser: continue
        
        # Eligibility Criteria 
        if not check_eligibility(coupon, user, cart):
            continue
            
        # Compute Discount 
        discount_amount = calculate_discount(coupon, cart.total_value)
        
        eligible_coupons.append({
            "coupon": coupon,
            "discount": discount_amount
        })

    if not eligible_coupons:
        return None

    # Select Best Coupon 
    # Sort Rule 1: Highest discount amount (Descending)
    # Sort Rule 2: Earliest endDate (Ascending) 
    # Sort Rule 3: Lexicographically smaller code (Ascending) 
    
    best_match = sorted(
        eligible_coupons,
        key=lambda x: (
            -x["discount"],           # Max discount first (negative for desc)
            x["coupon"].endDate,      # Earliest date next
            x["coupon"].code          # A-Z code next
        )
    )[0]

    return BestCouponResponse(
        couponCode=best_match["coupon"].code,
        discountAmount=best_match["discount"],
        description=best_match["coupon"].description or ""
    )