import frappe
from frappe.model.document import Document
import requests

class WeatherAPISettings(Document):
    def validate(self):
        self.validate_thresholds()
        if self.enabled:
            self.test_api_connection()
    
    def validate_thresholds(self):
        """Validate temperature and wind thresholds"""
        if self.high_temp_threshold <= self.low_temp_threshold:
            frappe.throw("High temperature threshold must be greater than low temperature threshold")
        
        if self.high_wind_threshold < 0:
            frappe.throw("Wind threshold cannot be negative")
            
        if self.default_duration <= 0:
            frappe.throw("Alert duration must be positive")
    
    def test_api_connection(self):
        """Test connection to weather API"""
        try:
            # Use Colombo coordinates as test location
            test_coords = (6.9271, 79.8612)
            
            if self.provider == "OpenWeatherMap":
                response = requests.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "lat": test_coords[0],
                        "lon": test_coords[1],
                        "appid": self.get_password("api_key"),
                        "units": "metric"
                    }
                )
            elif self.provider == "WeatherAPI":
                response = requests.get(
                    "https://api.weatherapi.com/v1/current.json",
                    params={
                        "key": self.get_password("api_key"),
                        "q": f"{test_coords[0]},{test_coords[1]}"
                    }
                )
            else:  # Custom provider
                if not self.api_endpoint:
                    frappe.throw("API endpoint is required for custom provider")
                    
                response = requests.get(
                    self.api_endpoint,
                    params={
                        "key": self.get_password("api_key"),
                        "lat": test_coords[0],
                        "lon": test_coords[1]
                    }
                )
            
            if response.status_code != 200:
                frappe.throw(f"API test failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            frappe.throw(f"API connection test failed: {str(e)}")
    
    def on_update(self):
        """Update scheduler frequency if check interval changed"""
        if self.has_value_changed("check_interval"):
            self.update_scheduler_frequency()
    
    def update_scheduler_frequency(self):
        """Update the scheduler frequency based on check interval"""
        # Convert check interval to seconds
        interval_map = {
            "15 minutes": 900,
            "30 minutes": 1800,
            "1 hour": 3600
        }
        
        interval = interval_map.get(self.check_interval, 1800)  # Default to 30 minutes
        
        # Update scheduler settings
        # Note: This is a placeholder. Actual implementation would depend on
        # how your scheduler is configured
        frappe.db.set_value(
            "Scheduler Manager",
            None,
            "weather_check_frequency",
            interval
        )