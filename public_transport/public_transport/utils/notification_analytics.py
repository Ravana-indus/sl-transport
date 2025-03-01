import frappe
from frappe.utils import add_days, getdate, now_datetime
from collections import defaultdict
from typing import Dict, List, Any

class NotificationAnalytics:
    def __init__(self):
        self.metrics = defaultdict(int)
        
    def track_notification_sent(self, notification_type: str, channel: str) -> None:
        """Track a notification being sent"""
        self._increment_metric(f"sent_{notification_type}_{channel}")
        self._increment_metric("total_sent")
        
    def track_notification_delivered(self, notification_type: str, channel: str) -> None:
        """Track a notification being delivered"""
        self._increment_metric(f"delivered_{notification_type}_{channel}")
        self._increment_metric("total_delivered")
        
    def track_notification_opened(self, notification_type: str, channel: str) -> None:
        """Track a notification being opened/read"""
        self._increment_metric(f"opened_{notification_type}_{channel}")
        self._increment_metric("total_opened")
        
    def track_notification_action(self, notification_type: str, action: str) -> None:
        """Track user action taken on notification"""
        self._increment_metric(f"action_{notification_type}_{action}")
        self._increment_metric("total_actions")
    
    def _increment_metric(self, metric_key: str) -> None:
        """Increment a metric in Redis"""
        date_key = getdate().strftime("%Y-%m-%d")
        redis_key = f"notification_metrics:{date_key}:{metric_key}"
        
        frappe.cache().incr(redis_key)
    
    @staticmethod
    def get_daily_metrics(days: int = 7) -> Dict[str, Any]:
        """Get notification metrics for the last n days"""
        metrics = defaultdict(lambda: defaultdict(int))
        
        for i in range(days):
            date = add_days(getdate(), -i)
            date_key = date.strftime("%Y-%m-%d")
            
            # Get all metrics for this date
            keys = frappe.cache().get_keys(f"notification_metrics:{date_key}:*")
            
            for key in keys:
                metric_name = key.split(":")[-1]
                value = frappe.cache().get_value(key) or 0
                metrics[date_key][metric_name] = value
        
        return dict(metrics)
    
    @staticmethod
    def get_channel_effectiveness() -> Dict[str, float]:
        """Calculate effectiveness of different notification channels"""
        channels = ["SMS", "Email", "App Notification"]
        effectiveness = {}
        
        for channel in channels:
            sent = frappe.cache().get_value(f"notification_metrics:{getdate()}:sent_total_{channel}") or 0
            delivered = frappe.cache().get_value(f"notification_metrics:{getdate()}:delivered_total_{channel}") or 0
            opened = frappe.cache().get_value(f"notification_metrics:{getdate()}:opened_total_{channel}") or 0
            
            if sent > 0:
                delivery_rate = (delivered / sent) * 100
                open_rate = (opened / delivered) * 100 if delivered > 0 else 0
                
                effectiveness[channel] = {
                    "delivery_rate": round(delivery_rate, 2),
                    "open_rate": round(open_rate, 2)
                }
            else:
                effectiveness[channel] = {
                    "delivery_rate": 0,
                    "open_rate": 0
                }
        
        return effectiveness
    
    @staticmethod
    def get_alert_type_engagement() -> Dict[str, Dict[str, float]]:
        """Calculate engagement metrics for different alert types"""
        alert_types = ["service_alert", "route_deviation", "weather_alert"]
        engagement = {}
        
        for alert_type in alert_types:
            sent = frappe.cache().get_value(f"notification_metrics:{getdate()}:sent_{alert_type}_total") or 0
            opened = frappe.cache().get_value(f"notification_metrics:{getdate()}:opened_{alert_type}_total") or 0
            actions = frappe.cache().get_value(f"notification_metrics:{getdate()}:action_{alert_type}_total") or 0
            
            if sent > 0:
                engagement[alert_type] = {
                    "open_rate": round((opened / sent) * 100, 2),
                    "action_rate": round((actions / sent) * 100, 2)
                }
            else:
                engagement[alert_type] = {
                    "open_rate": 0,
                    "action_rate": 0
                }
        
        return engagement
    
    @staticmethod
    def generate_daily_report() -> None:
        """Generate and store daily notification report"""
        today = getdate()
        
        # Get today's metrics
        metrics = NotificationAnalytics.get_daily_metrics(1)[today.strftime("%Y-%m-%d")]
        effectiveness = NotificationAnalytics.get_channel_effectiveness()
        engagement = NotificationAnalytics.get_alert_type_engagement()
        
        report = frappe.get_doc({
            "doctype": "Notification Analytics Report",
            "date": today,
            "total_notifications_sent": metrics.get("total_sent", 0),
            "total_notifications_delivered": metrics.get("total_delivered", 0),
            "total_notifications_opened": metrics.get("total_opened", 0),
            "total_actions_taken": metrics.get("total_actions", 0),
            "channel_effectiveness": effectiveness,
            "alert_type_engagement": engagement
        })
        
        report.insert()

def update_notification_metrics(notification_type: str, event_type: str, channel: str = None) -> None:
    """Update notification metrics based on events"""
    analytics = NotificationAnalytics()
    
    if event_type == "sent":
        analytics.track_notification_sent(notification_type, channel)
    elif event_type == "delivered":
        analytics.track_notification_delivered(notification_type, channel)
    elif event_type == "opened":
        analytics.track_notification_opened(notification_type, channel)
    elif event_type.startswith("action_"):
        analytics.track_notification_action(notification_type, event_type.split("_")[1])

def schedule_analytics_report() -> None:
    """Schedule daily analytics report generation"""
    if not frappe.flags.in_test:
        try:
            # Generate report at end of day
            report_time = now_datetime().replace(
                hour=23, minute=59, second=0, microsecond=0
            )
            
            # Add to scheduler
            frappe.get_doc({
                "doctype": "Scheduled Job Type",
                "method": "public_transport.public_transport.utils.notification_analytics.NotificationAnalytics.generate_daily_report",
                "frequency": "Daily",
                "next_execution": report_time,
                "server_script": 0
            }).insert()
            
        except Exception as e:
            frappe.log_error("Failed to schedule analytics report")