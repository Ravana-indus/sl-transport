import frappe
from frappe.model.document import Document

class BookingAgentSettings(Document):
    def validate(self):
        self.validate_commission()
        self.validate_user()
        if self.is_new():
            self.agent_id = self.name

    def validate_commission(self):
        if self.commission_percentage <= 0 or self.commission_percentage >= 100:
            frappe.throw("Commission percentage must be between 0 and 100")
        
        if self.minimum_payout_amount <= 0:
            frappe.throw("Minimum payout amount must be greater than zero")

    def validate_user(self):
        # Check if user has appropriate role
        user = frappe.get_doc("User", self.user)
        if not frappe.db.exists("Has Role", {"parent": self.user, "role": "Booking Agent"}):
            frappe.get_doc({
                "doctype": "Has Role",
                "parent": self.user,
                "parentfield": "roles",
                "parenttype": "User",
                "role": "Booking Agent"
            }).insert()

    def on_update(self):
        if self.has_value_changed('status') and self.status == 'Inactive':
            # Handle any pending payouts or commissions
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Booking Agent Settings",
                "reference_name": self.name,
                "content": f"Agent {self.agent_name} status changed to Inactive"
            }).insert()

def process_daily_payouts():
    """Process payouts for agents with daily payout frequency"""
    process_payouts("Daily")

def process_weekly_payouts():
    """Process payouts for agents with weekly payout frequency"""
    process_payouts("Weekly")

def process_monthly_payouts():
    """Process payouts for agents with monthly payout frequency"""
    process_payouts("Monthly")

def process_payouts(frequency):
    """Common function to process payouts based on frequency"""
    agents = frappe.get_all(
        "Booking Agent Settings",
        filters={
            "status": "Active",
            "payout_frequency": frequency
        },
        fields=["name", "agent_name", "minimum_payout_amount"]
    )
    
    for agent in agents:
        # Get all successful payments with unpaid commissions
        payments = frappe.get_all(
            "Payment",
            filters={
                "transaction_status": "Success",
                "commission_paid": 0,
                "booking_agent": agent.name
            },
            fields=["name", "amount", "commission_amount"]
        )
        
        total_commission = sum(p.commission_amount for p in payments)
        
        if total_commission >= agent.minimum_payout_amount:
            # Create payout record
            payout = frappe.get_doc({
                "doctype": "Agent Payout",
                "agent": agent.name,
                "amount": total_commission,
                "payout_date": frappe.utils.now_datetime(),
                "status": "Pending"
            })
            payout.insert()
            
            # Mark commissions as paid
            for payment in payments:
                frappe.db.set_value("Payment", payment.name, "commission_paid", 1)
            
            frappe.db.commit()