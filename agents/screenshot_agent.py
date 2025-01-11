"""Screenshot agent for capturing and analyzing screen content."""
import os
import time
from datetime import datetime
from pathlib import Path
import pyautogui
import pytesseract
from PIL import Image
import numpy as np
from base_agent import BaseAgent

SCREENSHOT_SYSTEM_PROMPT = """You are a specialized Screenshot Agent that captures and analyzes screen content.
Your tasks include:
1. Capturing screenshots of the entire screen or specific regions
2. Extracting text from images using OCR
3. Analyzing image content and providing descriptions
4. Organizing and managing screenshot files
5. Integrating with other agents to provide visual context
Focus on accurate capture and analysis while maintaining organized storage."""

class ScreenshotAgent(BaseAgent):
    """Agent for capturing and analyzing screen content."""
    
    def __init__(self):
        """Initialize the Screenshot Agent."""
        super().__init__(
            agent_type="screenshot",
            system_prompt=SCREENSHOT_SYSTEM_PROMPT,
        )
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # Ensure tesseract is available (required for OCR)
        if not self._check_tesseract():
            print("⚠️ Warning: Tesseract OCR not found. Text extraction will be disabled.")
    
    def _check_tesseract(self) -> bool:
        """Check if tesseract is installed and accessible."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    async def capture_screen(self, region=None) -> tuple[Path, str]:
        """Capture a screenshot of the screen or specified region.
        
        Args:
            region: Optional tuple of (left, top, width, height) for partial capture
            
        Returns:
            Tuple of (screenshot path, extracted text)
        """
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        
        # Capture screenshot
        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            # Save screenshot
            screenshot.save(filepath)
            print(f"📸 Screenshot saved to {filepath}")
            
            # Extract text if tesseract is available
            text = ""
            if self._check_tesseract():
                text = pytesseract.image_to_string(screenshot)
                print("📝 Text extracted from screenshot")
            
            return filepath, text
            
        except Exception as e:
            print(f"❌ Error capturing screenshot: {str(e)}")
            return None, ""
    
    async def analyze_content(self, image_path: Path) -> str:
        """Analyze the content of a screenshot and provide a description.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Description of the image content
        """
        try:
            # Extract text from image
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image) if self._check_tesseract() else ""
            
            # Get image properties
            width, height = image.size
            
            # Prepare prompt for content analysis
            prompt = f"""Analyze this screenshot and provide a clear description.
            Image dimensions: {width}x{height}
            Extracted text: {text}
            
            Describe the content, layout, and any notable elements visible in the screenshot."""
            
            # Use base agent to analyze content
            description = await self.process(prompt)
            return description
            
        except Exception as e:
            print(f"❌ Error analyzing screenshot: {str(e)}")
            return "Could not analyze screenshot content."
    
    async def process_screen_content(self, query: str = "") -> str:
        """Capture and process screen content based on the query.
        
        Args:
            query: Optional query to guide the analysis
            
        Returns:
            Analysis results including extracted text and content description
        """
        # Capture screenshot
        filepath, text = await self.capture_screen()
        if not filepath:
            return "Failed to capture screenshot."
        
        # Analyze content
        description = await self.analyze_content(filepath)
        
        # Prepare response
        response = f"""📸 Screenshot captured and analyzed:
        
Location: {filepath}

📝 Extracted Text:
{text if text.strip() else '(No text detected)'}

🔍 Content Analysis:
{description}

The screenshot has been saved and can be referenced later."""
        
        return response 