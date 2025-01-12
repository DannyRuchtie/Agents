"""Vision agent for analyzing images and screen content."""
import os
import time
from datetime import datetime
from pathlib import Path
import pyautogui
import pytesseract
from PIL import Image
import numpy as np
from .base_agent import BaseAgent
from config.openai_config import create_image_message
from config.paths_config import get_path

VISION_SYSTEM_PROMPT = """You are a specialized Vision Agent that analyzes visual content.
Your tasks include:
1. Analyzing shared images from the user
2. Capturing and analyzing screenshots when requested
3. Extracting text from images using OCR and vision analysis
4. Providing detailed descriptions of visual content
5. Organizing and managing analyzed images
Focus on accurate analysis and clear communication of visual content."""

class VisionAgent(BaseAgent):
    """Agent for analyzing images and screen content."""
    
    def __init__(self):
        """Initialize the Vision Agent."""
        super().__init__(
            agent_type="vision",  # Use vision-specific configuration
            system_prompt=VISION_SYSTEM_PROMPT,
        )
        self.screenshots_dir = get_path('screenshots')
        self.shared_dir = get_path('shared_images')
        
        # Ensure tesseract is available (used as backup for OCR)
        if not self._check_tesseract():
            print("⚠️ Warning: Tesseract OCR not found. Falling back to vision model for text extraction.")
    
    def _check_tesseract(self) -> bool:
        """Check if tesseract is installed and accessible."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    async def analyze_image(self, image_path: str, query: str = "") -> str:
        """Analyze a shared image.
        
        Args:
            image_path: Path to the image file
            query: Optional query to guide the analysis
            
        Returns:
            Analysis results including content description
        """
        try:
            # Verify the image exists
            if not os.path.exists(image_path):
                return f"Could not find image at: {image_path}"
            
            # Copy image to shared directory for organization
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shared_{timestamp}{Path(image_path).suffix}"
            filepath = self.shared_dir / filename
            
            # Copy the image
            with open(image_path, 'rb') as src, open(filepath, 'wb') as dst:
                dst.write(src.read())
            
            # Analyze content with specific query if provided
            if query:
                messages = create_image_message(query, str(filepath), detail="high")
            else:
                messages = create_image_message(
                    """Analyze this image and provide a detailed description. Include:
                    1. Main subjects or focus of the image
                    2. Important details and context
                    3. Any text content if present
                    4. Notable visual elements or patterns
                    5. Overall mood or style if relevant
                    Be specific but concise.""",
                    str(filepath),
                    detail="high"
                )
            
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[{"role": "user", "content": messages}],
                max_tokens=500
            )
            
            description = response.choices[0].message.content.strip()
            
            # Prepare response
            return f"""🔍 I've analyzed the image. Here's what I see:

{description}

The image has been saved to: {filepath}"""
            
        except Exception as e:
            print(f"❌ Error analyzing image: {str(e)}")
            return f"Could not analyze the image: {str(e)}"
    
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
            
            # Extract text using vision model
            text = await self._extract_text(filepath)
            print("📝 Text extracted from screenshot")
            
            return filepath, text
            
        except Exception as e:
            print(f"❌ Error capturing screenshot: {str(e)}")
            return None, ""
    
    async def _extract_text(self, image_path: Path) -> str:
        """Extract text from an image using vision model with OCR fallback.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text from the image
        """
        try:
            # First try using vision model
            messages = create_image_message(
                "Extract and return all text visible in this image. Return only the extracted text, nothing else.",
                str(image_path),
                detail="high"
            )
            
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[{"role": "user", "content": messages}],
                max_tokens=1000
            )
            
            vision_text = response.choices[0].message.content.strip()
            
            # If vision model fails or returns no text, try tesseract as backup
            if not vision_text and self._check_tesseract():
                image = Image.open(image_path)
                vision_text = pytesseract.image_to_string(image)
            
            return vision_text
            
        except Exception as e:
            print(f"❌ Error extracting text: {str(e)}")
            return ""
    
    async def process_screen_content(self, query: str = "") -> str:
        """Capture and process screen content based on the query.
        
        Args:
            query: Optional query to guide the analysis
            
        Returns:
            Analysis results including content description
        """
        # Capture screenshot
        filepath, text = await self.capture_screen()
        if not filepath:
            return "Failed to capture screenshot."
        
        # Analyze content with specific query if provided
        if query:
            messages = create_image_message(query, str(filepath), detail="high")
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[{"role": "user", "content": messages}],
                max_tokens=500
            )
            description = response.choices[0].message.content.strip()
        else:
            description = await self.analyze_content(filepath)
        
        # Prepare response
        response = f"""📸 I've captured and analyzed your screen. Here's what I see:

{description}

The screenshot has been saved to: {filepath}"""
        
        return response 