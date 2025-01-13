# Multi-Agent AI Assistant: Your Personal Digital Command Center

In the ever-evolving landscape of AI assistants, there's a persistent question that keeps surfacing: what if we could have the power of modern AI without compromising on privacy, while maintaining complete control over our digital workspace? That's exactly what this Multi-Agent AI Assistant sets out to solve, and it does so with a fascinating approach that feels both futuristic and surprisingly practical.

## What Makes This Different?

Unlike traditional cloud-based assistants, this system operates primarily on your local machine, creating a powerful bridge between advanced AI capabilities and your personal computing environment. It's not just another chat interface – it's a sophisticated multi-agent system that can:

- 🔍 **Access Your Local Environment**: Interact with your files and applications while keeping your data under your control
- 🧠 **Build Persistent Memory**: Learn from interactions and maintain context across sessions
- 🌐 **Combine Local & Web Resources**: Seamlessly blend local knowledge with web-sourced information
- 🎯 **Provide Contextual Assistance**: Understand your location and preferences to offer more relevant help
- 🔐 **Prioritize Privacy**: Keep sensitive information local and secure
- 🎤 **Natural Voice Output**: Local text-to-speech using kokoro-onnx voices

## Core Features

### 🤖 Specialized Agents
- **Search Agent**: Intelligent web searching with context awareness
- **Writer Agent**: Advanced text composition and summarization
- **Code Agent**: Code generation and explanation
- **Memory Agent**: Long-term information storage and retrieval
- **Scanner Agent**: Document vectorization and semantic search
- **Vision Agent**: Image analysis and screen content understanding
- **Location Agent**: Location-aware services and recommendations
- **Learning Agent**: System improvement through usage analysis

### 🎯 Key Capabilities
- Local text-to-speech with customizable voices
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

## Voice Output Guide

### Voice Settings
```bash
# Check voice status
voice status

# Enable/disable voice
enable voice
disable voice

# Change voice
set voice [name]  # Available: am_michael, af_bella, bf_emma, bm_george, af_sarah, af_sky

# Adjust speech speed
set voice speed [0.5-2.0]  # 1.0 is normal, 2.0 is twice as fast
```

### Available Voices
- `am_michael`: Adult male voice
- `af_bella`: Adult female voice
- `bf_emma`: British female voice
- `bm_george`: British male voice
- `af_sarah`: Adult female voice (default)
- `af_sky`: Adult female voice (alternative)

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
- Voice synthesis is performed locally using kokoro-onnx

## Contributing

This is an evolving project, and contributions are welcome! Whether it's adding new agents, improving existing functionality, or enhancing documentation, please feel free to submit pull requests.

## Future Roadmap

- [ ] Multi-language support
- [ ] Enhanced voice synthesis options
- [ ] Improved agent coordination
- [ ] Expanded local capabilities
- [ ] Advanced memory management
- [ ] Custom voice profile creation

## License

MIT License - See LICENSE file for details

---

*This project represents a step toward more personal, private, and powerful AI assistance. It's not just about what AI can do – it's about what AI can do for you, on your terms, with your privacy intact.*
