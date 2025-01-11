# 🤖 Multi-Agent AI Assistant

A sophisticated multi-agent system that combines specialized AI agents to handle various tasks efficiently. The system uses LangChain and OpenAI's latest models to provide a powerful, context-aware assistant experience.

```
┌───────────────────────────────────────────────────────────────┐
│                     Master Agent 🎮                           │
│                     (Orchestrator)                            │
└───────┬──────┬──────┬──────┬──────┬──────┬──────┬───────────┘
        │      │      │      │      │      │      │
    ┌───▼──┐ ┌─▼───┐ ┌▼───┐ ┌▼───┐ ┌▼────┐ ┌▼────┐ ┌▼────┐
    │Memory│ │Search│ │Code│ │Write│ │Scan │ │Vision│ │📍Loc│
    │ 📚   │ │ 🔍   │ │ 💻 │ │ ✍️  │ │ 📄  │ │ 🖼️   │ │🌤️   │
    └──────┘ └──────┘ └────┘ └────┘ └─────┘ └─────┘ └─────┘
```

## ✨ Features

- 🤖 **Specialized Agents**
  - 🔍 Search Agent: Web research and information gathering
  - ✍️ Writer Agent: Text composition and document creation
  - 💻 Code Agent: Code generation and technical solutions
  - 📚 Memory Agent: Context retention and information recall
  - 📄 Scanner Agent: Document vectorization and semantic search
  - 🖼️ Vision Agent: Image analysis and screen capture
  - 📍 Location Agent: Location and weather information

- 📊 **Document Management**
  - Automatic document processing and vectorization
  - Real-time monitoring of document changes
  - Semantic search across document contents
  - Intelligent document organization and retrieval
  - Automatic cleanup of deleted documents

- 🧠 **Memory Management**
  - Personal information storage
  - Conversation history tracking
  - Context-aware responses
  - Long-term information retention

- 📝 **File Management**
  - Markdown document creation
  - Desktop file saving
  - Automatic file organization
  - Document backup and tracking

### 1. 🤖 Specialized Agents
- **📚 Memory Agent**: Stores and retrieves information with categorized memory management
  - 👤 Personal information
  - 👥 Family contacts
  - 📋 Project details
  - ⚙️ User preferences
  - 📄 Document history
  
- **🔍 Search Agent**: Performs web searches to gather relevant information
  - 🌐 Real-time information retrieval
  - 🎯 Context-aware searching
  - 🛡️ Error handling and fallback mechanisms

- **✍️ Writer Agent**: Handles text composition and document creation
  - 📝 Blog post generation
  - 📋 Document summarization
  - 📘 Markdown file creation
  - 💾 Desktop file saving (@Desktop tag)
  - 🎨 Custom writing styles

- **💻 Code Agent**: Manages code-related tasks
  - ⌨️ Code generation
  - 📖 Code explanation
  - ✅ Best practices implementation

- **📄 Scanner Agent**: Manages document vectorization and storage
  - 📑 Document scanning and indexing
  - 🔍 Vector database management
  - 📂 Document backup and tracking
  - 🗑️ Automatic cleanup on deletion
  - 🔄 Real-time synchronization

- **🖼️ Vision Agent**: Analyzes images and screen content
  - 📸 Screen capture functionality
  - 🔍 OCR text extraction
  - 📊 Image content analysis
  - 🗂️ Image organization
  - 💾 Automatic saving and indexing

- **📍 Location Agent**: Provides location and weather information
  - 🌍 IP-based location detection
  - 🌤️ Real-time weather conditions
  - 🌡️ Temperature and humidity data
  - 💨 Wind speed and conditions
  - 🌧️ Precipitation forecasts

### 2. 🧠 Memory Management
The system maintains a structured memory system with categories:
```
Memory Structure
├── 👤 Personal
│   └── Names, preferences, dates
├── 👥 Contacts
│   ├── Family
│   ├── Friends
│   └── Colleagues
├── 📋 Projects
│   ├── Current
│   └── Past
├── 📚 Knowledge
│   ├── Technical
│   ├── Interests
│   └── Learning
└── ⚙️ System
    ├── Config
    └── History
```

### 3. 📂 File Management
- 💾 Automatic desktop file saving with @Desktop tag
- 📝 Markdown file formatting
- 🕒 Timestamp-based file naming
- 🛡️ Safe file handling

## 🚀 Setup

1. **🏗️ Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **📦 Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **🔑 Configure OpenAI API**

⚠️ **Security Note**: Never commit your API key to version control!

Create a `.env` file in the project root (this file is git-ignored):
```bash
# Create .env file
touch .env

# Add your API key (replace with your actual key)
echo "OPENAI_API_KEY=your-api-key-here" >> .env
```

Or set it as an environment variable:
```bash
# Linux/MacOS
export OPENAI_API_KEY=your-api-key-here

# Windows (Command Prompt)
set OPENAI_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:OPENAI_API_KEY="your-api-key-here"
```

## 📖 Usage

### 🏃‍♂️ Running the Application
```bash
python main.py
```

### 🎮 Basic Commands
```
┌────────────────────────────────────────┐
│ 💬 Type your query naturally           │
│ 🚪 'exit' to end session               │
│ 💾 '@Desktop' to save files            │
│ 📄 'scan' to process documents         │
│ 📸 'screenshot' to capture screen      │
│ 🖼️ 'analyze' to examine images         │
│ 📍 'weather' for local conditions      │
└────────────────────────────────────────┘
```

### 💡 Example Queries

1. **👥 Information Storage**
   ```
   "Remember that my name is [Name]"
   "My daughter's name is [Name]"
   ```

2. **📝 Document Creation**
   ```
   "Write a blog post about [topic] @Desktop"
   "Create a summary of [topic] and save it to my desktop"
   ```

3. **🔍 Information Retrieval**
   ```
   "What are the names of my children?"
   "Tell me about my family members"
   ```

4. **💻 Code Generation**
   ```
   "Write a Python function to [task]"
   "Create a JavaScript class for [purpose]"
   ```

5. **📄 Document Management**
   ```
   "Scan this document for later reference"
   "Find documents similar to [description]"
   ```

6. **🖼️ Image Analysis**
   ```
   "analyze 'path/to/image.jpg' what do you see"
   "screenshot and describe what's on my screen"
   ```

7. **📍 Location & Weather**
   ```
   "What's the weather like?"
   "Do I need an umbrella today?"
   "What's the temperature right now?"
   ```

## 📁 Project Structure
```
Project Root 📂
├── 🎮 main.py              # Main application
├── 🤖 agents/              # Agent modules
│   ├── 🔧 base_agent.py    # Base class
│   ├── 📚 memory_agent.py  # Memory management
│   ├── ✍️  writer_agent.py  # Text composition
│   ├── 🔍 search_agent.py  # Web searching
│   ├── 💻 code_agent.py    # Code generation
│   ├── 📄 scanner_agent.py # Document scanning
│   ├── 🖼️ vision_agent.py  # Image analysis
│   └── 📍 location_agent.py # Location & weather
├── 📂 documents/           # Managed documents
├── 📊 vectorstore/         # Vector database
├── 📸 screenshots/         # Captured screens
├── 🖼️ shared_images/       # Analyzed images
├── 🧠 memory.json          # Memory storage
├── 📦 requirements.txt     # Dependencies
└── 🔑 .env                 # Environment vars
```
