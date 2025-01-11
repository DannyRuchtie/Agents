# 🤖 Multi-Agent AI Assistant

An advanced AI assistant that combines multiple specialized agents to enhance your daily workflow. Built with OpenAI's latest models and running natively on macOS, this assistant can help you with everything from writing and research to code generation and local system interactions.

## ✨ Key Features

### 🎙️ Voice Interaction
- Natural text-to-speech using OpenAI's voices (alloy, echo, fable, onyx, nova, shimmer)
- Smart voice mode detection - automatically recognizes when you want spoken responses
- Easy voice commands like "speak to me" or "read this aloud"

### 📍 Location & Environment
- Real-time weather updates and location-aware responses
- Local system integration with macOS features
- Screen capture and image analysis capabilities

### 💡 Intelligent Assistance
- Web search and information retrieval
- Code generation and technical assistance
- Document scanning and analysis
- Memory storage for personal and contextual information

### 🔄 Natural Interaction
- Context-aware responses that remember previous conversations
- Seamless switching between text and voice modes
- Proactive suggestions based on context

## 🚀 Getting Started

### 1. **Prerequisites**
- Python 3.11 or higher
- macOS system
- OpenAI API key

### 2. **Installation**
```bash
# Clone the repository
git clone [repository-url]
cd [repository-name]

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. **Configuration**
Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your-api-key-here
```

## 💫 Usage Examples

### Voice Interaction
```bash
# Turn voice mode on (any of these patterns work)
> start speaking
> start voice
> enable speech
> enable voice
> turn on speech
> turn on voice
> voice on
> speech on

# Change voice
> set voice alloy    # Choose from: alloy, echo, fable, onyx, nova, shimmer
> change to echo
> use nova voice
> switch to shimmer

# Turn voice mode off
> stop speaking
> stop voice
> disable speech
> disable voice
> turn off speech
> turn off voice
> voice off
> speech off

# Toggle auto-play
> toggle autoplay
> toggle auto-play
> toggle voice

# Direct speech
> say [your text]
> speak [your text]
> tell me [your text]

Note: The system is designed to be flexible and understand variations of these commands,
including common typos (e.g., "stat speaking" will be recognized as "start speaking").
```

### Information & Search
```bash
# Get weather information
> what's the weather like?
> do I need an umbrella today?

# Web search
> search for recent AI developments
> find information about [topic]
```

### Memory & Personal Info
```bash
# Store information
> remember that my name is [Name]
> my daughter's name is [Name]

# Retrieve information
> what do you remember about my family?
> recall our previous conversation about [topic]
```

### Document & Image Analysis
```bash
# Process documents
> scan this document
> analyze this image
> take a screenshot and describe what you see
```

### Code Assistance
```bash
# Generate or explain code
> write a Python function to [task]
> explain how this code works
> help me debug this error
```

## 🎯 Use Cases

1. **Personal Assistant**
   - Schedule management and reminders
   - Weather updates and local information
   - Personal and family information management

2. **Development Helper**
   - Code generation and debugging
   - Technical documentation
   - Development workflow automation

3. **Research Assistant**
   - Web search and information gathering
   - Document analysis and summarization
   - Content creation and writing assistance

4. **System Interface**
   - Voice-controlled system interactions
   - Screen capture and analysis
   - Document management and processing

## 🔒 Security Note

- Never share your API keys
- Be cautious with personal information
- Review generated code before execution
- Keep your dependencies updated

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests, report bugs, or suggest new features.

## 📝 License

[Your chosen license]
