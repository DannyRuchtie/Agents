import cv2
import os
import tempfile
import asyncio # Added for async main
from config.settings import debug_print
from agents.vision_agent import VisionAgent # Import VisionAgent

class CameraAgent:
    def __init__(self, vision_agent: VisionAgent): # Accept VisionAgent instance
        """
        Initializes the CameraAgent.
        Args:
            vision_agent: An instance of VisionAgent.
        """
        self.last_capture_path = None
        self.vision_agent = vision_agent
        if not self.vision_agent:
            raise ValueError("VisionAgent instance is required.")
        debug_print("CameraAgent initialized with VisionAgent.")

    def capture_image(self, camera_index=0):
        """
        Captures an image from the specified camera.

        Args:
            camera_index (int): The index of the camera to use (default is 0).

        Returns:
            str: The path to the captured image file, or None if capture failed.
        """
        debug_print(f"Attempting to capture image from camera_index {camera_index}...")
        cap = cv2.VideoCapture(camera_index)

        if not cap.isOpened():
            debug_print(f"Error: Could not open camera with index {camera_index}.")
            cap.release()
            return None

        ret, frame = cap.read()
        cap.release() # Release the camera immediately after capture

        if not ret:
            debug_print("Error: Could not read frame from camera.")
            return None

        temp_file_obj = None # Initialize to ensure it's defined in finally block
        try:
            # Save the captured frame to a temporary file
            temp_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            cv2.imwrite(temp_file_obj.name, frame)
            self.last_capture_path = temp_file_obj.name
            debug_print(f"Image captured successfully and saved to {self.last_capture_path}")
            return self.last_capture_path
        except Exception as e:
            debug_print(f"Error saving captured image: {e}")
            if self.last_capture_path and os.path.exists(self.last_capture_path):
                 os.remove(self.last_capture_path) # Clean up if save failed mid-way
                 self.last_capture_path = None
            return None
        finally:
            if temp_file_obj:
                temp_file_obj.close() # Close the file handle

    async def describe_image(self, image_path: str, query: str = "Describe in detail what you see from the camera, as if you are looking through it."):
        """
        Describes the image using the provided VisionAgent.
        Cleans up the image file after attempting description.
        """
        if not image_path or not os.path.exists(image_path):
            debug_print(f"Describe image called with invalid or non-existent path: {image_path}")
            return "Could not access the captured image for description."

        debug_print(f"CameraAgent: Attempting to describe image at: {image_path} using VisionAgent.")
        description = "Vision analysis failed or was not performed." # Default if something goes wrong
        try:
            description = await self.vision_agent.analyze_image(image_path, query=query)
            debug_print(f"VisionAgent analysis complete. Description: {description[:100]}...") # Log snippet
        except Exception as e:
            debug_print(f"Error during VisionAgent analysis: {e}")
            description = f"I encountered an error while analyzing the image: {e}"
        finally:
            # Clean up the temporary file
            try:
                if os.path.exists(image_path):
                    # os.remove(image_path) # Temporarily commented out for debugging
                    debug_print(f"Temporary image file {image_path} NOT removed for debugging.") # Modified debug print
                    if self.last_capture_path == image_path:
                        self.last_capture_path = None # Clear if it was the one we just processed
            except Exception as e:
                debug_print(f"Error during (attempted) removal of temporary image file {image_path}: {e}")
            
        return description

    async def process(self, query: str):
        """
        Processes a query related to camera actions.
        Captures an image and uses VisionAgent to describe it.
        """
        debug_print(f"CameraAgent processing query: {query}")
        image_path = self.capture_image()
        if image_path:
            # Pass the responsibility of deleting image_path to describe_image (via finally block)
            description = await self.describe_image(image_path)
            return f"I've looked at the camera. {description}"
        else:
            return "I couldn't access the camera. Please check if it's connected and not in use by another application, or if I have the necessary permissions."

async def main_test(): # Renamed for clarity
    """Main function for testing CameraAgent."""
    print("Starting CameraAgent test...")
    try:
        # You'll need a VisionAgent instance. For testing, you might need to
        # initialize it or mock it if it has complex dependencies (like API keys).
        # This assumes VisionAgent() can be instantiated directly for a basic test.
        try:
            vision_agent_instance = VisionAgent()
            debug_print("VisionAgent instantiated for test.")
        except Exception as e:
            print(f"Could not instantiate VisionAgent for test: {e}")
            print("Skipping CameraAgent test that requires VisionAgent.")
            return

        camera_agent = CameraAgent(vision_agent=vision_agent_instance)
        
        print("\nTesting successful image capture and description...")
        response = await camera_agent.process("take a picture and describe it")
        print(f"Agent response: {response}")
        if camera_agent.last_capture_path and os.path.exists(camera_agent.last_capture_path):
            print(f"Warning: Temporary image file may not have been cleaned up: {camera_agent.last_capture_path}")
        else:
            print("Temporary image file (if created) was handled.")

        print("\nTesting with a non-existent camera (e.g., index 99)...")
        # For this test, we can call capture_image directly or ensure process handles it.
        # Re-instantiate or be careful if state from previous calls affects this.
        # The current process method calls capture_image, so it's covered.
        camera_agent_test_fail = CameraAgent(vision_agent=vision_agent_instance) 
        # Let's modify capture_image in this instance for the test, or rely on process
        # For a more direct test of this scenario:
        image_path_fail = camera_agent_test_fail.capture_image(camera_index=99)
        if image_path_fail is None:
            print("Correctly handled non-existent camera during capture_image call: No image path returned.")
        else:
            print(f"Unexpectedly got image path for non-existent camera: {image_path_fail}")
            if os.path.exists(image_path_fail): os.remove(image_path_fail)


        # Test the process method with a (presumably) failing camera
        print("\nTesting process method with a non-existent camera (e.g., index 99)...")
        
        # Create a mock capture_image that fails for one instance
        original_capture_image = camera_agent_test_fail.capture_image
        def mock_capture_fail(camera_index=0):
            if camera_index == 99:
                debug_print("Mocking capture_image to return None for camera_index 99")
                return None
            return original_capture_image(camera_index)

        camera_agent_test_fail.capture_image = mock_capture_fail
        response_fail_process = await camera_agent_test_fail.process("look at camera 99") # Query doesn't pick index yet
        print(f"Agent response for bad camera via process: {response_fail_process}")
        # Restore original method if other tests follow for this instance
        camera_agent_test_fail.capture_image = original_capture_image


    except Exception as e:
        print(f"An error occurred during the test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Basic test
    # Ensure that you have a VisionAgent available and configured for this test to run.
    # If VisionAgent requires API keys, ensure they are set in your environment.
    asyncio.run(main_test()) 