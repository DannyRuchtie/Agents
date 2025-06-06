# 🤖 Personal AI Assistant: Your Conversational Agent 🚀

## Project Overview

I am Danny's personal AI assistant and close friend. I act as the primary interface and intelligent router for various specialized AI agents.


## 🛠️ Meet the Agents: Your Specialist 

The heart of the assistant is its modular agent system, orchestrated by the Master Agent. Each agent has a specific role:

| Agent Name      | Description                                                                                                                                                       |
| :-------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🎩 **Master**      | Handles general conversation, chat, and direct questions. Also acts as the primary router.                                                                          |
| 💾 **Memory**      | Manages and recalls personal information, preferences, and past conversation details. (Always Active)                                                               |
| 😊 **Personality** | Analyzes interactions to understand and adapt to the user's personality and communication style.                                                                      |
| 🔍 **Search**      | Performs general web searches to find information, answer questions, or discover websites when a specific URL is not provided. Example: 'What is the capital of France?'.                                                                                                      |
| 🌐 **Browser**     | Interacts directly with specific websites. Navigates to URLs, takes screenshots, scrapes data from a given page, fills forms. Use if a URL is provided or a specific site action is requested (e.g., 'Go to example.com and take a screenshot', 'Scrape headlines from bbc.com/news'). Powered by `browser-use`. |
| ✍️ **Writer**      | Assists with writing tasks like composing emails, summaries, or creative text.                                                                                    |
| 📄 **Scanner**     | Scans and analyzes files and documents for information or insights.                                                                                                 |
| 🖼️ **Vision**      | Analyzes and understands EXPLICITLY PROVIDED image files or image paths. Use if query contains an image path or refers to an image just shown.                       |
| 📸 **Camera**      | Captures images using the webcam and describes them using VisionAgent. Use for queries like 'can you see me?', 'what do you see with the camera?', 'take a picture'. |
| 🧠 **Learning**    | Learns from interactions to improve responses and system performance over time.                                                                                     |
| ☀️ **Weather**     | Fetches current weather conditions and forecasts for specified locations.                                                                                           |
| ⏰ **Time**        | Provides the current date and time.                                                                                                                               |
| ➕ **Calculator**  | Handles mathematical calculations and evaluates expressions.                                                                                                      |
| 📧 **Email**       | Manages Gmail, checks for new emails, and can send emails.                                                                                                        |
| 🖥️ **Screen**      | Captures the user's CURRENT LIVE screen content and describes it. Use for queries like 'what am I looking at NOW?' or 'describe my CURRENT screen' when no image file is mentioned. |
| 🔗 **Limitless**   | Connects to Limitless API to retrieve and summarize your lifelogs, allowing you to ask about your past activities, meetings, and interactions.                     |
| 📚 *Get Last Sources* | (Internal Action) Retrieves and presents the sources for information recently provided by the search agent.                                                        |
| ⏰ **Reminders**   | Integrates with Apple Reminders to add, complete, delete, and search reminders using natural language queries. |


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
    
    **For Apple Reminders integration on macOS:**
    ```bash
    pip install pyobjc pyobjc-framework-EventKit
    ```
    *(These are included in requirements.txt, but you may need to grant permissions on first use.)*

    **For Browser Agent (Web Automation):**
    The `browser-use` library requires Playwright browsers. Install them by running:
    ```bash
    playwright install chromium --with-deps
    ```
    *(You can also install `firefox` or `webkit` if preferred, but `chromium` is commonly used. The `--with-deps` flag helps install necessary OS-level dependencies for Playwright browsers.)*

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

    #For getting yout Limitless AI lifelogs
    LIMITLESS_API_KEY="your_limmitless_ai_api_key_here"
    ```
    **Important**: The `BrowserAgent` uses `langchain_openai` by default (specifically `gpt-4o` as configured in `agents/browser_agent.py`). Ensure your `OPENAI_API_KEY` is set in the `.env` file for the BrowserAgent to function.

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


## 🤝 Contributing

Contributions are welcome! Whether it's adding new agents, improving existing functionality, enhancing documentation, or fixing bugs, please feel free to fork the repository, make your changes, and submit a pull request.

## 📜 License

This project is typically licensed under the MIT License (but please verify the `LICENSE` file in the repository).

---

*This README aims to be a comprehensive guide. If you find inaccuracies or areas for improvement, please contribute!*



## Security Notes

- API keys (OpenAI and Google) are stored locally in your .env file
- All document processing happens on your machine (when using ollama)
- Memory storage is local and under your control
- Web access is configurable and can be restricted
- Voice synthesis is performed by OpenAI TTS (optional)


## Contributing

This is an evolving project, and contributions are welcome! Whether it's adding new agents, improving existing functionality, or enhancing documentation, please feel free to submit pull requests.


## License

MIT License - See LICENSE file for details

---

