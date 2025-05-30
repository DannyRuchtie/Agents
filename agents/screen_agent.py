import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from .base_agent import BaseAgent
from .vision_agent import VisionAgent  # Assuming VisionAgent is in the same directory
from config.paths_config import get_path, TEMP_DIR
from config.settings import debug_print

class ScreenAgent(BaseAgent):
    """Agent for capturing the screen and describing its content using VisionAgent."""

    def __init__(self, vision_agent_instance: VisionAgent):
        super().__init__(
            agent_type="screen",
            # ScreenAgent itself doesn't use an LLM directly for its primary action,
            # but it coordinates. If it needed to parse intent for different screen actions,
            # a system prompt would be relevant here. For now, its action is singular.
            system_prompt="You are an agent that captures the user's screen and describes it."
        )
        if not vision_agent_instance:
            raise ValueError("ScreenAgent requires an instance of VisionAgent.")
        self.vision_agent = vision_agent_instance
        self.temp_dir = TEMP_DIR # Use the configured TEMP_DIR

    async def capture_screen(self) -> Optional[str]:
        """Captures the screen and returns the path to the screenshot."""
        screenshot_filename = f"screenshot_{uuid.uuid4()}.png"
        screenshot_path = self.temp_dir / screenshot_filename

        try:
            # Ensure the temp directory exists (though ensure_directories should handle it globally)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Using screencapture for macOS.
            # -x: do not play sounds
            # -C: capture the cursor as well (optional, remove if not desired)
            # Using PNG format.
            # The command will save the file directly to the specified path.
            process = await asyncio.create_subprocess_exec(
                'screencapture', '-x', '-C', str(screenshot_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                debug_print(f"ScreenAgent: Screenshot saved to {screenshot_path}")
                return str(screenshot_path)
            else:
                error_message = stderr.decode().strip() if stderr else "Unknown error"
                debug_print(f"ScreenAgent: Error capturing screen: {error_message}. Return code: {process.returncode}")
                # Try to provide a more user-friendly error if possible
                if "DisplayID not found" in error_message or "Cannot create image" in error_message:
                     return f"Error: I couldn't capture the screen. This might be due to display issues or permissions. Specific error: {error_message}"    
                return f"Error: Failed to capture screen. {error_message}"
        except FileNotFoundError:
            debug_print("ScreenAgent: Error: 'screencapture' command not found. This agent is for macOS only.")
            return "Error: The screen capture command wasn't found. This feature is likely for macOS only."
        except Exception as e:
            debug_print(f"ScreenAgent: Unexpected error during screen capture: {e}")
            return f"Error: An unexpected issue occurred while trying to capture the screen: {str(e)}"

    async def process(self, query: str) -> str:
        """
        Captures the screen, asks VisionAgent to describe it, and returns the description.
        The 'query' for ScreenAgent can be a generic request like 'describe my screen' 
        or can include specific instructions for the VisionAgent part, e.g., 
        'look at my screen and tell me what the error message says'.
        """
        debug_print(f"ScreenAgent processing query: {query}")
        screenshot_path_str = await self.capture_screen()

        if not screenshot_path_str or screenshot_path_str.startswith("Error:"):
            return screenshot_path_str # Return the error message from capture_screen

        screenshot_path = Path(screenshot_path_str)

        if not screenshot_path.exists():
            debug_print(f"ScreenAgent: Screenshot file {screenshot_path} does not exist after capture.")
            return "Error: Screenshot was reportedly taken, but the file is missing."

        # Construct the query for VisionAgent.
        # We prepend the path of the image to the user's original query (if any specific focus was asked).
        # VisionAgent is expected to understand "Analyze this image: /path/to/image.png. Then [original query]"
        vision_query = f"Analyze this image: {str(screenshot_path)}. {query if query else 'Describe what you see on the screen.'}"
        
        debug_print(f"ScreenAgent: Sending query to VisionAgent: {vision_query}")
        description = await self.vision_agent.process(vision_query)

        # Clean up the temporary screenshot
        try:
            os.remove(screenshot_path)
            debug_print(f"ScreenAgent: Deleted temporary screenshot {screenshot_path}")
        except OSError as e:
            debug_print(f"ScreenAgent: Error deleting temporary screenshot {screenshot_path}: {e}")
            # Non-critical error, so we don't return it to the user, just log it.

        return description 