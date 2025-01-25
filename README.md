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
- Google Custom Search API key (for web search)
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
   ```
   
   Configure the following in your `.env` file:
   ```bash
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key
   
   # Google Custom Search Configuration
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
   
   # Voice Settings (optional)
   DEFAULT_VOICE=af_sarah
   DEFAULT_VOICE_SPEED=1.0
   
   # API Configuration
   API_HOST=localhost
   API_PORT=8000
   RATE_LIMIT=60  # requests per minute
   ```

### Running the Assistant
Start the API server:
```bash
python -m api.run
```

For the macOS app:
1. Open the Xcode project in the `AgentAssistant` directory
2. Build and run the project
3. The app will appear as a floating window with a black circle

### Available Endpoints
All API endpoints are available at `http://localhost:8000` by default. See the API Documentation section for details.

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

## API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### Status Check
```bash
GET /

Response:
{
    "status": "ok",
    "message": "Agents API is running",
    "version": "1.0.0"
}
```

#### Send Query
```bash
POST /query
Content-Type: application/json

Request Body:
{
    "query": "your question here"
}

Response:
{
    "status": "success",
    "response": "assistant's response"
}
```

#### List Agents
```bash
GET /agents

Response:
{
    "agents": [
        {
            "type": "memory",
            "enabled": true
        },
        {
            "type": "search",
            "enabled": true
        },
        // ... other agents
    ],
    "total": 8
}
```

#### Voice Control
```bash
# Get voice status
GET /voice/status

Response:
{
    "status": "success",
    "voice_enabled": true,
    "current_voice": "af_sarah",
    "speed": 1.0,
    "available_voices": ["am_michael", "af_bella", "bf_emma", "bm_george", "af_sarah", "af_sky"]
}

# Enable voice
POST /voice/enable

# Disable voice
POST /voice/disable
```

### Error Responses
All endpoints may return the following error structure:
```json
{
    "status": "error",
    "message": "Error description"
}
```

### Rate Limiting
- Default rate limit: 60 requests per minute
- Endpoints return 429 Too Many Requests if rate limit is exceeded

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
