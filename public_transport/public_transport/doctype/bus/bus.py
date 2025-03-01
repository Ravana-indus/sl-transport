# -*- coding: utf-8 -*-
# Copyright (c) 2023, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class Bus(Document):
    def validate(self):
        # Custom validations for the Bus doctype
        self.validate_registration_plate()
        
    def validate_registration_plate(self):
        """Ensure registration plate is unique"""
        if self.registration_plate:
            # Check if registration plate exists on another bus
            existing = frappe.db.get_value("Bus", 
                {"registration_plate": self.registration_plate, "name": ["!=", self.name]}, 
                "name")
            
            if existing:
                frappe.throw(_("Registration Plate '{0}' already exists on Bus {1}").format(
                    self.registration_plate, existing))
                
    def on_update(self):
        """Check if registration plate changed and update audit trail"""
        if self.has_value_changed("registration_plate") and self.get_doc_before_save():
            previous_plate = self.get_doc_before_save().registration_plate
            
            # Create audit entry for registration plate change
            audit_entry = {
                "audit_id": frappe.utils.now(),
                "previous_registration": previous_plate,
                "change_timestamp": frappe.utils.now(),
                "reason": "Registration plate updated via system"
            }
            
            self.append("registration_audit", audit_entry)
    
    def before_save(self):
        if self.is_new():
            self.internal_bus_id = self.name
        elif self.has_value_changed('registration_plate'):
            # Create registration audit entry
            self.append('registration_audit', {
                'audit_id': frappe.generate_hash(length=10),
                'previous_registration': self.get_doc_before_save().registration_plate,
                'change_timestamp': frappe.utils.now_datetime(),
                'reason': 'Registration plate changed'
            })
