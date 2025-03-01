import frappe
from frappe.model.document import Document
from datetime import datetime

class SMSLog(Document):
    def validate(self):
        if not self.phone or len(self.phone) < 10:
            frappe.throw("Invalid phone number")
            
    def send_sms(self):
        try:
            # TODO: Integrate with actual SMS gateway
            # This is a placeholder for SMS gateway integration
            # For now, we'll simulate sending
            self.status = "Sent"
            self.sent_time = datetime.now()
            self.save()
            
            # Notify any listening clients
            frappe.publish_realtime(
                'sms_status_update',
                {
                    'sms_id': self.name,
                    'status': self.status
                }
            )
        except Exception as e:
            self.status = "Failed"
            self.error_message = str(e)
            self.save()
            frappe.log_error(f"SMS sending failed: {str(e)}")