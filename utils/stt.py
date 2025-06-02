import whisper
import sounddevice as sd
import numpy as np
import threading
import queue
import time
import pvporcupine
from typing import Optional, Callable, List
from config.settings import VOICE_SETTINGS, debug_print

# Audio settings
SAMPLE_RATE = 16000  # Whisper models are trained on 16kHz audio
WHISPER_CHANNELS = 1 # Whisper expects mono
# Porcupine needs specific frame length, will get from instance

class SpeechToText:
    def __init__(self, wake_word_callback: Optional[Callable[[str], None]] = None):
        # Whisper STT Model
        self.whisper_model_name = VOICE_SETTINGS.get("whisper_model", "tiny.en")
        self.whisper_device = VOICE_SETTINGS.get("whisper_device", "cpu")
        self.whisper_model = None
        self._load_whisper_model()

        # Picovoice Porcupine Wake Word Engine
        self.picovoice_access_key = VOICE_SETTINGS.get("picovoice_access_key")
        self.keyword_paths = VOICE_SETTINGS.get("picovoice_keyword_paths", [])
        self.keywords = VOICE_SETTINGS.get("picovoice_keywords", ["porcupine"])
        self.sensitivities = VOICE_SETTINGS.get("picovoice_sensitivities", [0.5])
        self.porcupine = None
        self.porcupine_frame_length = None # Will be set by porcupine instance
        self.porcupine_sample_rate = None # Will be set by porcupine instance
        self._init_porcupine()

        self.is_listening_for_wake_word = False
        self.is_capturing_command = False # True after wake word is detected
        self.audio_queue = queue.Queue() # Used by Whisper for command capture
        self.last_sound_time = time.time()
        
        self.wake_word_thread = None
        self.stop_wake_word_event = threading.Event()
        self.wake_word_callback = wake_word_callback

    def _load_whisper_model(self):
        try:
            debug_print(f"Loading Whisper model: {self.whisper_model_name} on device: {self.whisper_device}")
            self.whisper_model = whisper.load_model(self.whisper_model_name, device=self.whisper_device)
            debug_print("Whisper model loaded successfully.")
        except Exception as e:
            print(f"Error loading Whisper model '{self.whisper_model_name}': {e}")
            self.whisper_model = None

    def _init_porcupine(self):
        if not VOICE_SETTINGS.get("wakeword_enabled", False) or not self.picovoice_access_key:
            debug_print("Wake word disabled or no Picovoice AccessKey. Porcupine not initialized.")
            return
        try:
            keyword_args = {}
            if self.keyword_paths and len(self.keyword_paths) > 0:
                keyword_args["keyword_paths"] = self.keyword_paths
            elif self.keywords and len(self.keywords) > 0:
                # Check if these are built-in keywords
                valid_builtins = [k for k in self.keywords if k in pvporcupine.KEYWORDS]
                invalid_builtins = [k for k in self.keywords if k not in pvporcupine.KEYWORDS]
                if invalid_builtins:
                    print(f"[STT Warning] Invalid built-in Porcupine keywords specified: {invalid_builtins}. They will be ignored.")
                if not valid_builtins:
                    print("[STT Error] No valid Porcupine built-in keywords or custom keyword_paths provided. Wake word detection cannot start.")
                    return
                keyword_args["keywords"] = valid_builtins
            else:
                print("[STT Error] Porcupine requires either keyword_paths or keywords. Wake word detection cannot start.")
                return

            debug_print(f"Initializing Porcupine with: AccessKey set, Keywords/Paths: {keyword_args}, Sensitivities: {self.sensitivities}")
            self.porcupine = pvporcupine.create(
                access_key=self.picovoice_access_key,
                **keyword_args,
                sensitivities=self.sensitivities
            )
            self.porcupine_frame_length = self.porcupine.frame_length
            self.porcupine_sample_rate = self.porcupine.sample_rate
            debug_print(f"Porcupine initialized. Frame length: {self.porcupine_frame_length}, Sample rate: {self.porcupine_sample_rate}")
            # Ensure Whisper sample rate matches Porcupine if both are active
            # This example assumes Whisper will use its default (16kHz) and Porcupine will match or resample.
            # For robust integration, audio pipeline should ensure correct sample rates.
            if self.porcupine_sample_rate != SAMPLE_RATE:
                print(f"[STT Warning] Porcupine sample rate ({self.porcupine_sample_rate} Hz) differs from Whisper ({SAMPLE_RATE} Hz). This might affect performance or require resampling.")

        except pvporcupine.PorcupineError as e:
            print(f"Porcupine initialization error: {e}")
            print("Ensure your Picovoice AccessKey is valid and keyword paths/names are correct.")
            self.porcupine = None
        except Exception as e:
            print(f"An unexpected error occurred during Porcupine initialization: {e}")
            self.porcupine = None

    def _wake_word_audio_callback(self, indata, frames, time_info, status):
        """Callback for Porcupine: feeds audio frames directly to Porcupine."""
        if status:
            print(f"[Wake Word Audio Callback Warning] {status}")
        # This callback directly processes audio with Porcupine in the main wake word loop.
        # For now, this is just a placeholder if we need to queue raw audio for Porcupine
        # but the typical Picovoice examples read from a stream in a loop.
        pass # Audio is read and processed in the _run_wake_word_detection_loop

    def _command_capture_audio_callback(self, indata, frames, time_info, status):
        """Callback for Whisper: queues audio data after wake word is detected."""
        if status:
            print(f"[Command Capture Audio Callback Warning] {status}")
        if self.is_capturing_command:
            volume_norm = np.linalg.norm(indata) * 10
            if volume_norm > 0.1: # Basic VAD
                self.last_sound_time = time.time()
            self.audio_queue.put(indata.copy())

    def start_wake_word_listening(self):
        if not VOICE_SETTINGS.get("wakeword_enabled", False):
            print("Wake word is not enabled in settings.")
            return
        if not self.porcupine:
            print("Porcupine not initialized. Cannot start wake word listening.")
            # Attempt to re-initialize if settings might have changed (e.g. access key added)
            self._init_porcupine()
            if not self.porcupine:
                 print("Re-initialization of Porcupine failed.")
                 return

        if self.wake_word_thread is not None and self.wake_word_thread.is_alive():
            print("Wake word listening is already active.")
            return

        self.stop_wake_word_event.clear()
        self.wake_word_thread = threading.Thread(target=self._run_wake_word_detection_loop, daemon=True)
        self.wake_word_thread.start()
        print("🎤 Wake word detection started...")

    def stop_wake_word_listening(self):
        if self.wake_word_thread is not None and self.wake_word_thread.is_alive():
            self.stop_wake_word_event.set()
            # self.wake_word_thread.join(timeout=2) # Wait for thread to finish
            if self.wake_word_thread.is_alive():
                 debug_print("Wake word thread did not stop in time.")
            else:
                 debug_print("Wake word thread stopped.")
        self.is_listening_for_wake_word = False # Ensure this is reset
        self.is_capturing_command = False
        print("Wake word detection stopped.")
        # Release Porcupine resources if no longer needed or on app exit
        # if self.porcupine:
        #     self.porcupine.delete()
        #     self.porcupine = None
        #     debug_print("Porcupine resources released.")

    def _run_wake_word_detection_loop(self):
        if not self.porcupine:
            debug_print("Porcupine not available in _run_wake_word_detection_loop")
            return

        self.is_listening_for_wake_word = True
        pcm = None # Define pcm before the loop

        try:
            # Using sounddevice.InputStream directly for reading frames
            with sd.InputStream(
                samplerate=self.porcupine_sample_rate,
                channels=1, # Porcupine expects mono
                dtype='int16', # Porcupine expects 16-bit PCM
                blocksize=self.porcupine_frame_length
            ) as stream:
                debug_print(f"Listening for wake word(s): {self.keywords or self.keyword_paths} with Porcupine...")
                while not self.stop_wake_word_event.is_set():
                    pcm, overflowed = stream.read(self.porcupine_frame_length)
                    if overflowed:
                        debug_print("[Wake Word Warning] Input audio overflowed!")
                    
                    if pcm is None or len(pcm) == 0: # Should not happen with stream.read
                        time.sleep(0.01) # Prevent tight loop on error
                        continue

                    # Convert to list of int if necessary (pvporcupine expects list of int16)
                    # pcm_list = pcm.flatten().tolist()
                    
                    keyword_index = self.porcupine.process(pcm.flatten())

                    if keyword_index >= 0:
                        detected_keyword_list = self.keywords if self.keywords and len(self.keywords) > keyword_index else self.keyword_paths
                        detected_keyword = detected_keyword_list[keyword_index] if detected_keyword_list and len(detected_keyword_list) > keyword_index else "Unknown Keyword"
                        print(f"\n✨ Wake word '{detected_keyword}' detected! Listening for command...")
                        self.is_listening_for_wake_word = False # Pause wake word detection
                        self.is_capturing_command = True
                        
                        # Capture and transcribe command after wake word
                        # Using the existing listen_and_transcribe logic but with specific timeout for post-wake-word
                        command_text = self._capture_and_transcribe_command(
                            silence_timeout=VOICE_SETTINGS.get("wakeword_post_silence_timeout", 3),
                            phrase_limit=VOICE_SETTINGS.get("wakeword_post_phrase_time_limit", 7)
                        )
                        
                        self.is_capturing_command = False
                        if command_text and self.wake_word_callback:
                            self.wake_word_callback(command_text)
                        
                        # Resume wake word listening
                        debug_print("Resuming wake word detection...")
                        self.is_listening_for_wake_word = True
                        # Clear any residual audio in Porcupine (not explicitly needed with frame-by-frame)
                        # Re-prime last_sound_time for Whisper VAD if used in command capture
                        self.last_sound_time = time.time() 

        except Exception as e:
            print(f"Error in wake word detection loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_listening_for_wake_word = False
            debug_print("Exited wake word detection loop.")

    def _capture_and_transcribe_command(self, silence_timeout: int, phrase_limit: int) -> Optional[str]:
        """Captures audio for a short duration and transcribes using Whisper."""
        if not self.whisper_model:
            print("Whisper model not loaded. Cannot transcribe command.")
            return None

        self.audio_queue = queue.Queue() # Clear queue for new command
        recorded_data = []
        self.last_sound_time = time.time()
        self.is_capturing_command = True # Ensure this is true for the callback

        print(f"🎙️  Listening for command... (Silence: {silence_timeout}s, Max: {phrase_limit}s)")

        try:
            # Using sounddevice.InputStream for command capture.
            # This means we have two nested streams if wake word is active.
            # This might be problematic. A single audio stream managed by this class would be better.
            # For now, let's proceed, but this is a point for future refactoring.
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=WHISPER_CHANNELS, dtype='float32', callback=self._command_capture_audio_callback):
                start_time = time.time()
                while True: # Loop for command capture duration
                    try:
                        audio_chunk = self.audio_queue.get(timeout=0.1)
                        recorded_data.append(audio_chunk)
                    except queue.Empty:
                        pass

                    current_time = time.time()
                    if (current_time - self.last_sound_time) > silence_timeout:
                        debug_print("Silence detected after wake word, stopping command capture.")
                        break
                    if (current_time - start_time) > phrase_limit:
                        debug_print("Command phrase time limit reached, stopping command capture.")
                        break
                    if self.stop_wake_word_event.is_set(): # If main stop is called
                        debug_print("Global stop event received during command capture.")
                        break
        except Exception as e:
            print(f"Error during command audio recording: {e}")
            return None
        finally:
            self.is_capturing_command = False

        if not recorded_data:
            debug_print("No command audio data recorded.")
            print("No command speech detected after wake word.")
            return None

        print("Command audio recording complete. Transcribing with Whisper...")
        full_audio = np.concatenate(recorded_data, axis=0)

        try:
            result = self.whisper_model.transcribe(full_audio, fp16=(self.whisper_device != 'cpu'))
            transcribed_text = result["text"].strip()
            debug_print(f"Whisper transcription of command: '{transcribed_text}'")
            if not transcribed_text or len(transcribed_text) < 1: # Allow very short commands
                 print("Command transcription too short or empty.")
                 return None
            # No "You said:" here, that will be handled by main.py via callback
            return transcribed_text
        except Exception as e:
            print(f"Error during command transcription: {e}")
            return None

    # This is the original method, now primarily for the 'listen' command
    def listen_and_transcribe_once(self) -> Optional[str]: # Renamed from listen_and_transcribe
        if not self.whisper_model:
            print("Whisper model not loaded. Cannot transcribe.")
            return None

        self.audio_queue = queue.Queue()
        recorded_data = []
        self.last_sound_time = time.time()
        # Not setting self.is_capturing_command here, as this is a direct call

        phrase_time_limit = VOICE_SETTINGS.get("stt_phrase_time_limit", 10)
        silence_timeout = VOICE_SETTINGS.get("stt_silence_timeout", 2)

        print(f"\n🎙️  Listening for single command... (Model: {self.whisper_model_name}, Timeout: {silence_timeout}s silence, Max: {phrase_time_limit}s phrase)")
        print("Speak your command.")

        # This callback needs to be distinct or managed if wake word is also active
        # For simplicity, let's assume only one type of listening (wake word or direct) is active at a time
        # or that they use separate audio queue variables if needed.
        # The current design for command capture uses _command_capture_audio_callback which is fine.
        # This method now needs its own way to get audio into its `recorded_data`.
        # Reusing _command_capture_audio_callback means `is_capturing_command` needs to be managed.
        
        temp_is_capturing = self.is_capturing_command
        self.is_capturing_command = True # For the callback to work
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=WHISPER_CHANNELS, dtype='float32', callback=self._command_capture_audio_callback):
                start_time = time.time()
                while True:
                    try:
                        audio_chunk = self.audio_queue.get(timeout=0.1)
                        recorded_data.append(audio_chunk)
                    except queue.Empty:
                        pass

                    current_time = time.time()
                    if (current_time - self.last_sound_time) > silence_timeout:
                        debug_print("Silence detected, stopping one-time listen.")
                        break
                    if (current_time - start_time) > phrase_limit:
                        debug_print("One-time listen phrase time limit reached.")
                        break
                    if self.stop_wake_word_event.is_set(): # Check global stop
                        break
        except Exception as e:
            print(f"Error during one-time audio recording: {e}")
            return None
        finally:
            self.is_capturing_command = temp_is_capturing # Restore previous state

        if not recorded_data:
            debug_print("No audio data for one-time listen.")
            print("No speech detected for one-time listen.")
            return None

        print("One-time audio recording complete. Transcribing...")
        full_audio = np.concatenate(recorded_data, axis=0)

        try:
            result = self.whisper_model.transcribe(full_audio, fp16=(self.whisper_device != 'cpu'))
            transcribed_text = result["text"].strip()
            debug_print(f"Transcription result (one-time): '{transcribed_text}'")
            if not transcribed_text or len(transcribed_text) < 1:
                 print("Transcription (one-time) too short or empty.")
                 return None
            print(f"You said: {transcribed_text}") # This one can print "You said"
            return transcribed_text
        except Exception as e:
            print(f"Error during one-time transcription: {e}")
            return None

    def release_resources(self):
        debug_print("STT service releasing resources.")
        self.stop_wake_word_listening() # Stop thread if running
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
            debug_print("Porcupine resources released.")
        # Whisper model is loaded/unloaded with the class instance or re-init
        # No explicit unload for Whisper model here, Python GC will handle if stt_service is dereferenced.

stt_instance = None

def get_stt_instance(wake_word_callback=None):
    global stt_instance
    if stt_instance is None:
        stt_instance = SpeechToText(wake_word_callback=wake_word_callback)
    elif wake_word_callback is not None and stt_instance.wake_word_callback is None:
        # If instance exists but callback was not set initially
        stt_instance.wake_word_callback = wake_word_callback
    return stt_instance

if __name__ == '__main__':
    print("Running STT example with wake word (if configured and enabled)...")
    # Load .env for PICOVOICE_ACCESS_KEY if running directly
    from dotenv import load_dotenv
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True, verbose=True)
    
    # Update settings directly for test if needed (ensure load_settings() in your app does this from file/env)
    VOICE_SETTINGS["stt_enabled"] = True
    VOICE_SETTINGS["whisper_model"] = "tiny.en"
    VOICE_SETTINGS["whisper_device"] = "cpu"
    VOICE_SETTINGS["wakeword_enabled"] = True # Enable for this test
    VOICE_SETTINGS["picovoice_access_key"] = os.getenv("PICOVOICE_ACCESS_KEY") # Make sure this is loaded
    VOICE_SETTINGS["picovoice_keywords"] = ["porcupine", "bumblebee"] # Test with built-ins
    VOICE_SETTINGS["picovoice_sensitivities"] = [0.6, 0.6]

    if not VOICE_SETTINGS["picovoice_access_key"]:
        print("PICOVOICE_ACCESS_KEY not found in environment for testing. Wake word will not work.")
        VOICE_SETTINGS["wakeword_enabled"] = False

    def handle_wake_word_command(text):
        print(f"\n[MAIN APP SIMULATION] Wake word command received: {text}")
        if text.lower() == "stop listening":
            stt.stop_wake_word_listening()
            print("Stopping main loop due to 'stop listening' command.")
            # In a real app, this might set a global stop event for the main loop
            # For this test, we can try to exit more directly if needed, or just let thread end.
            global main_test_loop_active
            main_test_loop_active = False

    stt = get_stt_instance(wake_word_callback=handle_wake_word_command)

    if VOICE_SETTINGS["wakeword_enabled"] and stt.porcupine:
        stt.start_wake_word_listening()
        print("Wake word engine running. Say 'Porcupine' or 'Bumblebee' then a command (e.g., 'what time is it').")
        print("Say 'stop listening' as a command to end this test.")
        main_test_loop_active = True
        try:
            while main_test_loop_active and stt.is_listening_for_wake_word:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Keyboard interrupt, stopping...")
        finally:
            stt.stop_wake_word_listening()
            stt.release_resources()
            print("STT example finished.")
    elif VOICE_SETTINGS["stt_enabled"] and stt.whisper_model:
        print("Wake word not enabled or Porcupine failed. Testing direct listen-once STT.")
        text = stt.listen_and_transcribe_once()
        if text:
            print(f"Transcription successful (once): {text}")
        else:
            print("Transcription failed or no input (once).")
        stt.release_resources()
    else:
        print("STT (Whisper or Porcupine) could not be initialized for the example.") 