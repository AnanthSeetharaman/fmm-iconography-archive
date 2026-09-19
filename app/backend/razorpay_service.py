import razorpay
from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

# Initialize Razorpay Client
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_subscription_order(amount_inr: float, user_id: str) -> dict:
    """
    Creates a Razorpay order for a Scholar Pro subscription.
    Amount should be in INR (rupees).
    """
    if not razorpay_client:
        return {"error": "Razorpay credentials not configured."}
        
    # Razorpay expects amount in paise (1 INR = 100 paise)
    amount_paise = int(amount_inr * 100)
    
    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"receipt_{user_id}_{int(amount_inr)}",
        "notes": {
            "user_id": user_id,
            "tier": "scholar_pro"
        }
    }
    
    try:
        order = razorpay_client.order.create(data=order_data)
        return order
    except Exception as e:
        return {"error": str(e)}

def verify_payment_signature(payment_id: str, order_id: str, signature: str) -> bool:
    """
    Verifies the Razorpay payment signature.
    """
    if not razorpay_client:
        return False
        
    try:
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        return razorpay_client.utility.verify_payment_signature(params_dict)
    except Exception:
        return False
