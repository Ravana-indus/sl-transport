import frappe
import json
from frappe import _
from frappe.utils import now_datetime
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import requests

def process_card_payment(payment_doc):
    """Process card payment through payment gateway"""
    try:
        # Get gateway configuration
        gateway_settings = frappe.get_doc("Payment Gateway Settings")
        
        # Prepare payment data
        payment_data = {
            "amount": payment_doc.amount,
            "currency": "LKR",
            "payment_id": payment_doc.name,
            "merchant_id": gateway_settings.merchant_id,
            "order_id": payment_doc.booking
        }
        
        # Encrypt sensitive data
        encrypted_data = encrypt_payment_data(payment_data, gateway_settings.public_key)
        
        # Make API call to payment gateway
        response = requests.post(
            gateway_settings.api_endpoint,
            json={
                "merchant_id": gateway_settings.merchant_id,
                "payment_data": encrypted_data
            },
            headers={
                "Authorization": f"Bearer {gateway_settings.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                payment_doc.transaction_status = "Success"
                payment_doc.transaction_reference = result.get("transaction_id")
                payment_doc.save()
                return {"status": "success", "transaction_id": result.get("transaction_id")}
        
        payment_doc.transaction_status = "Failed"
        payment_doc.save()
        return {"status": "error", "message": "Payment processing failed"}
        
    except Exception as e:
        payment_doc.transaction_status = "Failed"
        payment_doc.save()
        frappe.log_error(f"Payment Processing Failed: {str(e)}")
        return {"status": "error", "message": str(e)}

def process_nfc_payment(payment_doc, nfc_data):
    """Process NFC card payment"""
    try:
        # Validate NFC data
        if not validate_nfc_data(nfc_data):
            raise ValueError("Invalid NFC data")
            
        # Process payment similar to card payment
        return process_card_payment(payment_doc)
        
    except Exception as e:
        payment_doc.transaction_status = "Failed"
        payment_doc.save()
        frappe.log_error(f"NFC Payment Failed: {str(e)}")
        return {"status": "error", "message": str(e)}

def validate_nfc_data(nfc_data):
    """Validate NFC card data"""
    try:
        data = json.loads(nfc_data)
        required_fields = ["card_token", "timestamp", "device_id"]
        return all(field in data for field in required_fields)
    except:
        return False

def encrypt_payment_data(data, public_key):
    """Encrypt sensitive payment data"""
    try:
        key = RSA.import_key(public_key)
        cipher = PKCS1_OAEP.new(key)
        encrypted_data = cipher.encrypt(json.dumps(data).encode())
        return encrypted_data.hex()
    except Exception as e:
        frappe.log_error(f"Encryption Failed: {str(e)}")
        raise