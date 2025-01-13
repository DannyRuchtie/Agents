# Personal AI Assistant

Your friendly AI assistant that acts like a close friend who knows you well and is always ready to help. It remembers your conversations, family details, and preferences, making every interaction personal and natural. Think of it as having a knowledgeable friend who's always there to chat, help with tasks, or find information - all while keeping the conversation casual and fun.

## What Makes This Special?

- **Acts Like a Real Friend**: Not just an AI - it's a friendly presence that knows you, your family, and your preferences
- **Natural Conversations**: Chats like a real person, with appropriate humor and personality
- **Remembers Everything**: Uses past conversations to make interactions more personal
- **Always Helpful**: Combines being friendly with being genuinely useful
- **Voice Enabled**: Can speak responses naturally, making it feel more like talking to a friend

## How It Behaves

The assistant is designed to be your friendly helper who:
- Greets you warmly and remembers previous conversations
- Uses casual, natural language instead of formal responses
- Brings up relevant details about you and your family when appropriate
- Keeps things light and fun while still being helpful
- Adapts its personality to match your preferences

### Personality Traits

The assistant's personality is customizable but always maintains a friendly, helpful demeanor:

- **Humor**: Can be witty and fun (adjustable from subtle to more playful)
- **Formality**: Keeps things casual like a friend (adjustable to your comfort level)
- **Empathy**: Shows understanding and support when needed
- **Engagement**: Shows genuine interest in your questions and concerns
- **Enthusiasm**: Maintains an upbeat, positive attitude

### Example Conversations

```
You: Hi there!
Assistant: Hey! Great to see you! How can I help you today? 😊

You: Can you remind me what my kids' names are?
Assistant: Of course! You have two wonderful children - Lena and Tobias! How are they doing?

You: I need help planning a trip
Assistant: I'd love to help you plan something! Given that you have two kids, Lena and Tobias, 
should we look for family-friendly destinations? I remember we talked about Bali before - 
is that still interesting, or would you like to explore other options? 😊

You: What's new in tech?
Assistant: Let me check that for you! I know you're interested in AI and development, 
so I'll focus on those areas while keeping it practical and relevant to your work.
```

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
