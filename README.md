# Personal AI Assistant: Your Conversational Super-Agent

Welcome to your Personal AI Assistant! This isn't just another chatbot; it's a powerful, multi-agent system designed to be your knowledgeable and conversational friend. It understands your needs, remembers your preferences, and can call upon a team of specialized AI agents to perform a wide variety of tasks – from searching the web and writing code to analyzing images and even accessing your webcam (with your permission!).

Built with flexibility in mind, you can choose to power its intelligence with cutting-edge OpenAI models or run it locally using Ollama for greater privacy and control.

## Core Philosophy

- **Conversational & Friendly**: Interacts naturally, like a close friend who's always ready to help.
- **Intelligent Routing**: The Master Agent understands your query and delegates to the best specialized agent.
- **Modular Agents**: A suite of agents, each with a specific skill set, working in harmony.
- **Extensible**: Designed to easily incorporate new agents and capabilities.
- **Choice of LLM**: Supports both OpenAI (cloud) and Ollama (local) language models.
- **Voice Enabled**: Can respond with voice output for a more engaging experience.

## Meet the Agents

Our assistant coordinates a team of specialized agents:

-   **Master Agent**: The conductor of the orchestra. Handles general conversation, understands your intent, and routes tasks to the appropriate specialist.
-   **Memory Agent**: Remembers your personal information, preferences, and past conversation details to personalize interactions. (Always active)
-   **Search Agent**: Performs intelligent web searches to find up-to-date information.
-   **Writer Agent**: Assists with writing tasks like composing emails, summaries, or creative text.
-   **Code Agent**: Helps with programming tasks, writing code, debugging, and explaining code snippets.
-   **Scanner Agent**: Scans and analyzes files and documents for information or insights.
-   **Vision Agent**: Analyzes and understands explicitly provided image files or image paths.
-   **Camera Agent**: Captures images using your webcam (requires your permission) and uses the Vision Agent to describe what it sees.
-   **Screen Agent**: Captures your current live screen content and describes it using the Vision Agent. Useful for queries like "what am I looking at?"
-   **Learning Agent**: Learns from interactions to improve responses and system performance over time.
-   **Weather Agent**: Fetches current weather conditions and forecasts.
-   **Time Agent**: Provides the current date and time.
-   **Calculator Agent**: Handles mathematical calculations and evaluates expressions.
-   **Email Agent**: Can connect to your Gmail account to check for new emails and (soon) send emails. (Requires setup and authorization)
-   **Personality Agent**: Analyzes interactions to understand and adapt to your personality and communication style.

*(Agent availability can be configured in `config/settings.py` or `config/settings.json`)*

## Getting Started

### Prerequisites

-   Python 3.11 or higher.
-   `pip` for installing Python packages.
-   **For Ollama (Local LLM):**
    -   Ollama installed and running. Download from [ollama.com](https://ollama.com/).
    -   At least one model pulled, e.g., `ollama pull gemma3:4b-it-q4_K_M` (or your preferred model).
-   **For OpenAI (Cloud LLM):**
    -   An OpenAI API key.
-   **For Web Search (Search Agent):**
    -   A Google API Key.
    -   A Google Programmable Search Engine ID.
-   **For Camera/Screen Agents on macOS:** You may need to grant terminal/Python permission to access the camera and screen recording in your System Settings (Privacy & Security).

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/DannyRuchtie/Agents
 
    ```

2.  **Create and Activate a Virtual Environment:**
    (Recommended to avoid conflicts with global packages)
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    *(On Windows, use `.venv\\Scripts\\activate`)*

3.  **Install Dependencies:**
    Ensure your `requirements.txt` is up-to-date, then run:
    ```bash
    pip install -r requirements.txt
    pip install ollama # If not already in requirements.txt
    ```
    *(We'll generate/update `requirements.txt` later if needed)*

### Configuration

1.  **Environment Variables (`.env` file):**
    Create a `.env` file in the root directory of the project by copying the example if provided, or create it manually:
    ```
    touch .env
    ```
    Add the following necessary API keys and configurations:

    ```env
    # For OpenAI LLM Provider & Embeddings
    OPENAI_API_KEY="your_openai_api_key_here"

    # For Search Agent (Google Custom Search)
    GOOGLE_API_KEY="your_google_api_key_here"
    GOOGLE_CSE_ID="your_google_programmable_search_engine_id_here"

    # Other optional environment variables can be added here
    ```
    **Important**: Never commit your `.env` file to version control. Add `.env` to your `.gitignore` file.

2.  **Ollama Setup (if using as LLM provider):**
    -   Ensure the Ollama application is running.
    -   Pull the desired model. The default configured in the app for Ollama is `gemma3:4b-it-q4_K_M`, but you can change this in `config/settings.py` (`LLM_PROVIDER_SETTINGS["ollama_default_model"]`).
        ```bash
        ollama pull gemma3:4b-it-q4_K_M
        ```
        Or list available models: `ollama list`

3.  **LLM Provider Selection:**
    You can choose your LLM provider when running the assistant. See "Running the Assistant" below. The default is set to Ollama.

4.  **Other Settings (`config/settings.py` and `config/settings.json`):**
    Advanced settings, such as agent enablement, voice preferences (TTS provider, voice model), and default LLM models, are managed in `config/settings.py`. These settings are saved to and loaded from `config/settings.json` at runtime. You can modify `config/settings.json` directly or edit the defaults in `config/settings.py` (which will regenerate the JSON if it's deleted or missing sections).

## Running the Assistant

Navigate to the project's root directory in your terminal (ensure your virtual environment is activated).

-   **To run with the default LLM provider (Ollama):**
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

## Basic Usage

-   Simply type your questions or commands and press Enter.
-   **Exit:** Type `exit` to close the assistant.
-   **Help:** Type `help` to see a list of available commands (if implemented in `main.py`'s `process_input`).
-   **Voice Output:**
    -   Voice output can be toggled using commands like `voice on`/`voice off` (if implemented).
    -   The default TTS provider (e.g., OpenAI) and voice preferences are set in `config/settings.py` under `VOICE_SETTINGS`.

## Development Notes

-   **Adding New Agents**:
    1.  Create your new agent class, typically inheriting from `BaseAgent`.
    2.  Implement the `process(self, query: str)` method.
    3.  Add initialization logic for your agent in `MasterAgent.__init__`.
    4.  Update `MasterAgent.agent_descriptions` and the routing prompt in `MasterAgent.process` to include your new agent and when it should be used.
    5.  Add default settings for your agent (e.g., enable/disable status) in `config/settings.py`.
-   **Debugging**: Set `debug_mode: True` in `SYSTEM_SETTINGS` in `config/settings.py` (or `config/settings.json`) to see detailed debug prints.

---

This README provides a comprehensive guide to getting your Personal AI Assistant up and running. Enjoy your new conversational friend!

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

## Future Roadmap

- [ ] Enhanced voice synthesis options
- [ ] Improved agent coordination
- [ ] Expanded local capabilities
- [ ] Advanced memory management
- [ ] Custom voice profile creation

## License

MIT License - See LICENSE file for details

---

*This project represents a step toward more personal, private, and powerful AI assistance. It's not just about what AI can do – it's about what AI can do for you, on your terms, with your privacy intact.*

## Features

### Personality Learning
The assistant includes a sophisticated personality learning system that:
- Adapts to your communication style (formal/informal, concise/detailed)
- Learns your interests and preferred topics
- Tracks interaction patterns and peak activity times
- Adjusts humor and emoji usage based on your preferences
- Stores personality insights in memory for more personal interactions

### Memory System

## Available Agents

### Personality Agent
The personality agent learns and adapts to your personality traits and preferences:
- Communication style analysis
- Interest and topic tracking
- Interaction pattern learning
- Dynamic response adaptation
- Personality insight generation

### Memory Agent
