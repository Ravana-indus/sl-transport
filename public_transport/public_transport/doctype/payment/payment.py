import frappe
from frappe.model.document import Document

class Payment(Document):
    def validate(self):
        self.validate_amount()
        self.validate_payment_type()
        if self.is_new():
            self.payment_time = frappe.utils.now_datetime()

    def validate_amount(self):
        if self.amount <= 0:
            frappe.throw("Payment amount must be greater than zero")

    def validate_payment_type(self):
        booking = frappe.get_doc("Booking", self.booking)
        if self.payment_type != booking.payment_mode:
            frappe.throw(f"Payment type must match booking payment mode: {booking.payment_mode}")

    def on_submit(self):
        if self.transaction_status == "Success":
            # Update booking status
            booking = frappe.get_doc("Booking", self.booking)
            booking.booking_status = "Confirmed"
            booking.save()

            # Handle booking agent commission if applicable
            if booking.booking_agent:
                self.process_agent_commission(booking)

    def process_agent_commission(self, booking):
        agent = frappe.get_doc("Booking Agent Settings", booking.booking_agent)
        if agent.status == "Active":
            commission_amount = self.amount * (agent.commission_percentage / 100)
            # TODO: Create commission ledger entry
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Payment",
                "reference_name": self.name,
                "content": f"Commission of {commission_amount} calculated for agent {agent.agent_name}"
            }).insert()