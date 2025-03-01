from . import __version__ as app_version

app_name = "public_transport"
app_title = "Public Transport"
app_publisher = "Patu"
app_description = "Public Transport Management System"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "patu@example.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
    "/assets/public_transport/css/public_transport.css",
    "/assets/public_transport/css/tracking.css",
    "/assets/public_transport/css/notifications.css"
]
app_include_js = [
    "/assets/public_transport/js/realtime_handlers.js",
    "/assets/public_transport/js/notification_handlers.js"
]

# Web Include JS
web_include_js = [
    "/assets/public_transport/js/booking_interface.js",
    "https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY"
]

# Custom DocTypes
# --------------
fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", [
            "Bus Operator",
            "Bus Conductor",
            "Booking Agent",
            "Regular User"
        ]]]
    },
    {
        "dt": "Custom Field",
        "filters": [["dt", "in", [
            "Bus",
            "Bus Trip",
            "Booking",
            "Payment",
            "Booking Agent Settings"
        ]]]
    }
]

# Document Events
# --------------
doc_events = {
    "Booking": {
        "on_update": "public_transport.public_transport.doctype.booking.booking.on_update",
        "on_submit": [
            "public_transport.public_transport.doctype.booking.booking.on_submit",
            "public_transport.public_transport.utils.sms_service.send_booking_confirmation"
        ]
    },
    "Payment": {
        "on_submit": "public_transport.public_transport.doctype.payment.payment.on_submit"
    },
    "SMS Log": {
        "after_insert": "public_transport.public_transport.utils.sms_service.process_sms_queue"
    },
    "GPS Location Log": {
        "after_insert": "public_transport.public_transport.utils.gps_tracking.update_bus_location"
    }
}

# Scheduled Tasks
# -------------
scheduler_events = {
    "daily": [
        "public_transport.public_transport.commands.process_agent_payouts",
        "public_transport.public_transport.commands.send_trip_reminders",
        "public_transport.public_transport.commands.cleanup_gps_logs",
        "public_transport.public_transport.utils.notification_analytics.NotificationAnalytics.generate_daily_report"
    ],
    "hourly": [
        "public_transport.public_transport.commands.cleanup_expired_seat_locks"
    ],
    "weekly": [
        "public_transport.public_transport.doctype.booking_agent_settings.booking_agent_settings.process_weekly_payouts"
    ],
    "monthly": [
        "public_transport.public_transport.doctype.booking_agent_settings.booking_agent_settings.process_monthly_payouts"
    ],
    "all": [
        "public_transport.public_transport.utils.sms_service.process_sms_queue",
        "public_transport.public_transport.utils.alert_generator.check_weather_conditions",
        "public_transport.public_transport.utils.alert_generator.check_traffic_incidents"
    ],
    "cron": {
        "*/15 * * * *": [  # Every 15 minutes
            "public_transport.public_transport.utils.notification_analytics.update_notification_metrics"
        ]
    }
}

# Additional app-specific hooks

app_initialization = [
    "public_transport.public_transport.utils.notification_analytics.schedule_analytics_report"
]

# Authentication and authorization
# -----------------------------
has_permission = {
    "Bus Trip": "public_transport.public_transport.doctype.bus_trip.bus_trip.has_permission",
    "Booking": "public_transport.public_transport.doctype.booking.booking.has_permission"
}

# API Endpoints
# -----------------------------
api_version = 1

# Boot Info
# -----------------------------
boot_session = "public_transport.api.boot_session"

# Website Generators
# ------------------
website_generators = ["Bus Trip"]

# Website Route Rules
# ------------------
website_route_rules = [
    {"from_route": "/book/<trip_id>", "to_route": "www/book_trip"},
    {"from_route": "/booking/<booking_id>", "to_route": "www/view_booking"}
]

# Portal Menu Items
# ----------------
portal_menu_items = [
    {"title": "My Bookings", "route": "/bookings", "role": "Regular User"}
]
