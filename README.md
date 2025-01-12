# Multi-Agent AI Assistant: Your Personal Digital Command Center

In the ever-evolving landscape of AI assistants, there's a persistent question that keeps surfacing: what if we could have the power of modern AI without compromising on privacy, while maintaining complete control over our digital workspace? That's exactly what this Multi-Agent AI Assistant sets out to solve, and it does so with a fascinating approach that feels both futuristic and surprisingly practical.

## What Makes This Different?

Unlike traditional cloud-based assistants, this system operates primarily on your local machine, creating a powerful bridge between advanced AI capabilities and your personal computing environment. It's not just another chat interface – it's a sophisticated multi-agent system that can:

- 🔍 **Access Your Local Environment**: Interact with your calendar, files, and applications while keeping your data under your control
- 🧠 **Build Persistent Memory**: Learn from interactions and maintain context across sessions
- 🌐 **Combine Local & Web Resources**: Seamlessly blend local knowledge with web-sourced information
- 🎯 **Provide Contextual Assistance**: Understand your location, schedule, and preferences to offer more relevant help
- 🔐 **Prioritize Privacy**: Keep sensitive information local and secure
- 🎤 **Natural Voice Interaction**: Wake word detection and continuous conversation support

## Core Features

### 🤖 Specialized Agents
- **Search Agent**: Intelligent web searching with context awareness
- **Writer Agent**: Advanced text composition and summarization
- **Code Agent**: Code generation and explanation
- **Memory Agent**: Long-term information storage and retrieval
- **Scanner Agent**: Document vectorization and semantic search
- **Vision Agent**: Image analysis and screen content understanding
- **Location Agent**: Location-aware services and recommendations
- **Speech Agent**: Natural voice interaction with customizable voices and speeds
- **Learning Agent**: System improvement through usage analysis

### 🎯 Key Capabilities
- Voice interaction with wake word detection
- Customizable voices and speech settings
- Calendar and reminder management
- Document analysis and semantic search
- Screen capture and image analysis
- Location-aware assistance
- Continuous learning and improvement
- Web search and information synthesis

## Getting Started

### Prerequisites
- Python 3.11 or higher
- OpenAI API key
- Picovoice API key (for wake word detection)
- macOS (for full feature compatibility)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/agents.git
   cd agents
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key and Picovoice key
   ```

### Running the Assistant
```bash
python main.py
```

## Voice Interaction Guide

### Wake Word Detection
The assistant listens for the wake word "computer" before accepting commands. You can:
1. Say "computer" to activate listening mode
2. Speak your command when you see "Listening..."
3. Wait for the response or continue with more commands

### Voice Settings
```bash
# List available voices
list voices

# Change voice
set voice [name]  # Available: nova, echo, onyx, alloy, fable, shimmer

# Adjust speech speed
set speed [0.5-2.0]  # 1.0 is normal, 2.0 is twice as fast

# Enable/disable continuous listening
continuous listening [on/off]

# Adjust listening timeouts
set wait timeout [seconds]    # Time to wait for speech to start
set phrase timeout [seconds]  # Maximum duration of a command
```

### Voice Commands
The assistant supports natural language commands. Examples:
```
"computer, what's the weather like?"
"computer, search for latest AI news"
"computer, summarize this document"
"computer, take a screenshot"
```

### Continuous Conversation Mode
Enable continuous listening to have natural back-and-forth conversations:
1. Say "continuous listening on"
2. Start with "computer" once
3. Continue speaking commands without the wake word
4. Say "stop listening" to exit continuous mode

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

- API keys are stored locally in your .env file
- All document processing happens on your machine
- Memory storage is local and under your control
- Web access is configurable and can be restricted
- Voice data is processed locally except for speech-to-text conversion

## Contributing

This is an evolving project, and contributions are welcome! Whether it's adding new agents, improving existing functionality, or enhancing documentation, please feel free to submit pull requests.

## Future Roadmap

- [ ] Additional wake word options
- [ ] Custom wake word training
- [ ] Offline speech-to-text support
- [ ] Multi-language support
- [ ] Enhanced voice activity detection
- [ ] Voice profile customization
- [ ] Improved continuous conversation handling

## License

MIT License - See LICENSE file for details

---

*This project represents a step toward more personal, private, and powerful AI assistance. It's not just about what AI can do – it's about what AI can do for you, on your terms, with your privacy intact.*
