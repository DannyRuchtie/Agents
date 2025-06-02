"""Weather agent for fetching forecasts from a local URL."""
import asyncio
import aiohttp
import os
import json
import httpx # Using httpx for async requests
from typing import Dict, Any, Optional
import re

from .base_agent import BaseAgent
from config.settings import debug_print

# System prompt for the WeatherAgent's internal LLM (to parse location from query)
WEATHER_AGENT_SYSTEM_PROMPT = """You are an assistant that extracts location information from user queries for weather lookups.
Given the user's query, identify the city name or geographic location they are asking about.
Respond ONLY with a JSON object containing a single key "location" and the extracted location as its value.
Example: User query "What's the weather like in London?" -> {"location": "London"}
Example: User query "Tell me the current temperature in Paris, France." -> {"location": "Paris, France"}
Example: User query "Is it raining in Tokyo?" -> {"location": "Tokyo"}
If no specific location is mentioned (e.g. "what is the weather like?", "how is the weather?"), respond with {"location": null}.
"""

# System prompt for summarizing weather data from API
WEATHER_SUMMARY_PROMPT_TEMPLATE = """You are an AI assistant that provides clear and concise weather summaries.
Based on the following weather data (in JSON format), provide a user-friendly, conversational summary.
Mention the current temperature, feels-like temperature, main weather condition (e.g., sunny, cloudy, rain), humidity, and wind speed.
Convert temperature from Kelvin to Celsius (Celsius = Kelvin - 273.15).
If essential data is missing, state that you couldn't retrieve full details.

Weather Data:
{weather_data_json}

Your conversational summary:
"""

class WeatherAgent(BaseAgent):
    """Agent for fetching weather forecasts from a local service."""

    def __init__(self, memory_data_ref: Optional[Dict[str, Any]] = None):
        """Initialize the Weather Agent."""
        super().__init__(
            agent_type="weather",
            system_prompt=WEATHER_AGENT_SYSTEM_PROMPT
        )
        self.api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        if not self.api_key:
            debug_print("WeatherAgent: WARNING - OPENWEATHERMAP_API_KEY not found in .env. Weather functionality will fail.")
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.memory_data_ref = memory_data_ref if memory_data_ref is not None else {}

    async def get_weather(self, location: str) -> Optional[Dict[str, Any]]:
        """Fetches current weather data for a given location from OpenWeatherMap."""
        if not self.api_key:
            debug_print("WeatherAgent: Missing API key. Cannot fetch weather.")
            return None
        if not location:
            debug_print("WeatherAgent: No location provided.")
            return None

        params = {
            'q': location,
            'appid': self.api_key,
            'units': 'metric' # Request Celsius directly, though API returns Kelvin by default. We'll use metric for feels_like etc.
                                # API provides temp in Kelvin by default. If using 'metric', temp is Celsius.
                                # Let's stick to Kelvin from API and convert, as per original plan, for clarity.
                                # No, 'metric' gives Celsius. 'standard' (default) gives Kelvin. Let's use metric for direct Celsius.
        }
        params_no_units = {
            'q': location,
            'appid': self.api_key
        }


        try:
            async with httpx.AsyncClient() as client:
                # First, try with units=metric to get Celsius directly
                response = await client.get(self.base_url, params=params)
                response.raise_for_status() # Raise an exception for HTTP errors (4XX, 5XX)
                debug_print(f"WeatherAgent: API response for {location} (units=metric): {response.json()}")
                return response.json()
        except httpx.HTTPStatusError as e:
            debug_print(f"WeatherAgent: HTTP error fetching weather for {location} (units=metric): {e.response.status_code} - {e.response.text}")
            # If units=metric fails (e.g. some locations don't play well with it, though rare for 'q'),
            # try falling back to standard units (Kelvin) if the error suggests it might be parameter related.
            # For now, we'll just report the error from the 'metric' attempt.
            # A more robust fallback could try params_no_units if the error is e.g. 400.
            return {"error": True, "status_code": e.response.status_code, "message": e.response.json().get("message", "API error") if e.response.content else "API error"}
        except httpx.RequestError as e:
            debug_print(f"WeatherAgent: Request error fetching weather for {location}: {e}")
            return {"error": True, "message": "Network error connecting to weather service."}
        except Exception as e:
            debug_print(f"WeatherAgent: Unexpected error fetching weather for {location}: {e}")
            return {"error": True, "message": f"Unexpected error: {str(e)}"}

    async def process(self, query: str) -> str:
        """Processes a weather-related query from the user."""
        if not self.api_key:
            return "I can't provide weather information right now as I'm missing the necessary API key configuration."

        debug_print(f"WeatherAgent processing query: {query}")
        extracted_location: Optional[str] = None

        # Use LLM (BaseAgent.process with WEATHER_AGENT_SYSTEM_PROMPT) to extract location
        try:
            location_json_str = await super().process(query)
            debug_print(f"WeatherAgent: LLM location extraction response: {location_json_str}")
            location_data = json.loads(location_json_str)
            extracted_location = location_data.get("location")
        except json.JSONDecodeError:
            debug_print("WeatherAgent: Failed to parse JSON from LLM for location extraction. Will check memory for default.")
            extracted_location = None 
        except Exception as e:
            debug_print(f"WeatherAgent: Error during LLM location extraction: {e}. Will check memory for default.")
            extracted_location = None

        if not extracted_location:
            debug_print("WeatherAgent: No location in query from LLM. Checking memory for user's default location.")
            # 1. Check for explicit default_location fact (legacy support)
            if isinstance(self.memory_data_ref, dict) and "fact_store" in self.memory_data_ref:
                for fact in self.memory_data_ref["fact_store"]:
                    if isinstance(fact, dict) and fact.get("entity", "").lower() == "user" and fact.get("attribute", "").lower() == "default_location":
                        user_default_location = fact.get("value")
                        if user_default_location:
                            extracted_location = user_default_location
                            debug_print(f"WeatherAgent: Using user default location from memory: {extracted_location}")
                            break
            # 2. If not found, search 'personal' memories for location-like statements
            if not extracted_location and isinstance(self.memory_data_ref, dict) and "personal" in self.memory_data_ref:
                personal_memories = self.memory_data_ref["personal"]
                location_candidates = []
                for entry in personal_memories:
                    if not isinstance(entry, dict):
                        continue
                    content = entry.get("content", "").lower()
                    # Look for common location phrases
                    match = re.search(r"i (live|am) in ([a-zA-Z\s]+)", content)
                    if match:
                        location = match.group(2).strip().capitalize()
                        location_candidates.append((entry.get("timestamp", ""), location))
                # Use the most recent such entry
                if location_candidates:
                    location_candidates.sort(reverse=True) # Most recent first
                    extracted_location = location_candidates[0][1]
                    debug_print(f"WeatherAgent: Extracted location from personal memory: {extracted_location}")
            if not extracted_location: # Still no location after checking memory
                debug_print("WeatherAgent: No default location found in memory.")
                return "I couldn't determine the location for the weather forecast from your query, nor find a default location in memory. Please specify a city or area."
        
        debug_print(f"WeatherAgent: Final location for weather lookup: {extracted_location}")
        weather_api_data = await self.get_weather(extracted_location)

        if not weather_api_data:
            return f"Sorry, I couldn't retrieve weather data for {extracted_location} at the moment due to an unexpected issue with the weather service connection."
        
        if weather_api_data.get("error"):
            api_error_message = weather_api_data.get("message", "an unknown issue")
            if weather_api_data.get("status_code") == 404:
                return f"I couldn't find weather information for '{extracted_location}'. Please check the location name and try again."
            elif weather_api_data.get("status_code") == 401: # Unauthorized
                 return f"I can't access the weather service right now due to an authentication issue (API key problem). Please check the setup."
            return f"Sorry, I encountered an error when fetching weather data for {extracted_location}: {api_error_message}."

        # Use LLM to summarize the weather data
        # Temporarily set a different system prompt for summarization
        original_system_prompt = self.system_prompt
        self.system_prompt = WEATHER_SUMMARY_PROMPT_TEMPLATE.format(weather_data_json=json.dumps(weather_api_data))
        
        # We are not actually sending a query to the LLM here, the weather data is in the prompt.
        # So the "query" argument to super().process can be minimal or a placeholder.
        summary_query_placeholder = "Provide a weather summary based on the data in your system prompt."

        try:
            # The actual data to summarize is embedded in the system_prompt
            # The query here is just to trigger the LLM call with that prompt.
            summary = await super().process(summary_query_placeholder) 
        except Exception as e:
            debug_print(f"WeatherAgent: Error during LLM weather summarization: {e}")
            summary = "I retrieved the weather data, but I had trouble summarizing it."
        finally:
            self.system_prompt = original_system_prompt # Reset system prompt

        return summary 