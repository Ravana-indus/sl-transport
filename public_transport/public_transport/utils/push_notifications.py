import frappe
from frappe.utils import now_datetime
import json
import requests
from typing import List, Dict, Any, Optional

class PushNotificationManager:
    def __init__(self):
        self.settings = frappe.get_doc("Push Notification Settings")
        
    def send_alert_notification(self, alert: Dict[str, Any], recipients: List[str]) -> None:
        """Send push notification about service alert"""
        if not self.settings.enabled:
            return
            
        notification_data = {
            "title": f"Service Alert: {alert.alert_type}",
            "body": alert.alert_message,
            "data": {
                "type": "service_alert",
                "alert_id": alert.name,
                "severity": alert.severity,
                "route": alert.affected_routes[0].route if alert.affected_routes else None
            }
        }
        
        self._send_notification(notification_data, recipients)
    
    def send_deviation_notification(self, deviation: Dict[str, Any], bus_id: str) -> None:
        """Send push notification about route deviation"""
        if not self.settings.enabled:
            return
            
        # Get operator for this bus
        operators = frappe.get_all(
            "Bus Trip",
            filters={
                "bus": bus_id,
                "departure_time": ["<=", now_datetime()],
                "arrival_time": [">", now_datetime()]
            },
            fields=["bus_operator"]
        )
        
        if not operators:
            return
            
        notification_data = {
            "title": "Route Deviation Detected",
            "body": f"Your bus has deviated from the planned route. Check app for details.",
            "data": {
                "type": "route_deviation",
                "deviation_id": deviation.name,
                "bus_id": bus_id
            }
        }
        
        self._send_notification(notification_data, [operators[0].bus_operator])
    
    def send_weather_notification(self, conditions: Dict[str, Any], affected_routes: List[str]) -> None:
        """Send push notification about weather conditions"""
        if not self.settings.enabled:
            return
            
        # Get operators for affected routes
        operators = frappe.get_all(
            "Bus Trip",
            filters={
                "route": ["in", affected_routes],
                "departure_time": ["<=", now_datetime()],
                "arrival_time": [">", now_datetime()]
            },
            fields=["bus_operator"]
        )
        
        if not operators:
            return
            
        notification_data = {
            "title": "Weather Alert",
            "body": f"Adverse weather conditions affecting your route: {conditions['description']}",
            "data": {
                "type": "weather_alert",
                "conditions": conditions
            }
        }
        
        recipients = [op.bus_operator for op in operators]
        self._send_notification(notification_data, recipients)
    
    def _send_notification(self, notification_data: Dict[str, Any], recipients: List[str]) -> None:
        """Send push notification through configured provider"""
        try:
            if self.settings.provider == "Firebase":
                self._send_firebase_notification(notification_data, recipients)
            elif self.settings.provider == "OneSignal":
                self._send_onesignal_notification(notification_data, recipients)
            else:
                self._send_custom_notification(notification_data, recipients)
                
        except Exception as e:
            frappe.log_error(
                f"Push notification failed: {str(e)}\n"
                f"Data: {json.dumps(notification_data)}\n"
                f"Recipients: {json.dumps(recipients)}"
            )
    
    def _send_firebase_notification(self, notification_data: Dict[str, Any], recipients: List[str]) -> None:
        """Send notification through Firebase Cloud Messaging"""
        # Get device tokens for recipients
        tokens = self._get_device_tokens(recipients)
        if not tokens:
            return
            
        headers = {
            "Authorization": f"key={self.settings.get_password('firebase_server_key')}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "notification": {
                "title": notification_data["title"],
                "body": notification_data["body"]
            },
            "data": notification_data["data"],
            "registration_ids": tokens
        }
        
        response = requests.post(
            "https://fcm.googleapis.com/fcm/send",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Firebase request failed: {response.text}")
    
    def _send_onesignal_notification(self, notification_data: Dict[str, Any], recipients: List[str]) -> None:
        """Send notification through OneSignal"""
        headers = {
            "Authorization": f"Basic {self.settings.get_password('onesignal_rest_api_key')}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "app_id": self.settings.onesignal_app_id,
            "headings": {"en": notification_data["title"]},
            "contents": {"en": notification_data["body"]},
            "data": notification_data["data"],
            "include_external_user_ids": recipients
        }
        
        response = requests.post(
            "https://onesignal.com/api/v1/notifications",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"OneSignal request failed: {response.text}")
    
    def _send_custom_notification(self, notification_data: Dict[str, Any], recipients: List[str]) -> None:
        """Send notification through custom provider"""
        if not self.settings.custom_endpoint:
            raise Exception("Custom endpoint not configured")
            
        response = requests.post(
            self.settings.custom_endpoint,
            headers={"Authorization": f"Bearer {self.settings.get_password('custom_api_key')}"},
            json={
                "notification": notification_data,
                "recipients": recipients
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Custom provider request failed: {response.text}")
    
    def _get_device_tokens(self, user_ids: List[str]) -> List[str]:
        """Get device tokens for given users"""
        tokens = []
        for user_id in user_ids:
            device_tokens = frappe.get_all(
                "Push Notification Device",
                filters={
                    "user": user_id,
                    "enabled": 1
                },
                fields=["token"]
            )
            tokens.extend([d.token for d in device_tokens])
        return tokens