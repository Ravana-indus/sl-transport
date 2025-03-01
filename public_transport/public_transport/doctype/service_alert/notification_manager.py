import frappe
from frappe.utils import now_datetime
from ...utils.push_notifications import PushNotificationManager

class ServiceAlertNotificationManager:
    def __init__(self, alert_doc):
        self.alert = alert_doc
        self.push_manager = PushNotificationManager()
        
    def notify_all_channels(self):
        """Send notifications through all configured channels"""
        if not self.alert.notification_channels:
            return
            
        channels = (self.alert.notification_channels.split('\n') 
                   if self.alert.notification_channels != "All Channels"
                   else ["SMS", "Email", "App Notification"])
        
        affected_parties = self.get_affected_parties()
        
        if "App Notification" in channels:
            self.send_push_notifications(affected_parties)
        if "SMS" in channels:
            self.send_sms_notifications(affected_parties)
        if "Email" in channels:
            self.send_email_notifications(affected_parties)
            
    def get_affected_parties(self):
        """Get list of affected passengers and operators"""
        affected = {
            "passengers": [],
            "operators": [],
            "agents": []
        }
        
        if not self.alert.affected_routes:
            return affected
            
        route_list = [r.route for r in self.alert.affected_routes]
        
        # Get active trips during alert period
        trips = frappe.get_all(
            "Bus Trip",
            filters={
                "route": ["in", route_list],
                "departure_time": ["between", (self.alert.start_time, self.alert.end_time)],
                "docstatus": 1
            },
            fields=["name", "bus_operator"]
        )
        
        # Collect unique operators
        operators = set(trip.bus_operator for trip in trips if trip.bus_operator)
        affected["operators"].extend(list(operators))
        
        # Get bookings for these trips
        for trip in trips:
            bookings = frappe.get_all(
                "Booking",
                filters={
                    "bus_trip": trip.name,
                    "booking_status": "Confirmed"
                },
                fields=["passenger_name", "passenger_contact", "booking_agent"]
            )
            
            for booking in bookings:
                affected["passengers"].append({
                    "name": booking.passenger_name,
                    "contact": booking.passenger_contact
                })
                
                if booking.booking_agent:
                    affected["agents"].append(booking.booking_agent)
        
        # Remove duplicates
        affected["agents"] = list(set(affected["agents"]))
        affected["passengers"] = [dict(t) for t in {tuple(d.items()) for d in affected["passengers"]}]
        
        return affected
    
    def send_push_notifications(self, affected_parties):
        """Send push notifications to all affected parties"""
        try:
            # Notify operators
            if affected_parties["operators"]:
                self.push_manager.send_alert_notification(
                    self.alert,
                    affected_parties["operators"]
                )
            
            # Notify booking agents
            if affected_parties["agents"]:
                self.create_agent_notification(affected_parties["agents"])
            
            # Notify passengers (if they have the app)
            passenger_users = []
            for passenger in affected_parties["passengers"]:
                user = frappe.get_all(
                    "User",
                    filters={"mobile_no": passenger["contact"]},
                    fields=["name"]
                )
                if user:
                    passenger_users.append(user[0].name)
            
            if passenger_users:
                self.push_manager.send_alert_notification(
                    self.alert,
                    passenger_users
                )
                
        except Exception as e:
            frappe.log_error(f"Push notification failed: {str(e)}")
    
    def send_sms_notifications(self, affected_parties):
        """Send SMS notifications to affected parties"""
        try:
            message = self.create_sms_content()
            
            # Send to passengers
            for passenger in affected_parties["passengers"]:
                if passenger["contact"]:
                    frappe.get_doc({
                        "doctype": "SMS Log",
                        "message": message,
                        "phone": passenger["contact"],
                        "status": "Queued"
                    }).insert()
            
            # Send to operators
            for operator in affected_parties["operators"]:
                phone = frappe.db.get_value("User", operator, "mobile_no")
                if phone:
                    frappe.get_doc({
                        "doctype": "SMS Log",
                        "message": self.create_operator_sms_content(),
                        "phone": phone,
                        "status": "Queued"
                    }).insert()
                    
        except Exception as e:
            frappe.log_error(f"SMS notification failed: {str(e)}")
    
    def send_email_notifications(self, affected_parties):
        """Send email notifications to affected parties"""
        try:
            for group in ["operators", "agents"]:
                for user in affected_parties[group]:
                    email = frappe.db.get_value("User", user, "email")
                    if email:
                        self.send_email_alert(email, user)
                        
            # Send to passengers who have email registered
            for passenger in affected_parties["passengers"]:
                user = frappe.get_all(
                    "User",
                    filters={"mobile_no": passenger["contact"]},
                    fields=["email"]
                )
                if user and user[0].email:
                    self.send_email_alert(user[0].email, passenger["name"])
                    
        except Exception as e:
            frappe.log_error(f"Email notification failed: {str(e)}")
    
    def create_sms_content(self):
        """Create SMS content for passengers"""
        return f"""
Service Alert: {self.alert.alert_type}
Severity: {self.alert.severity}
{self.alert.alert_message}
Duration: {self.alert.start_time.strftime('%H:%M')} - {self.alert.end_time.strftime('%H:%M')}
{self.alert.action_required if self.alert.action_required else ''}
        """.strip()
    
    def create_operator_sms_content(self):
        """Create SMS content for operators"""
        return f"""
OPERATOR ALERT: {self.alert.alert_type}
Severity: {self.alert.severity}
{self.alert.alert_message}
Areas: {self.alert.affected_areas}
Duration: {self.alert.start_time.strftime('%H:%M')} - {self.alert.end_time.strftime('%H:%M')}
Action: {self.alert.action_required if self.alert.action_required else 'Follow standard procedures'}
        """.strip()
    
    def create_agent_notification(self, agent_list):
        """Create in-app notifications for booking agents"""
        for agent in agent_list:
            frappe.get_doc({
                "doctype": "User Notification",
                "user": agent,
                "type": "Service Alert",
                "subject": f"Service Alert: {self.alert.alert_type}",
                "message": self.alert.alert_message,
                "status": "Unread",
                "timestamp": now_datetime()
            }).insert()
    
    def send_email_alert(self, email, recipient_name):
        """Send email notification"""
        subject = f"Service Alert: {self.alert.alert_type} - {self.alert.severity} Severity"
        
        message = frappe.render_template(
            "templates/emails/service_alert.html",
            {
                "alert": self.alert,
                "passenger": {"name": recipient_name}
            }
        )
        
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message
        )