import sounddevice as sd
import numpy as np
import threading
import queue
import time
import pvporcupine
import httpx # For explicit proxy handling with OpenAI client
from typing import Optional, Callable, List
from config.settings import VOICE_SETTINGS, debug_print, SYSTEM_SETTINGS
from pathlib import Path
import soundfile as sf
from datetime import datetime
import struct
import wave
import os
from collections import deque
import openai # Added for OpenAI STT
import inspect # For inspecting class signature

# Audio settings
SAMPLE_RATE = 16000  # Whisper models are trained on 16kHz audio
WHISPER_CHANNELS = 1 # Whisper expects mono
# Porcupine needs specific frame length, will get from instance

class SpeechToText:
    def __init__(self, wake_word_callback: Optional[Callable[[str], None]] = None):
        self.stt_provider = VOICE_SETTINGS.get("stt_provider", "openai_api") # Default to openai_api
        self.openai_client = None

        if self.stt_provider == "openai_api":
            try:
                # ---- START DEBUG INSPECTION ----
                try:
                    sig = inspect.signature(openai.OpenAI.__init__)
                    debug_print(f"[STT DEBUG] openai.OpenAI.__init__ signature: {sig}")
                    if 'proxies' in sig.parameters:
                        debug_print("[STT DEBUG] 'proxies' IS an expected parameter in openai.OpenAI.__init__ based on inspection!")
                    else:
                        debug_print("[STT DEBUG] 'proxies' is NOT an expected parameter in openai.OpenAI.__init__ based on inspection.")
                except Exception as inspect_e:
                    debug_print(f"[STT DEBUG] Error inspecting openai.OpenAI.__init__: {inspect_e}")
                # ---- END DEBUG INSPECTION ----

                # Explicitly create a synchronous httpx client with no proxies
                sync_http_client = httpx.Client(proxies=None)
                self.openai_client = openai.OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    http_client=sync_http_client
                )
                if self.openai_client.api_key:
                    debug_print("OpenAI sync client initialized for STT with API key and no proxies.")
                else:
                    debug_print("[STT Warning] OpenAI client initialized but API key seems missing/empty after init.")
                    # This might still lead to issues later, but the client object might exist.
            except Exception as e:
                print(f"Error initializing OpenAI client for STT: {e}")
                # If OpenAI fails, STT won't work. Consider a hard failure or notification.
                self.openai_client = None # Ensure it's None
                print("[STT Critical Error] Failed to initialize OpenAI client. STT will not be available.")
        else:
            # This case should ideally not be reached if configuration is always openai_api
            # Or if local_whisper was an option, it's now removed.
            print(f"[STT Warning] STT provider is set to '{self.stt_provider}', but only 'openai_api' is supported in this version. Attempting to use OpenAI API.")
            self.stt_provider = "openai_api" # Force to openai_api
            try:
                sync_http_client = httpx.Client(proxies=None)
                self.openai_client = openai.OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    http_client=sync_http_client
                )
                if self.openai_client.api_key:
                    debug_print("OpenAI sync client initialized for STT with API key (forced fallback) and no proxies.")
                else:
                    debug_print("[STT Warning] OpenAI client initialized (forced fallback) but API key seems missing/empty after init.")
            except Exception as e:
                print(f"Error initializing OpenAI client for STT (forced fallback): {e}")
                self.openai_client = None
                print("[STT Critical Error] Failed to initialize OpenAI client. STT will not be available.")

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
        """Captures audio for a short duration and transcribes using the configured STT provider."""
        debug_print(f"[STT DEBUG] _capture_and_transcribe_command called. Provider: {self.stt_provider}")
        if self.stt_provider != "openai_api" or not self.openai_client:
            print("OpenAI client not initialized or provider not set to openai_api. Cannot transcribe command via API.")
            return None

        self.audio_queue = queue.Queue() # Clear queue for new command
        recorded_data = []
        self.last_sound_time = time.time()
        self.is_capturing_command = True # Ensure this is true for the callback

        print(f"🎙️  Listening for command... (Provider: {self.stt_provider}, Silence: {silence_timeout}s, Max: {phrase_limit}s)")

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
            debug_print("[STT _capture] No command audio data recorded.")
            print("No command speech detected after wake word.")
            return None

        num_chunks = len(recorded_data)
        if num_chunks > 0:
            total_frames = sum(chunk.shape[0] for chunk in recorded_data)
            estimated_duration = total_frames / SAMPLE_RATE
            debug_print(f"[STT _capture] Recorded {num_chunks} audio chunks. Total frames: {total_frames}. Estimated duration: {estimated_duration:.2f}s.")
            debug_print(f"[STT _capture] First chunk shape: {recorded_data[0].shape}, dtype: {recorded_data[0].dtype}")
        else: 
            debug_print("[STT _capture] recorded_data is empty after loop - unexpected.")
            return None

        debug_print(f"[STT _capture] Preparing to concatenate audio chunks...")
        try:
            full_audio = np.concatenate(recorded_data, axis=0)
            debug_print(f"[STT _capture] Audio concatenated. Shape: {full_audio.shape}, Dtype: {full_audio.dtype}. Approx size: {full_audio.nbytes / (1024*1024):.2f} MB.")
        except Exception as e:
            debug_print(f"[STT _capture] ERROR during np.concatenate: {e}")
            for i, chunk in enumerate(recorded_data):
                debug_print(f"[STT _capture] Chunk {i} shape: {chunk.shape}, dtype: {chunk.dtype}")
            return None

        print("Command audio recording complete and concatenated. Transcribing with Whisper...")

        # --- Save concatenated audio for debugging ---
        try:
            temp_audio_dir = Path(SYSTEM_SETTINGS.get("app_path", ".")) / "temp_audio"
            temp_audio_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_filename = temp_audio_dir / f"command_concatenated_audio_{timestamp}.wav"
            sf.write(str(debug_filename), full_audio, SAMPLE_RATE)
            debug_print(f"[STT _capture] Command audio (concatenated) saved to {debug_filename}")
        except Exception as e:
            debug_print(f"[STT _capture] Error saving concatenated command audio: {e}")
        # --- End save audio for debugging ---

        debug_print(f"[STT _capture] Calling {self.stt_provider} to transcribe audio...")

        try:
            # OpenAI API expects a file-like object. We'll use the saved .wav file.
            # If the file wasn't saved, this will fail. Consider in-memory option if possible or ensure saving.
            if not debug_filename or not debug_filename.exists():
                print("[STT Error] OpenAI API needs audio file, but it wasn't saved or found.")
                return None
            
            with open(debug_filename, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model=VOICE_SETTINGS.get("openai_stt_model", "whisper-1"),
                    file=audio_file
                )
            transcribed_text = transcript.text.strip()
            debug_print(f"OpenAI API transcription of command: '{transcribed_text}'")

            if not transcribed_text or len(transcribed_text) < 1: 
                 print("Command transcription too short or empty.")
                 return None
            return transcribed_text
        except Exception as e:
            print(f"Error during command transcription with {self.stt_provider}: {e}")
            return None

    # This is the original method, now primarily for the 'listen' command
    def listen_and_transcribe_once(self) -> Optional[str]: 
        if self.stt_provider != "openai_api" or not self.openai_client:
            print("OpenAI client not initialized or provider not set to openai_api. Cannot transcribe.")
            return None

        self.audio_queue = queue.Queue()
        recorded_data = []
        self.last_sound_time = time.time()
        
        phrase_time_limit = VOICE_SETTINGS.get("stt_phrase_time_limit", 10)
        silence_timeout = VOICE_SETTINGS.get("stt_silence_timeout", 2)

        print(f"\n🎙️  Listening for single command... (Provider: {self.stt_provider}, Model: {VOICE_SETTINGS.get('openai_stt_model', 'whisper-1')}, Timeout: {silence_timeout}s silence, Max: {phrase_time_limit}s phrase)")
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
                    if (current_time - start_time) > phrase_time_limit:
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

        # --- Save audio for OpenAI API if needed ---
        saved_for_openai_path = None
        if self.stt_provider == "openai_api":
            try:
                temp_audio_dir = Path(SYSTEM_SETTINGS.get("app_path", ".")) / "temp_audio"
                temp_audio_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                openai_filename = temp_audio_dir / f"onetime_command_openai_{timestamp}.wav"
                sf.write(str(openai_filename), full_audio, SAMPLE_RATE)
                saved_for_openai_path = openai_filename
                debug_print(f"[STT listen_once] Audio for OpenAI API saved to {openai_filename}")
            except Exception as e:
                debug_print(f"[STT listen_once] Error saving audio for OpenAI API: {e}")
                print("Error saving audio file for OpenAI. Cannot transcribe.")
                return None
        # --- End save audio ---

        try:
            if not saved_for_openai_path or not saved_for_openai_path.exists():
                print("[STT Error] OpenAI API needs audio file for one-time listen, but it wasn't saved or found.")
                return None
            with open(saved_for_openai_path, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model=VOICE_SETTINGS.get("openai_stt_model", "whisper-1"),
                    file=audio_file
                )
            transcribed_text = transcript.text.strip()
            debug_print(f"Transcription result (one-time, OpenAI API): '{transcribed_text}'")
            # Clean up the temp file after successful transcription by OpenAI
            try:
                os.remove(saved_for_openai_path)
                debug_print(f"Cleaned up temp audio file: {saved_for_openai_path}")
            except Exception as e:
                debug_print(f"Error cleaning up temp audio file {saved_for_openai_path}: {e}")
                
            if not transcribed_text or len(transcribed_text) < 1:
                 print("Transcription (one-time) too short or empty.")
                 return None
            print(f"You said: {transcribed_text}") 
            return transcribed_text
        except Exception as e:
            print(f"Error during one-time transcription with {self.stt_provider}: {e}")
            # If OpenAI API was used and file was saved, clean it up on error too
            if self.stt_provider == "openai_api" and saved_for_openai_path and saved_for_openai_path.exists():
                 try:
                    os.remove(saved_for_openai_path)
                    debug_print(f"Cleaned up temp audio file on error: {saved_for_openai_path}")
                 except Exception as e_clean:
                    debug_print(f"Error cleaning up temp audio file {saved_for_openai_path} on error: {e_clean}")
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

def reset_stt_instance():
    """Resets the global STT instance so a new one can be created."""
    global stt_instance
    if stt_instance:
        stt_instance.release_resources() # Ensure old one is cleaned up if not already
        stt_instance = None
        debug_print("Global STT instance reset.")

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
    VOICE_SETTINGS["stt_provider"] = "local_whisper" # For testing local whisper in __main__
    # VOICE_SETTINGS["stt_provider"] = "openai_api" # For testing OpenAI API in __main__

    if not VOICE_SETTINGS["picovoice_access_key"] and VOICE_SETTINGS["wakeword_enabled"]:
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

    # Ensure temp_audio directory exists
    temp_audio_dir = Path(SYSTEM_SETTINGS.get("app_path", ".")) / "temp_audio"
    try:
        temp_audio_dir.mkdir(parents=True, exist_ok=True)
        print(f"Ensured temp_audio directory exists at {temp_audio_dir}")
    except Exception as e:
        print(f"Error creating temp_audio directory: {e}")

    # These lines seem to be from a previous version of the test block and cause errors
    # print(f"Audio recording stopped after {stt.audio_frames_for_command} frames.")

    # # Save the recorded audio to a temporary file for debugging
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # temp_file_path = temp_audio_dir / f"recorded_audio_{timestamp}.wav"
    # sf.write(temp_file_path, stt.recorded_audio, samplerate=SAMPLE_RATE)
    # print(f"Recorded audio saved to: {temp_file_path}") 