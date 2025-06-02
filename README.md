# 🤖 Personal AI Assistant: Your Conversational Super-Agent 🚀

Welcome to your Personal AI Assistant! This isn't just another chatbot; it's a powerful, multi-agent system designed to be your knowledgeable and conversational friend. It understands your needs, remembers your preferences, and can call upon a team of specialized AI agents to perform a wide variety of tasks – from searching the web and writing code to analyzing images and even accessing your webcam (with your permission!).

Built with flexibility in mind, you can choose to power its intelligence with cutting-edge OpenAI models or run it locally using Ollama for greater privacy and control.

## ✨ Core Philosophy

-   **🗣️ Conversational & Friendly**: Interacts naturally, like a close friend who's always ready to help.
-   **🧠 Intelligent Routing**: The Master Agent understands your query and delegates to the best specialized agent.
-   **🧩 Modular Agents**: A suite of agents, each with a specific skill set, working in harmony.
-   **🔧 Extensible**: Designed to easily incorporate new agents and capabilities.
-   **💻 Choice of LLM**: Supports both OpenAI (cloud) and Ollama (local) language models.
-   **🔊 Voice Enabled**: Can respond with voice output for a more engaging experience (powered by OpenAI TTS by default).

## 🚀 Getting Started

### Prerequisites

-   Python 3.11 or higher.
-   `pip` for installing Python packages.
-   **Environment Variables & API Keys (Crucial!):**
    -   An **OpenAI API Key**: Required for the OpenAI LLM provider, embeddings, and the default Text-to-Speech (TTS) service.
    -   **For Web Search (Search Agent):**
        -   A Google API Key.
        -   A Google Programmable Search Engine ID.
    -   **For Weather Agent:**
        -   An OpenWeatherMap API Key.
    -   **macOS Specifics (for Camera/Screen Agents):** You may need to grant your terminal/Python application permission to access the camera and screen recording in `System Settings > Privacy & Security`.

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/DannyRuchtie/Agents.git
    cd Agents
    ```

2.  **Create and Activate a Virtual Environment:**
    (Recommended to avoid conflicts with global packages)
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    *(On Windows, use `.venv\Scripts\activate`)*

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure `ollama` is listed in `requirements.txt` if you plan to use it).*

### Configuration

1.  **Set Up Environment Variables (`.env` file):**
    Create a `.env` file in the root directory of the project:
    ```bash
    touch .env
    ```
    Add the following necessary API keys. Replace placeholder values with your actual keys:

    ```env
    # For OpenAI LLM Provider, Embeddings, and TTS
    OPENAI_API_KEY="your_openai_api_key_here"

    # For Search Agent (Google Custom Search)
    GOOGLE_API_KEY="your_google_api_key_here"
    GOOGLE_CSE_ID="your_google_programmable_search_engine_id_here"

    # For Weather Agent (OpenWeatherMap)
    OPENWEATHERMAP_API_KEY="your_openweathermap_api_key_here"
    ```
    **Important**: Never commit your `.env` file to version control. The `.gitignore` file should already be configured to ignore it.

2.  **Ollama Setup (if using as your LLM provider):**
    -   Ensure the Ollama application is running locally.
    -   Pull your desired model. The default configured in the app for Ollama is `gemma3:4b-it-q4_K_M`, but you can change this in `config/settings.py` (`LLM_PROVIDER_SETTINGS["ollama_default_model"]`).
        ```bash
        ollama pull gemma3:4b-it-q4_K_M
        # Or list your local models:
        ollama list
        ```

3.  **LLM Provider Selection (Runtime):**
    You choose your LLM provider when running the assistant. The default is Ollama. See "Running the Assistant" below.

4.  **Application Settings (`config/settings.py` & `config/settings.json`):**
    Advanced settings like agent enablement, default LLM models for each provider, voice preferences (TTS provider, specific voice model), and personality traits are managed in `config/settings.py`. These settings are saved to and loaded from `config/settings.json` at runtime. You can modify `config/settings.json` directly for persistent changes, or edit the defaults in `config/settings.py` (which will apply if `config/settings.json` is missing or doesn't contain a specific setting).

## 🚀 Running the Assistant

Navigate to the project's root directory in your terminal (ensure your virtual environment is activated).

-   **To run with the default LLM provider (currently Ollama):**
    ```bash
    python main.py
    ```

-   **To explicitly specify Ollama:**
    ```bash
    python main.py --llm ollama
    ```

-   **To run with OpenAI:**
    ```bash
    python main.py --llm openai
    ```

You'll see a welcome message and a `You:` prompt.

## 🗣️ Basic Usage

-   Simply type your questions or commands and press Enter.
-   **Exit:** Type `exit` to close the assistant.
-   **Help:** Type `help` to see a list of available commands (note: command parsing is handled in `main.py`'s `process_input` function; enhance this to add more commands).
-   **Voice Output:**
    -   Voice output is **disabled by default**.
    -   You can toggle it using commands like `voice on` / `voice off` (if implemented and recognized in `main.py`).
    -   The default TTS provider is OpenAI. Voice preferences (e.g., OpenAI voice model like "alloy", "nova") are set in `config/settings.py` under `VOICE_SETTINGS`.
-   **Speech Input (STT) - Local Whisper:**
    -   (Removed: No longer available)
-   **Wake Word Detection (Picovoice Porcupine):**
    -   (Removed: No longer available)

## 🛠️ Meet the Agents: Your Specialist Team

The heart of the assistant is its modular agent system, orchestrated by the Master Agent.

| Icon | Agent             | Description                                                                                                                               |
| :--- | :---------------- | :---------------------------------------------------------------------------------------------------------------------------------------- |
| 🎩   | **Master Agent**  | The conductor! Handles general chat, understands your intent, and routes tasks to the best specialist.                                      |
| 💾   | **Memory Agent**  | Your personal archivist. Remembers personal info, preferences, and past conversations to tailor interactions. (Always active)              |
| 🔍   | **Search Agent**  | Your window to the web. Performs intelligent searches for up-to-date information. (Requires Google API Key & CSE ID)                      |
| ✍️   | **Writer Agent**  | Your personal wordsmith. Assists with composing emails, summaries, creative text, and more.                                               |
| 💻   | **Code Agent**    | Your coding partner. Helps with programming tasks, writing code, debugging, and explaining code snippets.                                 |
| 📸   | **Camera Agent**  | Your digital eyes. Captures images from your webcam (with permission) and uses the Vision Agent to describe them. (macOS may need permissions) |
| 🖼️   | **Vision Agent**  | Your image interpreter. Analyzes and understands explicitly provided image files or paths.                                                |
| 🖥️   | **Screen Agent**  | Your screen reader. Captures your live screen content and describes it using the Vision Agent. (macOS may need permissions)               |
| 📄   | **Scanner Agent** | Your document analyst. Scans and analyzes files/documents for information (can be configured for vector embeddings).                      |
| 🧠   | **Learning Agent**| The self-improver. Learns from interactions to enhance responses and system performance over time.                                       |
| ☀️   | **Weather Agent** | Your local meteorologist. Fetches current weather conditions and forecasts. (Requires OpenWeatherMap API Key)                             |
| ⏰   | **Time Agent**    | The timekeeper. Provides the current date and time.                                                                                       |
| ➕   | **Calculator Agent**| The number cruncher. Handles mathematical calculations and evaluates expressions.                                                       |
| 📧   | **Email Agent**   | Your mail assistant. Can connect to Gmail to check for new emails. (Requires setup/authorization, functionality may be evolving)        |
| 😊   | **Personality Agent**| The empath. Analyzes interactions to understand and adapt to your personality and communication style.                                 |

*(Agent availability can be configured in `config/settings.py` or `config/settings.json`)*

## 🔬 Agent Capabilities in Detail

Here's a closer look at what some key agents can do:

### 🎩 Master Agent
The Master Agent is the primary interface you interact with. It uses a powerful language model (OpenAI or Ollama) to:
-   Understand your queries in natural language.
-   Engage in general conversation and direct Q&A.
-   Determine the best specialized agent to handle a specific request based on its capabilities.
-   Present the specialist agent's findings to you in a cohesive, friendly manner.

### 💾 Memory Agent
This agent is crucial for making the assistant feel personal and aware.
-   **Stores Information**: You can explicitly tell the assistant things to remember about you, your family, preferences, or any facts. It can also learn some details implicitly.
-   **Retrieves Information**: When relevant, the assistant (via the Master Agent or other agents) can query the Memory Agent to recall stored information, making conversations more contextual and personalized (e.g., remembering your kids' names, your favorite hobbies, or a project you were working on).
-   **Data Storage**: Currently, memories are stored locally in `agent_memory.json` (ensure this is in `.gitignore`). The structure allows for different types of memories (facts, conversation summaries, etc.).
-   **Example**: *"Remember that my wife Kiki's birthday is on August 15th."* Later: *"When is Kiki's birthday?"*

### 🔍 Search Agent
Leverages Google Custom Search to find information online.
-   **Setup**: Requires `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` in your `.env` file.
-   **Functionality**: Takes your query, performs a web search, and then often uses its LLM to synthesize the search results into a concise answer. It can provide sources for its information.
-   **Example**: *"What are the latest developments in quantum computing?"*

### ✍️ Writer Agent
Your go-to for text generation and manipulation.
-   **Capabilities**: Can draft emails, write summaries of text, generate creative content (poems, stories), rewrite text in a different tone, and more.
-   **Example**: *"Write a short, friendly email to my team reminding them about the deadline on Friday."*

### 💻 Code Agent
Provides assistance with programming.
-   **Features**: Can generate code snippets in various languages, explain existing code, help debug, and answer programming-related questions.
-   **Example**: *"Write a Python function that takes a list of numbers and returns the sum of all even numbers in the list."*

### 📸 Camera Agent & 🖼️ Vision Agent & 🖥️ Screen Agent
These three agents work together for visual understanding:
-   **Vision Agent**: The core image analysis engine. It takes an image (from a file path, a live capture, or a screen grab) and a prompt, then uses a vision-capable LLM (like GPT-4.1 Vision with OpenAI, or a multi-modal Ollama model if configured) to describe or answer questions about the image.
-   **Camera Agent**: Uses your webcam to capture a live image. It then passes this image to the Vision Agent for analysis. *Requires webcam access and system permissions.*
    -   **Example**: *"Can you see me with the camera and describe what I'm wearing?"*
-   **Screen Agent**: Captures your current computer screen. It then sends this screenshot to the Vision Agent for analysis. *Requires screen recording permissions.*
    -   **Example**: *"Describe what's on my screen right now."* or *"Read the error message on my screen."*

### ☀️ Weather Agent
Provides weather forecasts using the OpenWeatherMap API.
-   **Setup**: Requires an `OPENWEATHERMAP_API_KEY` in your `.env` file.
-   **Functionality**: You can ask for the weather in a specific location. If you have a default location stored in memory (e.g., by telling the Memory Agent: *"Remember my default location is London."*), it can use that.
-   **Example**: *"What's the weather like in Paris today?"* or (if default is set) *"What's the weather like?"*

*(More detailed sections for other agents can be added here as needed.)*


## 🤝 Contributing

Contributions are welcome! Whether it's adding new agents, improving existing functionality, enhancing documentation, or fixing bugs, please feel free to fork the repository, make your changes, and submit a pull request.

## 📜 License

This project is typically licensed under the MIT License (but please verify the `LICENSE` file in the repository).

---

*This README aims to be a comprehensive guide. If you find inaccuracies or areas for improvement, please contribute!*

## Personality Settings

The assistant's personality can be customized:
```bash
# Adjust humor level (0.0 to 1.0)
set humor 0.7

# Set formality level (0.0 to 1.0)
set formality 0.3

# Toggle personality traits
toggle trait [witty/empathetic/curious/enthusiastic]

# Control emoji usage
toggle emoji [on/off]
```

## Security Notes

- API keys (OpenAI and Google) are stored locally in your .env file
- All document processing happens on your machine
- Memory storage is local and under your control
- Web access is configurable and can be restricted
- Voice synthesis is performed locally using kokoro-onnx
- Rate limiting is enabled by default to prevent API abuse

## Contributing

This is an evolving project, and contributions are welcome! Whether it's adding new agents, improving existing functionality, or enhancing documentation, please feel free to submit pull requests.


## License

MIT License - See LICENSE file for details

---

