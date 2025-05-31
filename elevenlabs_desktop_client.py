import sounddevice as sd
import pvporcupine
import websockets
import asyncio
import threading
import queue
import os
import json
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# --- Configuration ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
ELEVENLABS_WEBSOCKET_URL_TEMPLATE = "wss://api.elevenlabs.io/v1/conversational/{agent_id}/ws?voice_id={voice_id}"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Example: Rachel

WAKE_WORD_KEYWORD_PATHS = [pvporcupine.KEYWORD_PATHS["jarvis"]] # Or your custom .ppn file
PORCUPINE_MODEL_PATH = pvporcupine.MODEL_PATH

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_BLOCK_DURATION_MS = 50

# --- Application States (for console logging) ---
STATE_IDLE = "idle"
STATE_AWAKENED = "awakened"
STATE_LISTENING_TO_USER = "listening_to_user"
STATE_PROCESSING_USER_SPEECH = "processing_user_speech"
STATE_AGENT_SPEAKING = "agent_speaking"

STATUS_TEXT = {
    STATE_IDLE: "Status: Idle. Waiting for wake word...",
    STATE_AWAKENED: "Status: Awakened. Listening for your command...",
    STATE_LISTENING_TO_USER: "Status: Listening to user...",
    STATE_PROCESSING_USER_SPEECH: "Status: Processing user speech...",
    STATE_AGENT_SPEAKING: "Status: Agent speaking..."
}


class VoiceApp:
    def __init__(self):
        print("Initializing Voice Assistant (CLI mode)...")
        self.current_state = STATE_IDLE
        self.porcupine = None
        self.audio_stream_in = None
        self.audio_stream_out = None
        self.websocket = None
        self.event_queue = queue.Queue() # Still useful for inter-thread communication if needed
        self.asyncio_loop = None
        self.asyncio_thread = None
        self.keep_recording = False
        self.user_is_speaking = False
        self.shutdown_event = threading.Event() # For graceful shutdown

        self._validate_keys()
        self._initialize_services()

    def _validate_keys(self):
        if not PICOVOICE_ACCESS_KEY:
            print("ERROR: PICOVOICE_ACCESS_KEY not found in .env file.")
        if not ELEVENLABS_API_KEY:
            print("ERROR: ELEVENLABS_API_KEY not found in .env file.")
        if not ELEVENLABS_AGENT_ID:
            print("ERROR: ELEVENLABS_AGENT_ID not found in .env file. Please configure it.")
        # Consider exiting if keys are missing and critical

    def _set_state(self, new_state):
        self.current_state = new_state
        print(STATUS_TEXT.get(self.current_state, f"Status: {self.current_state}"))

    def _initialize_services(self):
        try:
            self.porcupine = pvporcupine.create(
                access_key=PICOVOICE_ACCESS_KEY,
                keyword_paths=WAKE_WORD_KEYWORD_PATHS,
                sensitivities=[0.5] * len(WAKE_WORD_KEYWORD_PATHS)
            )
            print(f"Porcupine initialized. Frame length: {self.porcupine.frame_length}, Sample rate: {self.porcupine.sample_rate}")

            self.porcupine_thread = threading.Thread(target=self._run_porcupine_loop, daemon=True)
            self.porcupine_thread.start()

            self.asyncio_loop = asyncio.new_event_loop()
            self.asyncio_thread = threading.Thread(target=self._start_asyncio_loop, daemon=True)
            self.asyncio_thread.start()
            
            print("Services initialized.")
            self._set_state(STATE_IDLE)

        except pvporcupine.PorcupineError as e:
            print(f"Porcupine initialization failed: {e}")
            # Potentially set a failed state or exit
        except Exception as e:
            print(f"Error initializing services: {e}")

    def _start_asyncio_loop(self):
        asyncio.set_event_loop(self.asyncio_loop)
        self.asyncio_loop.run_forever()

    def _run_porcupine_loop(self):
        if not self.porcupine:
            return

        audio_stream_porcupine = None
        try:
            audio_stream_porcupine = sd.InputStream(
                samplerate=self.porcupine.sample_rate,
                channels=1,
                dtype='int16',
                blocksize=self.porcupine.frame_length,
                callback=None
            )
            audio_stream_porcupine.start()
            print("Porcupine listening for wake word (Ctrl+C to exit)...")

            while not self.shutdown_event.is_set():
                if self.current_state == STATE_IDLE:
                    pcm = audio_stream_porcupine.read(self.porcupine.frame_length)[0]
                    result = self.porcupine.process(pcm.flatten())

                    if result >= 0:
                        print(f"Wake word detected (keyword_index {result})!")
                        # self.event_queue.put("WAKE_WORD_DETECTED") # If using queue for other things
                        asyncio.run_coroutine_threadsafe(self.handle_wake_word(), self.asyncio_loop)
                        self._set_state(STATE_AWAKENED)
                        # Wait for conversation to finish or timeout
                        while self.current_state != STATE_IDLE and not self.shutdown_event.is_set():
                            time.sleep(0.1)
                        if not self.shutdown_event.is_set():
                           print("Resuming wake word detection.")
                else:
                    time.sleep(0.1)

        except Exception as e:
            if not self.shutdown_event.is_set(): # Don't print errors if shutting down
                print(f"Porcupine loop error: {e}")
        finally:
            if audio_stream_porcupine is not None:
                audio_stream_porcupine.stop()
                audio_stream_porcupine.close()
            print("Porcupine loop stopped.")

    async def handle_wake_word(self):
        if not ELEVENLABS_AGENT_ID or not ELEVENLABS_API_KEY:
            print("ERROR: ElevenLabs Agent ID or API Key not configured for wake word handling.")
            self._set_state(STATE_IDLE)
            return

        self._set_state(STATE_AWAKENED) # State already set by caller, but good for clarity
        self.user_is_speaking = False

        websocket_url = ELEVENLABS_WEBSOCKET_URL_TEMPLATE.format(
            agent_id=ELEVENLABS_AGENT_ID,
            voice_id=DEFAULT_VOICE_ID
        )
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        
        print(f"Connecting to ElevenLabs: {websocket_url}")

        try:
            async with websockets.connect(websocket_url, extra_headers=headers) as ws:
                self.websocket = ws
                print("Connected to ElevenLabs.")
                self.keep_recording = True
                
                send_task = asyncio.create_task(self._send_microphone_input())
                receive_task = asyncio.create_task(self._receive_agent_output())
                
                await asyncio.gather(send_task, receive_task)

        except websockets.exceptions.ConnectionClosed as e:
            print(f"ElevenLabs WebSocket connection closed: {e}")
        except Exception as e:
            print(f"ElevenLabs WebSocket error: {e}")
        finally:
            self.websocket = None
            self.keep_recording = False
            # Ensure streams are closed if they were opened
            if self.audio_stream_in:
                try:
                    self.audio_stream_in.stop()
                    self.audio_stream_in.close()
                except Exception as e_si:
                    print(f"Error closing input stream: {e_si}")
                self.audio_stream_in = None
            if self.audio_stream_out:
                try:
                    self.audio_stream_out.stop()
                    # RawOutputStream doesn't always have close()
                except Exception as e_so:
                    print(f"Error stopping output stream: {e_so}")                    
                self.audio_stream_out = None
            print("ElevenLabs session ended.")
            if not self.shutdown_event.is_set(): # Don't revert to idle if shutting down globally
                self._set_state(STATE_IDLE)

    async def _send_microphone_input(self):
        if not self.websocket or self.shutdown_event.is_set():
            return

        self._set_state(STATE_LISTENING_TO_USER)
        await asyncio.sleep(0.2)

        try:
            self.audio_stream_in = sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype='int16',
                blocksize=int(AUDIO_SAMPLE_RATE * AUDIO_BLOCK_DURATION_MS / 1000)
            )
            self.audio_stream_in.start()
            print("Microphone input stream started for ElevenLabs.")

            while self.keep_recording and self.current_state not in [STATE_AGENT_SPEAKING, STATE_IDLE] and not self.shutdown_event.is_set() and self.websocket and self.websocket.open:
                audio_chunk, overflowed = self.audio_stream_in.read(self.audio_stream_in.blocksize)
                if overflowed:
                    print("Warning: Microphone input overflowed")
                
                if len(audio_chunk) > 0 and self.websocket and self.websocket.open:
                    try:
                        await self.websocket.send(audio_chunk.tobytes())
                        if not self.user_is_speaking:
                            self.user_is_speaking = True
                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket closed by server while sending audio.")
                        self.keep_recording = False # Stop trying to send
                        break 
                    except Exception as e_send:
                        print(f"Error during websocket send: {e_send}")
                        self.keep_recording = False
                        break
                await asyncio.sleep(AUDIO_BLOCK_DURATION_MS / 1000)

        except Exception as e:
            if not self.shutdown_event.is_set():
                print(f"Error sending microphone input: {e}")
        finally:
            if self.audio_stream_in:
                try:
                    self.audio_stream_in.stop()
                    self.audio_stream_in.close()
                except Exception as e_si_fin:
                     print(f"Error closing input stream in _send_microphone_input finally: {e_si_fin}")
                self.audio_stream_in = None
            print("Microphone input stream for ElevenLabs stopped.")
            if self.current_state == STATE_LISTENING_TO_USER and not self.shutdown_event.is_set():
                 self._set_state(STATE_PROCESSING_USER_SPEECH)

    async def _receive_agent_output(self):
        if not self.websocket or self.shutdown_event.is_set():
            return

        try:
            self.audio_stream_out = sd.RawOutputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype='int16'
            )
        except Exception as e_out_setup:
            print(f"Error setting up output audio stream: {e_out_setup}")
            return
        
        try:
            async for message in self.websocket:
                if self.shutdown_event.is_set() or not self.websocket or not self.websocket.open:
                    break

                if isinstance(message, bytes):
                    if self.current_state != STATE_AGENT_SPEAKING:
                        self._set_state(STATE_AGENT_SPEAKING)
                        if self.audio_stream_out:
                            try: 
                                self.audio_stream_out.start()
                            except Exception as e_start_out:
                                print(f"Error starting output stream: {e_start_out}")
                                self.keep_recording = False; break
                        self.keep_recording = False # Stop our mic recording if agent speaks
                    
                    if self.audio_stream_out and len(message) > 0:
                        try:
                            self.audio_stream_out.write(message)
                        except Exception as e_write_out:
                            print(f"Error writing to output stream: {e_write_out}")
                            break # Stop trying to play audio if stream fails
                elif isinstance(message, str):
                    print(f"Received text message from WebSocket: {message}")
                    # Potentially handle control messages from ElevenLabs here
                    # if message_obj.get("event") == "conversation_end": self.keep_recording = False; break

        except websockets.exceptions.ConnectionClosed:
            if not self.shutdown_event.is_set():
                print("WebSocket closed while receiving agent output.")
        except Exception as e:
            if not self.shutdown_event.is_set():
                print(f"Error receiving agent output: {e}")
        finally:
            if self.audio_stream_out:
                try:
                    self.audio_stream_out.stop()
                except Exception as e_stop_out:
                    print(f"Error stopping output stream in _receive_agent_output finally: {e_stop_out}")
                self.audio_stream_out = None
            print("Agent output processing finished.")
            # State transition back to IDLE is handled by handle_wake_word()'s finally block

    def run(self):
        """Main loop for the CLI application."""
        print("Starting Voice Assistant. Press Ctrl+C to exit.")
        try:
            while not self.shutdown_event.is_set():
                # Main thread can sleep or do other minimal work here
                # The action happens in porcupine_thread and asyncio_thread
                time.sleep(1)
        except KeyboardInterrupt:
            print("Ctrl+C received, shutting down...")
        finally:
            self.shutdown()

    def shutdown(self):
        print("Shutting down application...")
        self.shutdown_event.set() # Signal all threads to stop
        self.keep_recording = False

        if self.porcupine:
            self.porcupine.delete()
            print("Porcupine resources released.")

        # Porcupine thread is daemon, should exit when main thread exits or shutdown_event is set

        if self.asyncio_loop:
            if self.websocket and self.websocket.open:
                asyncio.run_coroutine_threadsafe(self.websocket.close(), self.asyncio_loop)
            
            self.asyncio_loop.call_soon_threadsafe(self.asyncio_loop.stop)
            if self.asyncio_thread and self.asyncio_thread.is_alive():
                 print("Waiting for asyncio thread to join...")
                 self.asyncio_thread.join(timeout=3)
                 if self.asyncio_thread.is_alive():
                     print("Asyncio thread did not join cleanly.")
            print("Asyncio loop stopped.")

        # Audio streams should be closed by their respective methods' finally blocks
        # or by the shutdown_event check.

        print("Application closed.")

if __name__ == "__main__":
    if not all([PICOVOICE_ACCESS_KEY, ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID]):
        print("CRITICAL ERROR: Missing one or more required environment variables:")
        if not PICOVOICE_ACCESS_KEY: print("- PICOVOICE_ACCESS_KEY")
        if not ELEVENLABS_API_KEY: print("- ELEVENLABS_API_KEY")
        if not ELEVENLABS_AGENT_ID: print("- ELEVENLABS_AGENT_ID")
        print("Please create a .env file with these values or set them in your environment. Exiting.")
        exit(1)

    app = VoiceApp()
    app.run() # Start the main application loop 