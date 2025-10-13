# 🤖 Personal AI Assistant: Your Conversational Agent 🚀

## Project Overview

I am Danny's personal AI assistant and close friend. I act as the primary interface and intelligent router for various specialized AI agents. Built with modern AI capabilities including:

- 🧠 **Auto Model Selection** - Automatically selects the best AI model for your task
- 💾 **Mem0 Integration** - Intelligent semantic memory that truly understands you
- 🎙️ **Real-time Voice** - Natural voice conversations with GPT-4o Mini Realtime
- 🔄 **Hybrid Memory** - JSON + Mem0 for reliable and intelligent memory
- 🎯 **Streamlined Architecture** - Focused on core, high-quality agents


## 🛠️ Meet the Agents: Your Specialists

The heart of the assistant is its modular agent system, orchestrated by the Master Agent. Each agent has a specific role:

| Agent Name | Description                                                                                               |
| :--------- | :-------------------------------------------------------------------------------------------------------- |
| 🎩 **Master** | Handles conversation, keeps the personality prompt fresh, and routes queries to specialist agents.        |
| 💾 **Memory** | JSON-backed long-term memory system for personal facts, preferences, and lightweight personality notes. |
| 🔍 **Search** | Web search agent (Google Custom Search when keys are available, DuckDuckGo fallback otherwise).         |

**Note:** Personality Agent has been **consolidated into Memory Agent**. All personality analysis and insights are now handled by the unified memory system.

### 🎯 Auto Model Selection

The system intelligently selects the best model for each task:

- **Simple tasks** (definitions, basic queries): `gpt-4o-mini` - Fast and cost-effective
- **Moderate tasks** (summaries, search synthesis): `gpt-5-mini` - Balanced performance
- **Complex tasks** (deep analysis, multi-step): `gpt-5` - Maximum capability  
- **Reasoning tasks** (logic problems, proofs): `o1` - Advanced reasoning
- **Vision tasks** (image analysis, screenshots): `gpt-5` - Vision-enabled
- **Real-time audio**: `gpt-realtime-mini-2025-10-06` - Low-latency voice ([GPT-4o Mini Realtime](https://platform.openai.com/docs/models/gpt-realtime-mini))

Configuration is in `config/settings.py` under `MODEL_SELECTOR_SETTINGS`.


## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher.
- `pip` for installing Python packages.
- **Environment variables (in `.env`):**
  - `OPENAI_API_KEY` (required).
  - `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` (optional—without them the assistant uses DuckDuckGo).

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
    
    **Key dependencies include:**
    - `mem0ai` - Enhanced semantic memory system
    - `pyaudio` - Real-time audio support
    - `pyobjc` - Apple Reminders integration (macOS)
    - `browser-use` - Web automation
    - `ollama` (optional) - Local LLM support
    
    **For Browser Agent (Web Automation):**
    Install Playwright browsers:
    ```bash
    playwright install chromium --with-deps
    ```
    
    **For Apple Reminders (macOS):**
    Grant permissions in `System Settings > Privacy & Security > Reminders` on first use.

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

    # For Gmail Integration (Email Agent)
    GOOGLE_CLIENT_ID="your_google_client_id_here"
    GOOGLE_CLIENT_SECRET="your_google_client_secret_here"
    
    # Optional: For Real-time Voice (if using custom endpoint)
    # OPENAI_REALTIME_API_URL="wss://api.openai.com/v1/audio/speech/realtime"
    ```
    
    **Important Notes:**
    - The system uses OpenAI by default for LLM operations
    - BrowserAgent uses `gpt-4o` by default
    - All vision tasks use API-based models (no local vision models needed)
    - Mem0 uses OpenAI embeddings for semantic search

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
    
    **Key Settings Sections:**
    - `AGENT_SETTINGS` - Enable/disable individual agents
    - `MODEL_SELECTOR_SETTINGS` - Configure auto model selection
    - `MEM0_SETTINGS` - Configure semantic memory (user_id, embedding model, vector store)
    - `VOICE_SETTINGS` - TTS and real-time audio configuration
    - `PERSONALITY_TRAITS` - Customize communication style
    
    Settings are saved to `config/settings.json` at runtime. You can edit either file for persistent changes.

## 🚀 Running the Assistant

Navigate to the project's root directory in your terminal (ensure your virtual environment is activated).

-   **To run with the default LLM provider (OpenAI recommended for latest models):**
    ```bash
    python main.py
    ```

-   **To run with OpenAI (with auto model selection):**
    ```bash
    python main.py --llm openai
    ```

-   **To run with Ollama (for local/offline use):**
    ```bash
    python main.py --llm ollama
    ```

You'll see a welcome message and a `You:` prompt. The assistant will automatically select the best model for each request.

## 🗣️ Basic Usage

-   Simply type your questions or commands and press Enter.
-   **Exit:** Type `exit` to close the assistant.
-   **Help:** Type `help` to see a list of available commands (note: command parsing is handled in `main.py`'s `process_input` function; enhance this to add more commands).
-   **Voice Output:**
    -   Voice output is **disabled by default**.
    -   You can toggle it using commands like `voice on` / `voice off` (if implemented and recognized in `main.py`).
    -   The default TTS provider is OpenAI. Voice preferences (e.g., OpenAI voice model like "alloy", "nova") are set in `config/settings.py` under `VOICE_SETTINGS`.

## 🧪 Evaluations

Quickly validate the core agent flows (memory recall, search routing, and help command) with the bundled evaluation harness:

```bash
python3 -m evals.run_evals
```

Each scenario spins up a fresh `MasterAgent`, runs the prompt, and verifies the response for expected behavior. Extend `evals/run_evals.py` with additional cases to cover new agents or workflows.


## 🤝 Contributing

Contributions are welcome! Whether it's adding new agents, improving existing functionality, enhancing documentation, or fixing bugs, please feel free to fork the repository, make your changes, and submit a pull request.

## 📜 License

This project is typically licensed under the MIT License (but please verify the `LICENSE` file in the repository).

---

*This README aims to be a comprehensive guide. If you find inaccuracies or areas for improvement, please contribute!*



## 🔐 Security & Privacy

- **API Keys**: Stored locally in `.env` file (never committed)
- **Memory**: Hybrid system - JSON files + Mem0 vector database, both local
- **LLM Processing**: Choose between cloud (OpenAI) or local (Ollama)
- **Web Access**: Configurable, only when explicitly requested
- **Voice**: Optional TTS and real-time audio through OpenAI
- **Permissions**: System-level permissions required for Reminders, Screen capture

## 🆕 What's New in Version 2.0

### Major Changes:
- ✅ **Removed 9 deprecated agents** for cleaner architecture
- ✅ **Auto Model Selector** - Intelligent model selection based on task complexity
- ✅ **Mem0 Integration** - Semantic memory that truly understands context
- ✅ **GPT-4o Mini Realtime** - Natural voice conversations with low latency
- ✅ **API-Based Vision** - Screen and Browser agents now use direct API calls
- ✅ **Enhanced Reminders** - Better NLP with LLM-powered intent extraction
- ✅ **Latest Models** - Support for GPT-5, GPT-5-mini, O1, and Realtime Mini

### Removed/Consolidated Agents:
The following agents were removed or consolidated to streamline the system:
- **Removed:** Calculator, Camera, Learning, Limitless, Scanner, Time, Vision, Weather, Writer (9 agents)
- **Consolidated:** Personality Agent merged into Memory Agent (now handles both memories and personality)

These capabilities are now handled by the Master Agent or integrated into remaining agents.

**Total reduction:** From 17 agents to 7 core agents (-59% complexity)


## Contributing

This is an evolving project, and contributions are welcome! Whether it's adding new agents, improving existing functionality, or enhancing documentation, please feel free to submit pull requests.


## License

MIT License - See LICENSE file for details

---
