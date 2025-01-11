# 🤖 Multi-Agent AI Assistant

A sophisticated multi-agent system that combines specialized AI agents to handle various tasks efficiently. The system uses LangChain v0.3 and OpenAI's latest models to provide a powerful, context-aware assistant experience.

```
┌──────────────────────────┐
│     Master Agent 🎮      │
│     (Orchestrator)       │
└─────┬────┬────┬────┬────┘
      │    │    │    │
┌─────▼──┐ │  ┌─▼──┐ ┌▼────┐
│ Memory │ │  │Code│ │Writer│
│  📚    │ │  │ 💻 │ │ ✍️   │
└────────┘ │  └────┘ └─────┘
           │
        ┌──▼──┐
        │Search│
        │ 🔍  │
        └─────┘
```

## ✨ Features

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
┌────────────────────────────────┐
│ 💬 Type your query naturally   │
│ 🚪 'exit' to end session       │
│ 💾 '@Desktop' to save files    │
└────────────────────────────────┘
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

## 📁 Project Structure
```
Project Root 📂
├── 🎮 main.py              # Main application
├── 🤖 agents/              # Agent modules
│   ├── 🔧 base_agent.py    # Base class
│   ├── 📚 memory_agent.py  # Memory management
│   ├── ✍️  writer_agent.py  # Text composition
│   ├── 🔍 search_agent.py  # Web searching
│   └── 💻 code_agent.py    # Code generation
├── 🧠 memory.json          # Memory storage
├── 📦 requirements.txt     # Dependencies
└── 🔑 .env                 # Environment vars
```

## ⚙️ Configuration

### 📚 Memory Storage
```
memory.json 📄
├── 📋 Structure: JSON
├── 🔄 Updates: Real-time
└── 💾 Backup: Manual
```

### 🔐 Environment Variables
- 🔑 `OPENAI_API_KEY`: Your OpenAI API key
- ⚙️ Additional variables in `.env`

## 💡 Best Practices

1. **🧠 Memory Management**
   ```
   ┌─────────────────────┐
   │ ✅ Use categories   │
   │ 📝 Add context      │
   │ 🔄 Verify often     │
   └─────────────────────┘
   ```

2. **📝 Document Creation**
   ```
   ┌─────────────────────┐
   │ 💾 Use @Desktop     │
   │ 🎨 Set style        │
   │ 📋 Clear titles     │
   └─────────────────────┘
   ```

3. **💻 Code Generation**
   ```
   ┌─────────────────────┐
   │ 📋 Clear specs      │
   │ 🔧 Set language     │
   │ 🛡️ Error handling   │
   └─────────────────────┘
   ```

## ⚠️ Error Handling
```
Error Types 🛡️
├── 🌐 API Failures
├── 📂 File Operations
├── 🧠 Memory Access
├── 🔍 Search Issues
└── ❌ Invalid Queries
```

## 🤝 Contributing

1. 🔀 Fork repository
2. 🌿 Create feature branch
3. ✍️ Make changes
4. 🔄 Push changes
5. 📬 Create Pull Request

## 📜 License

MIT License 📄 - feel free to use and modify as needed.

## 🆘 Support

For issues and feature requests, please create an issue in the repository.

## 🎯 Quick Reference

```
Commands Quick Look 👀
├── 💬 Chat Commands
│   ├── exit
│   └── help
├── 💾 File Commands
│   └── @Desktop
└── 🔍 Search Commands
    └── "search for..."
``` 