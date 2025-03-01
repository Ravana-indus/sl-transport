import frappe
from frappe.model.document import Document

class GPSLocationLog(Document):
    def validate(self):
        self.validate_coordinates()
        
    def validate_coordinates(self):
        if not -90 <= self.latitude <= 90:
            frappe.throw("Latitude must be between -90 and 90 degrees")
        if not -180 <= self.longitude <= 180:
            frappe.throw("Longitude must be between -180 and 180 degrees")
            
    def after_insert(self):
        """Notify subscribed clients about location update"""
        frappe.publish_realtime(
            'gps_update',
            {
                'bus': self.bus,
                'latitude': self.latitude,
                'longitude': self.longitude,
                'timestamp': str(self.timestamp)
            }
        )