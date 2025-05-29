"""Weather agent for fetching forecasts from a local URL."""
import asyncio
import aiohttp
from typing import Dict, Any

from .base_agent import BaseAgent
from config.settings import debug_print

WEATHER_SYSTEM_PROMPT = """You are a Weather Agent. Your task is to fetch and present weather forecast data clearly.
You will retrieve data from a local forecast service."""

class WeatherAgent(BaseAgent):
    """Agent for fetching weather forecasts from a local service."""

    def __init__(self):
        """Initialize the Weather Agent."""
        super().__init__(
            agent_type="weather",
            system_prompt=WEATHER_SYSTEM_PROMPT,
        )
        self.forecast_url = "http://127.0.0.1:8008/forecast"

    async def get_weather_forecast(self) -> Dict[str, Any]:
        """Fetch weather forecast data from the local service."""
        debug_print(f"Fetching weather forecast from {self.forecast_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.forecast_url) as response:
                    response.raise_for_status()  # Raise an exception for bad status codes
                    data = await response.json()
                    debug_print(f"Successfully fetched forecast data: {data}")
                    return data
        except aiohttp.ClientConnectorError:
            debug_print(f"Error: Could not connect to {self.forecast_url}. Ensure the service is running.")
            return {"error": "Could not connect to the weather service. Please ensure it's running."}
        except aiohttp.ContentTypeError:
            debug_print("Error: Weather service did not return valid JSON.")
            return {"error": "The weather service returned data in an unexpected format."}
        except Exception as e:
            debug_print(f"Error fetching weather forecast: {str(e)}")
            return {"error": f"An unexpected error occurred while fetching the forecast: {str(e)}"}

    async def process(self, query: str, **kwargs: Any) -> str:
        """Process a request for weather information, parsing the hourly forecast data."""
        debug_print(f"WeatherAgent processing query: {query}")
        forecast_data = await self.get_weather_forecast()

        if not forecast_data or "error" in forecast_data:
            error_msg = forecast_data.get("error", "Could not retrieve weather data.")
            print(error_msg)
            return error_msg

        debug_print(f"WeatherAgent received data: {forecast_data}")

        try:
            # Ensure forecast_data is a non-empty dictionary
            if not isinstance(forecast_data, dict) or not forecast_data:
                debug_print("WeatherAgent: Forecast data is not a valid non-empty dictionary.")
                error_msg = f"Sorry, the weather data received was not in the expected format for Zeegse."
                print(error_msg)
                return error_msg

            location_name = "Zeegse" # Default to Zeegse
            
            # For simplicity, we'll assume the query implies wanting current/near-term weather
            # unless specific keywords for a longer forecast are present.
            
            # Find the current or soonest forecast entry
            # We need datetime to compare, assuming forecast keys are ISO-like strings
            import datetime
            now = datetime.datetime.now()
            soonest_entry_time_str = None
            soonest_entry_data = None
            # min_time_diff = datetime.timedelta.max # Not currently used, can be removed or kept for other logic

            processed_forecasts = []
            num_forecasts_to_show = 1 
            target_specific_time_dt = None

            # Try to parse a specific time from the query (very basic parsing)
            # Example: "weather at 8pm", "temp at 20:00"
            # This is a simplistic approach and can be significantly improved with more robust parsing.
            query_lower = query.lower()
            if " at " in query_lower:
                try:
                    time_str_part = query_lower.split(" at ")[1].replace(".","") # Remove periods often used like "at 8 p.m."
                    # Attempt to parse common time formats, assuming today's date if only time is given
                    # This will need refinement for different phrasing and for dates other than today.
                    # For now, let's try a few formats. This is hard without a proper NLP date/time parser.
                    # Example: "8pm", "20:00"
                    parsed_time = None
                    formats_to_try = ["%I%p", "%I %p", "%H:%M"] # e.g., "8pm", "8 pm", "20:00"
                    for fmt in formats_to_try:
                        try:
                            parsed_time = datetime.datetime.strptime(time_str_part.strip(), fmt).time()
                            break
                        except ValueError:
                            continue
                    
                    if parsed_time:
                        # Combine with today's date for comparison, or if a date is also parsed, use that.
                        # For now, assumes the query refers to a time on the current day if only time is specified.
                        # Or, if the data timestamps include dates, it will match against those.
                        target_specific_time_dt = datetime.datetime.combine(now.date(), parsed_time)
                        debug_print(f"WeatherAgent: Parsed specific target time from query: {target_specific_time_dt}")
                        num_forecasts_to_show = 1 # We only want this specific time
                except Exception as e:
                    # Corrected f-string for the debug message
                    time_str_part_debug = query_lower.split(" at ")[1] if " at " in query_lower else "[not found]"
                    debug_print(f"WeatherAgent: Could not parse specific time from query part '{time_str_part_debug}': {e}")

            # Basic keyword check for a multi-hour forecast (prediction) for future
            if not target_specific_time_dt and any(keyword in query_lower for keyword in ["prediction", "forecast", "later", "next few hours"]):
                num_forecasts_to_show = 3 
            
            # Sort the forecast keys (timestamps) to process them chronologically
            sorted_timestamps = sorted(forecast_data.keys())
            debug_print(f"WeatherAgent: Sorted timestamps to process: {sorted_timestamps}")
            
            if not sorted_timestamps:
                debug_print("WeatherAgent: No timestamps found in the forecast data.")
                error_msg = f"Sorry, I couldn't find any specific forecast times for Zeegse."
                print(error_msg)
                return error_msg

            future_forecasts_found = 0
            
            for timestamp_str in sorted_timestamps:
                try:
                    entry_time = datetime.datetime.fromisoformat(timestamp_str)
                    debug_print(f"WeatherAgent: Parsed '{timestamp_str}' to datetime: {entry_time}") 
                    
                    # If a specific time was requested in the query
                    if target_specific_time_dt:
                        # Check if this entry matches the requested time (ignoring seconds/microseconds for flexibility)
                        if entry_time.year == target_specific_time_dt.year and \
                           entry_time.month == target_specific_time_dt.month and \
                           entry_time.day == target_specific_time_dt.day and \
                           entry_time.hour == target_specific_time_dt.hour and \
                           entry_time.minute == target_specific_time_dt.minute:
                            debug_print(f"WeatherAgent: Timestamp {timestamp_str} matches specific target time {target_specific_time_dt}.")
                            # (Further processing for this specific entry is below)
                        else:
                            # If target_specific_time_dt is set, we only care about that exact match.
                            debug_print(f"WeatherAgent: Timestamp {timestamp_str} does not match specific target {target_specific_time_dt}. Skipping.")
                            continue 
                    # If no specific time in query, look for current/future for general requests or predictions
                    elif entry_time < now and num_forecasts_to_show > 1: # if asking for prediction, skip past entries
                        debug_print(f"WeatherAgent: Timestamp {timestamp_str} is in the past ({entry_time} < {now}) for a prediction query. Skipping.")
                        continue
                    elif entry_time < now and num_forecasts_to_show == 1 and not target_specific_time_dt: # if general query for current, skip past
                        debug_print(f"WeatherAgent: Timestamp {timestamp_str} is in the past ({entry_time} < {now}) for a current weather query. Skipping.")
                        continue
                        
                    # Proceed to format this entry if it's relevant
                    # (i.e., it matched target_specific_time_dt, or it's a future entry for a general/prediction query)
                    
                    # This condition ensures we only add if it's the specifically targeted past/future time, 
                    # OR if it's a future time and we haven't collected enough for a prediction/current display.
                    if future_forecasts_found < num_forecasts_to_show: 
                        entry_data = forecast_data[timestamp_str]
                        temp = entry_data.get('temp', 'N/A')
                        prcp = entry_data.get('prcp', 'N/A') # Precipitation
                        wspd = entry_data.get('wspd', 'N/A') # Wind speed
                        rhum = entry_data.get('rhum', 'N/A') # Relative humidity
                        wdir_sin = entry_data.get('wdir_sin')
                        wdir_cos = entry_data.get('wdir_cos')
                        
                        # Calculate wind direction
                        wind_direction_cardinal = "N/A"
                        if wdir_sin is not None and wdir_cos is not None:
                            import math
                            # angle in radians from atan2(sin, cos) is typically Y, X relative to positive X-axis
                            # Meteorological wind direction is usually where the wind is COMING FROM.
                            # Standard atan2(y,x) gives angle relative to positive x-axis.
                            # If sin is y (Northward component) and cos is x (Eastward component),
                            # then atan2(sin, cos) is fine. Let's assume this convention.
                            angle_rad = math.atan2(wdir_sin, wdir_cos) 
                            angle_deg = math.degrees(angle_rad)
                            # Convert from -180 to 180 range to 0 to 360 range
                            angle_deg = (angle_deg + 360) % 360
                            
                            # Convert degrees to cardinal direction
                            directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
                            index = round(angle_deg / (360. / len(directions))) % len(directions)
                            wind_direction_cardinal = directions[index]

                        # Simple condition summary (can be improved)
                        condition = "Clear"
                        if prcp is not None and isinstance(prcp, (int, float)) and prcp > 0.0:
                            condition = "Precipitation expected"
                        elif wspd is not None and isinstance(wspd, (int, float)) and wspd > 15: # Adjusted threshold
                            condition = "Windy"
                        elif rhum is not None and isinstance(rhum, (int, float)) and rhum > 90:
                            condition = "High humidity"

                        forecast_detail = (
                            f"For {entry_time.strftime('%I:%M %p on %b %d')}:\n"
                            f"  - Temperature: {temp}°C\n"
                            f"  - Condition: {condition}\n"
                            f"  - Precipitation: {prcp}mm\n"
                            f"  - Wind: {wspd}km/h from {wind_direction_cardinal}\n"
                            f"  - Humidity: {rhum}%"
                        )
                        processed_forecasts.append(forecast_detail)
                        future_forecasts_found += 1
                    else:
                        debug_print(f"WeatherAgent: Already found enough forecasts ({num_forecasts_to_show}). Breaking loop.")
                        break # Got enough future forecasts
                except ValueError:
                    debug_print(f"WeatherAgent: Could not parse timestamp: {timestamp_str}. Skipping entry.")
                    continue # Skip malformed timestamps

            if not processed_forecasts:
                error_msg = f"Sorry, I couldn't find any current or future weather information for {location_name}."
                print(error_msg)
                return error_msg

            response_intro = f"Here's the weather update for {location_name}:\n"
            final_response = response_intro + "\n\n".join(processed_forecasts)
            print(final_response)
            return final_response

        except Exception as e:
            debug_print(f"Error formatting weather forecast: {str(e)}")
            error_msg = "I had trouble understanding the weather data format. The raw data might be available in the logs."
            print(error_msg)
            return error_msg 