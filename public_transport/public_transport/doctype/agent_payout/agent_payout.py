import frappe
from frappe.model.document import Document

class AgentPayout(Document):
    def validate(self):
        self.validate_amount()
        self.validate_agent()

    def validate_amount(self):
        if self.amount <= 0:
            frappe.throw("Payout amount must be greater than zero")

    def validate_agent(self):
        agent = frappe.get_doc("Booking Agent Settings", self.agent)
        if agent.status != "Active":
            frappe.throw("Cannot process payout for inactive agent")
        if self.amount < agent.minimum_payout_amount:
            frappe.throw(f"Amount {self.amount} is below minimum payout threshold of {agent.minimum_payout_amount}")

    def on_submit(self):
        try:
            # Here you would integrate with your payment gateway
            # For now, we'll just simulate the payment process
            self.process_payout()
        except Exception as e:
            self.status = "Failed"
            self.remarks = str(e)
            self.save()
            frappe.throw(f"Payout processing failed: {str(e)}")

    def process_payout(self):
        """Simulate payout processing"""
        agent = frappe.get_doc("Booking Agent Settings", self.agent)
        
        # Here you would integrate with actual payment gateway
        # For demonstration, we'll just mark it as processed
        self.status = "Processed"
        self.transaction_reference = frappe.generate_hash(length=12)
        self.remarks = f"Payout processed successfully to {agent.agent_name}"
        self.save()