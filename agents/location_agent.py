"""Location agent for getting location and weather information."""
import os
import json
import subprocess
from typing import Dict, Optional, Tuple
import geocoder
import python_weather
import asyncio
from datetime import datetime
import requests

from .base_agent import BaseAgent

LOCATION_SYSTEM_PROMPT = """You are a specialized Location Agent that provides location and weather information.
Your tasks include:
1. Getting the current location based on IP address
2. Fetching detailed weather information for the location
3. Providing useful insights about the location and weather
4. Formatting the information in a clear and concise way
Focus on accuracy and relevant details for the user's needs."""

class LocationAgent(BaseAgent):
    """Agent for handling location and weather information."""
    
    def __init__(self):
        """Initialize the Location Agent."""
        super().__init__(
            agent_type="location",
            system_prompt=LOCATION_SYSTEM_PROMPT,
        )
        self.weather_client = python_weather.Client(unit=python_weather.IMPERIAL)
    
    def _get_location_from_mac(self) -> Optional[Tuple[str, float, float]]:
        """Get location using macOS CoreLocation services."""
        try:
            # Use CoreLocation through a shell command
            cmd = """
            osascript -e '
            tell application "System Events"
                tell application process "SystemUIServer"
                    try
                        click (menu bar item 1 of menu bar 1 whose description contains "Location")
                        delay 0.5
                        click (menu bar item 1 of menu bar 1 whose description contains "Location")
                        return "Location accessed"
                    on error
                        return "Location error"
                    end try
                end tell
            end tell'
            """
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if "Location accessed" in result.stdout:
                # Now get the actual location data
                response = requests.get('https://ipapi.co/json/')
                if response.status_code == 200:
                    data = response.json()
                    return data['city'], float(data['latitude']), float(data['longitude'])
            
        except Exception as e:
            print(f"❌ Error getting macOS location: {str(e)}")
        return None
    
    async def get_location(self) -> Tuple[str, float, float]:
        """Get the current location using multiple sources.
        
        Returns:
            Tuple of (location name, latitude, longitude)
        """
        try:
            # Try macOS location first
            mac_location = self._get_location_from_mac()
            if mac_location:
                return mac_location
            
            # Try ipapi.co as fallback
            response = requests.get('https://ipapi.co/json/')
            if response.status_code == 200:
                data = response.json()
                return data['city'], float(data['latitude']), float(data['longitude'])
            
            # Try geocoder as final fallback
            g = geocoder.ip('me')
            if g.ok:
                return g.city, g.lat, g.lng
            
            raise Exception("Could not determine location from any source")
            
        except Exception as e:
            print(f"❌ Error getting location: {str(e)}")
            return "Unknown", 0.0, 0.0
    
    async def get_weather(self, lat: float, lng: float) -> Optional[Dict]:
        """Get weather information for the given coordinates."""
        try:
            # Use OpenWeatherMap API
            api_key = os.getenv("OPENWEATHER_API_KEY")
            if not api_key:
                print("❌ OpenWeather API key not found in environment variables")
                return None
                
            api_key = api_key.strip()  # Remove any whitespace
            if not api_key:
                print("❌ OpenWeather API key is empty")
                return None
                
            # Use the free tier API endpoint
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={api_key}&units=metric"
            print(f"🌍 Fetching weather data from OpenWeather API...")  # Debug line
            response = requests.get(url, timeout=10)
            
            if response.status_code == 401:
                print(f"❌ Invalid OpenWeather API key. This could be because:")
                print("   1. The API key is incorrect")
                print("   2. The API key is new and hasn't been activated yet (can take up to 2 hours)")
                print("   3. You haven't subscribed to the free tier at https://openweathermap.org/price")
                print(f"   API Response: {response.text}")
                return None
            elif response.status_code != 200:
                print(f"❌ OpenWeather API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            return {
                "temperature": round(data['main']['temp'], 1),
                "description": data['weather'][0]['description'],
                "humidity": data['main']['humidity'],
                "wind_speed": round(data['wind']['speed'] * 3.6, 1),  # Convert m/s to km/h
                "time": datetime.now().strftime("%H:%M"),
            }
                
        except requests.Timeout:
            print("❌ OpenWeather API request timed out. Please try again")
            return None
        except Exception as e:
            print(f"❌ Error getting weather: {str(e)}")
            return None
    
    async def process(self, input_text: str, **kwargs) -> str:
        """Process location and weather requests."""
        try:
            # Get current location
            city, lat, lng = await self.get_location()
            if city == "Unknown":
                return "❌ Sorry, I couldn't determine your current location. Please check your location services are enabled."
            
            # Get weather data
            weather = await self.get_weather(lat, lng)
            if not weather:
                return f"""📍 Location found: {city} (Lat: {lat}, Lng: {lng})
❌ Could not get weather information. If you've just created your OpenWeather API key, please note:
   • New API keys take 10 minutes to 2 hours to activate
   • You can check the status at: https://home.openweathermap.org/api_keys
   • Once activated, the weather information will appear automatically"""
            
            # Format response
            response = f"""📍 Current Location: {city}
🌡️ Temperature: {weather['temperature']}°C
☁️ Conditions: {weather['description']}
💧 Humidity: {weather['humidity']}%
💨 Wind Speed: {weather['wind_speed']} km/h
⏰ Local Time: {weather['time']}"""
            
            return response
            
        except Exception as e:
            print(f"❌ Error processing request: {str(e)}")
            return "❌ Sorry, I encountered an error while getting your location and weather information. Please try again."
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources."""
        await self.weather_client.close() 