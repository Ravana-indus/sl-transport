import frappe
from frappe.model.document import Document

class SeatMap(Document):
    def validate(self):
        self.validate_seat_id()
        self.validate_row_column()

    def validate_seat_id(self):
        """Ensure seat ID follows the pattern [Side Initial][Row Number]"""
        if not self.seat_id:
            return

        valid_prefix = {"R": "Right", "L": "Left"}
        prefix = self.seat_id[0].upper()
        
        if prefix not in valid_prefix or valid_prefix[prefix] != self.side:
            frappe.throw(f"Seat ID must start with 'R' for Right side or 'L' for Left side")

    def validate_row_column(self):
        """Validate row and column identifiers"""
        if not self.row_identifier or not self.column_identifier:
            frappe.throw("Row and Column identifiers are required")