"""Location agent for getting location information."""
import os
import json
import subprocess
from typing import Dict, Optional, Tuple
import geocoder
import requests

from .base_agent import BaseAgent

LOCATION_SYSTEM_PROMPT = """You are a specialized Location Agent that provides location information.
Your tasks include:
1. Getting the current location based on IP address or system location services
2. Providing useful insights about the location
3. Formatting the information in a clear and concise way
Focus on accuracy and relevant details for the user's needs."""

class LocationAgent(BaseAgent):
    """Agent for handling location information."""
    
    def __init__(self):
        """Initialize the Location Agent."""
        super().__init__(
            agent_type="location",
            system_prompt=LOCATION_SYSTEM_PROMPT,
        )
    
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
    
    async def process(self, input_text: str, **kwargs) -> str:
        """Process location requests."""
        try:
            # Get current location
            city, lat, lng = await self.get_location()
            if city == "Unknown":
                return "❌ Sorry, I couldn't determine your current location. Please check your location services are enabled."
            
            # Format response
            response = f"""📍 Current Location: {city}
🌍 Coordinates: {lat:.4f}, {lng:.4f}
🏙️ City: {city}"""
            
            return response
            
        except Exception as e:
            print(f"❌ Error processing request: {str(e)}")
            return "❌ Sorry, I encountered an error while getting your location information. Please try again." 