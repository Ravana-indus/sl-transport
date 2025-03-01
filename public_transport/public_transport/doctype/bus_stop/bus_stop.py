import frappe
from frappe.model.document import Document

class BusStop(Document):
    def validate(self):
        self.validate_coordinates()
        self.validate_facilities()
    
    def validate_coordinates(self):
        """Validate latitude and longitude"""
        if not -90 <= self.latitude <= 90:
            frappe.throw("Latitude must be between -90 and 90 degrees")
        if not -180 <= self.longitude <= 180:
            frappe.throw("Longitude must be between -180 and 180 degrees")
    
    def validate_facilities(self):
        """Ensure no duplicate facilities"""
        if self.facilities:
            facility_types = []
            for facility in self.facilities:
                if facility.facility_type in facility_types:
                    frappe.throw(f"Duplicate facility type: {facility.facility_type}")
                facility_types.append(facility.facility_type)
    
    def on_update(self):
        """Update all routes using this stop"""
        routes = frappe.get_all(
            "Route Stop",
            filters={"stop": self.name},
            fields=["parent"]
        )
        
        for route in routes:
            frappe.get_doc("Route", route.parent).save()