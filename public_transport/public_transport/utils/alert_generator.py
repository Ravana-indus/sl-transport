import frappe
from frappe.utils import now_datetime, add_to_date
import requests
from geopy.distance import geodesic


def get_weather_data(api_key, coordinates):
    """Get weather data for given coordinates"""
    weather_data = []
    
    for lat, lon in coordinates:
        response = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": lat,
                "lon": lon,
                "appid": api_key,
                "units": "metric"
            }
        )
        
        if response.status_code == 200:
            weather_data.append(response.json())
            
    return weather_data


def check_weather_conditions():
    """Check weather conditions and create alerts if needed"""
    try:
        # Get weather API settings
        settings = frappe.get_doc("Weather API Settings")
        if not settings.enabled:
            return
            
        # Get active routes
        routes = frappe.get_all(
            "Route",
            filters={"status": "Active"},
            fields=["name", "route_name"]
        )
        
        for route in routes:
            # Get route stops for weather checking
            stops = frappe.get_all(
                "Route Stop",
                filters={"parent": route.name},
                fields=["stop"]
            )
            
            if not stops:
                continue
                
            # Check weather at first and last stop
            first_stop = frappe.get_doc("Bus Stop", stops[0].stop)
            last_stop = frappe.get_doc("Bus Stop", stops[-1].stop)
            
            weather_data = get_weather_data(
                settings.api_key,
                [(first_stop.latitude, first_stop.longitude),
                 (last_stop.latitude, last_stop.longitude)]
            )
            
            if should_create_weather_alert(weather_data):
                create_weather_alert(route, weather_data)
    except Exception as e:
        frappe.log_error(f"Error checking weather conditions: {str(e)}", "Weather Alert Error")


def should_create_weather_alert(weather_data):
    """Determine if weather conditions warrant an alert"""
    severe_conditions = [
        "thunderstorm", "snow", "tornado", "hurricane",
        "extreme rain", "flood", "heavy snow"
    ]
    
    for data in weather_data:
        if not data:
            continue
            
        # Check for severe weather conditions
        weather_desc = data.get("weather", [{}])[0].get("description", "").lower()
        if any(condition in weather_desc for condition in severe_conditions):
            return True
            
        # Check for extreme temperatures
        temp = data.get("main", {}).get("temp")
        if temp and (temp > 40 or temp < 0):  # Celsius
            return True
            
        # Check for strong winds
        wind_speed = data.get("wind", {}).get("speed")
        if wind_speed and wind_speed > 20:  # m/s
            return True
            
    return False


def create_weather_alert(route, weather_data):
    """Create a weather-based service alert"""
    conditions = []
    for data in weather_data:
        if data:
            desc = data.get("weather", [{}])[0].get("description", "").title()
            temp = data.get("main", {}).get("temp")
            wind = data.get("wind", {}).get("speed")
            conditions.append(
                f"{desc}, Temperature: {temp}°C, Wind: {wind}m/s"
            )
    
    alert = frappe.get_doc({
        "doctype": "Service Alert",
        "alert_type": "Weather Warning",
        "severity": get_weather_severity(weather_data),
        "start_time": now_datetime(),
        "end_time": add_to_date(None, hours=6),  # 6-hour default duration
        "affected_routes": [{"route": route.name}],
        "affected_areas": route.route_name,
        "alert_message": (
            f"Adverse weather conditions affecting route {route.route_name}. "
            f"Conditions: {', '.join(conditions)}"
        ),
        "action_required": "Expect delays and drive with caution.",
        "notification_channels": "All Channels",
        "status": "Active"
    })
    
    alert.insert()
    alert.submit()


def get_weather_severity(weather_data):
    """Determine alert severity based on weather conditions"""
    for data in weather_data:
        if not data:
            continue
            
        weather_id = data.get("weather", [{}])[0].get("id", 0)
        
        # Standard weather condition codes
        if weather_id in [202, 212, 504, 511, 602, 762, 781]:  # Extreme conditions
            return "Critical"
        elif weather_id in [201, 211, 503, 601, 771]:  # Severe conditions
            return "High"
        elif weather_id in [200, 210, 502, 600, 741]:  # Moderate conditions
            return "Medium"
            
        # Check other parameters
        temp = data.get("main", {}).get("temp")
        wind_speed = data.get("wind", {}).get("speed")
        
        if temp > 45 or temp < -5 or wind_speed > 25:
            return "Critical"
        elif temp > 40 or temp < 0 or wind_speed > 20:
            return "High"
        elif temp > 35 or temp < 5 or wind_speed > 15:
            return "Medium"
    
    return "Low"


def check_traffic_incidents():
    """Check for traffic incidents and create alerts"""
    try:
        active_trips = frappe.get_all(
            "Bus Trip",
            filters={
                "departure_time": ["<=", now_datetime()],
                "arrival_time": [">", now_datetime()],
                "docstatus": 1
            },
            fields=["name", "bus", "route"]
        )
        
        for trip in active_trips:
            # Get recent GPS logs for the bus
            logs = frappe.get_all(
                "GPS Location Log",
                filters={"bus": trip.bus},
                fields=["latitude", "longitude", "timestamp"],
                order_by="timestamp desc",
                limit=10
            )
            
            if len(logs) < 2:
                continue
                
            # Calculate average speed
            distances = []
            times = []
            
            for i in range(len(logs) - 1):
                pos1 = (logs[i].latitude, logs[i].longitude)
                pos2 = (logs[i + 1].latitude, logs[i + 1].longitude)
                
                distance = geodesic(pos1, pos2).kilometers
                time_diff = (logs[i].timestamp - logs[i + 1].timestamp).total_seconds() / 3600  # hours
                
                if time_diff > 0:
                    distances.append(distance)
                    times.append(time_diff)
            
            if not distances or not times:
                continue
                
            avg_speed = sum(distances) / sum(times)
            
            # If average speed is very low, create traffic alert
            if avg_speed < 10:  # km/h
                create_traffic_alert(trip, avg_speed)
    except Exception as e:
        frappe.log_error(f"Error checking traffic incidents: {str(e)}", "Traffic Alert Error")


def create_traffic_alert(trip, speed):
    """Create a traffic-based service alert"""
    route = frappe.get_doc("Route", trip.route)
    
    alert = frappe.get_doc({
        "doctype": "Service Alert",
        "alert_type": "Traffic Delay",
        "severity": "High" if speed < 5 else "Medium",
        "start_time": now_datetime(),
        "end_time": add_to_date(None, hours=2),
        "affected_routes": [{"route": route.name}],
        "affected_areas": route.route_name,
        "alert_message": (
            f"Heavy traffic detected on route {route.route_name}. "
            f"Current average speed: {speed:.1f} km/h"
        ),
        "action_required": "Expect significant delays. Consider alternative routes.",
        "notification_channels": "All Channels",
        "status": "Active"
    })
    
    alert.insert()
    alert.submit()