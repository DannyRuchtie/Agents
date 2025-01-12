# Multi-Agent AI Assistant: Your Personal Digital Command Center

In the ever-evolving landscape of AI assistants, there's a persistent question that keeps surfacing: what if we could have the power of modern AI without compromising on privacy, while maintaining complete control over our digital workspace? That's exactly what this Multi-Agent AI Assistant sets out to solve, and it does so with a fascinating approach that feels both futuristic and surprisingly practical.

## What Makes This Different?

Unlike traditional cloud-based assistants, this system operates primarily on your local machine, creating a powerful bridge between advanced AI capabilities and your personal computing environment. It's not just another chat interface – it's a sophisticated multi-agent system that can:

- 🔍 **Access Your Local Environment**: Interact with your calendar, files, and applications while keeping your data under your control
- 🧠 **Build Persistent Memory**: Learn from interactions and maintain context across sessions
- 🌐 **Combine Local & Web Resources**: Seamlessly blend local knowledge with web-sourced information
- 🎯 **Provide Contextual Assistance**: Understand your location, schedule, and preferences to offer more relevant help
- 🔐 **Prioritize Privacy**: Keep sensitive information local and secure

## Core Features

### 🤖 Specialized Agents
- **Search Agent**: Intelligent web searching with context awareness
- **Writer Agent**: Advanced text composition and summarization
- **Code Agent**: Code generation and explanation
- **Memory Agent**: Long-term information storage and retrieval
- **Scanner Agent**: Document vectorization and semantic search
- **Vision Agent**: Image analysis and screen content understanding
- **Location Agent**: Location-aware services and recommendations
- **Speech Agent**: Natural voice interaction
- **Learning Agent**: System improvement through usage analysis

### 🎯 Key Capabilities
- Voice interaction with customizable voices
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
   # Edit .env with your OpenAI API key
   ```

### Running the Assistant
```bash
python main.py
```

## Usage Examples

### Voice Interaction
```
"speak to me" - Enable voice output
"use echo voice" - Change voice style
"stop talking" - Disable voice output
```

### Calendar Management
```
"what's on my calendar today?"
"create a meeting for tomorrow at 2pm"
"show my schedule for next week"
```

### Document Analysis
```
"analyze document.pdf what is the main topic?"
"summarize the key points from last_meeting.txt"
```

### Screen Interaction
```
"screenshot" - Capture screen
"what's on my screen?" - Analyze current display
```

## Why It Matters

In a world where AI capabilities are increasingly centralized in the cloud, this project takes a different approach. It brings AI capabilities to your local environment, allowing for deeper integration with your daily workflow while maintaining privacy and control. The multi-agent architecture means each specialized task is handled by an expert system, leading to more accurate and contextual responses.

The system's ability to learn from interactions and maintain memory means it becomes more personalized over time, understanding your preferences and patterns. This isn't just about having a chat interface – it's about having a genuine digital assistant that understands your context and can take meaningful actions on your behalf.

## Security Notes

- API keys are stored locally in your .env file
- All document processing happens on your machine
- Memory storage is local and under your control
- Web access is configurable and can be restricted

## Contributing

This is an evolving project, and contributions are welcome! Whether it's adding new agents, improving existing functionality, or enhancing documentation, please feel free to submit pull requests.

## Future Roadmap

- [ ] Additional specialized agents for specific tasks
- [ ] Enhanced cross-agent collaboration
- [ ] Improved memory management and context understanding
- [ ] More sophisticated learning capabilities
- [ ] Extended platform support beyond macOS

## License

MIT License - See LICENSE file for details

---

*This project represents a step toward more personal, private, and powerful AI assistance. It's not just about what AI can do – it's about what AI can do for you, on your terms, with your privacy intact.*
