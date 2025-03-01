# -*- coding: utf-8 -*-
# Copyright (c) 2023, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class BusRegistrationAudit(Document):
    def validate(self):
        if not self.audit_id:
            self.audit_id = frappe.generate_hash(length=10)
        self.validate_previous_registration()

    def validate_previous_registration(self):
        if not self.previous_registration:
            frappe.throw("Previous registration plate is required")
        
        if not self.change_timestamp:
            self.change_timestamp = frappe.utils.now_datetime()
