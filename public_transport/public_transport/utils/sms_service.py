import frappe
import requests
from frappe.utils import now_datetime

class SMSProvider:
    def __init__(self):
        self.settings = frappe.get_doc("SMS Settings")
        self.api_endpoint = self.settings.sms_gateway_url
        self.api_key = self.settings.api_key
        self.sender_id = self.settings.sender_id

    def send_message(self, phone_number, message):
        """Send SMS through configured gateway"""
        try:
            response = requests.post(
                self.api_endpoint,
                json={
                    "recipient": phone_number,
                    "message": message,
                    "sender_id": self.sender_id
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    return True, result.get("message_id")
            
            return False, response.text
            
        except Exception as e:
            frappe.log_error(f"SMS Sending Failed: {str(e)}")
            return False, str(e)

def process_sms_queue():
    """Process pending SMS in queue"""
    sms_provider = SMSProvider()
    
    # Get queued messages
    pending_messages = frappe.get_all(
        "SMS Log",
        filters={"status": "Queued"},
        fields=["name", "message", "phone"]
    )
    
    for sms in pending_messages:
        try:
            success, result = sms_provider.send_message(
                sms.phone,
                sms.message
            )
            
            if success:
                frappe.db.set_value("SMS Log", sms.name, {
                    "status": "Sent",
                    "sent_time": now_datetime()
                })
            else:
                frappe.db.set_value("SMS Log", sms.name, {
                    "status": "Failed",
                    "error_message": result
                })
                
        except Exception as e:
            frappe.db.set_value("SMS Log", sms.name, {
                "status": "Failed",
                "error_message": str(e)
            })
            
        frappe.db.commit()

def send_booking_confirmation(booking_id):
    """Send booking confirmation SMS"""
    try:
        booking = frappe.get_doc("Booking", booking_id)
        trip = frappe.get_doc("Bus Trip", booking.bus_trip)
        
        message = (
            f"Booking Confirmed!\n"
            f"Booking ID: {booking.name}\n"
            f"Route: {trip.route}\n"
            f"Date: {trip.departure_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Seats: {', '.join(s.seat_id for s in booking.selected_seats)}"
        )
        
        frappe.get_doc({
            "doctype": "SMS Log",
            "message": message,
            "phone": booking.passenger_contact,
            "status": "Queued"
        }).insert()
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Booking Confirmation SMS Failed: {str(e)}")
        return False

def send_trip_reminder(booking_id):
    """Send trip reminder SMS"""
    try:
        booking = frappe.get_doc("Booking", booking_id)
        trip = frappe.get_doc("Bus Trip", booking.bus_trip)
        
        message = (
            f"Trip Reminder!\n"
            f"Your trip {trip.route} is scheduled for tomorrow at "
            f"{trip.departure_time.strftime('%H:%M')}.\n"
            f"Booking ID: {booking.name}"
        )
        
        frappe.get_doc({
            "doctype": "SMS Log",
            "message": message,
            "phone": booking.passenger_contact,
            "status": "Queued"
        }).insert()
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Trip Reminder SMS Failed: {str(e)}")
        return False