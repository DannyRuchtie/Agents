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
        """Get location using macOS CoreLocation services via the 'whereami' command-line tool."""
        try:
            # Try to use the 'whereami' command-line tool if available
            # Assumes 'whereami' is installed and outputs JSON with --format json
            # e.g., {"latitude": 37.7749, "longitude": -122.4194, "accuracy": 65, ...}
            cmd = ["whereami", "--format", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                debug_print(f"whereami stdout: {result.stdout.strip()}")
                data = json.loads(result.stdout.strip())
                lat = data.get('latitude')
                lon = data.get('longitude')
                
                if lat is not None and lon is not None:
                    # 'whereami' doesn't directly give city name.
                    # We need to reverse geocode the lat/lon to get a city name.
                    # We can use geocoder for this, or another service if preferred.
                    try:
                        g = geocoder.osm([lat, lon], method='reverse')
                        city = g.city if g.ok and g.city else f"Near {lat:.2f}, {lon:.2f}"
                        debug_print(f"macOS CoreLocation (via whereami & reverse geocode): City: {city}, Lat: {lat}, Lon: {lon}")
                        return city, float(lat), float(lon)
                    except Exception as rev_geo_e:
                        debug_print(f"Reverse geocoding for whereami result failed: {rev_geo_e}")
                        # Fallback: return lat/lon, city will be handled by generic IP lookup if this fails higher up
                        # Or, just return None so the main get_location tries other methods for city name.
                        # For now, let's return None to allow IP services to provide the city name cleanly.
                        return None 
            else:
                debug_print(f"'whereami' command failed or gave no output. Return code: {result.returncode}, Error: {result.stderr.strip()}")
                debug_print("Ensure 'whereami' (from corelocationcli or similar) is installed and has location permissions.")
                
        except FileNotFoundError:
            debug_print("'whereami' command not found. Please install it (e.g., npm install -g corelocationcli) for precise macOS location.")
        except subprocess.TimeoutExpired:
            debug_print("'whereami' command timed out.")
        except Exception as e:
            # Use debug_print from config.settings for consistency if available, otherwise use standard print
            try:
                from config.settings import debug_print
                debug_print(f"Error getting macOS location via whereami: {str(e)}")
            except ImportError:
                print(f"[DEBUG_LOCATION_AGENT] Error getting macOS location via whereami: {str(e)}")
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