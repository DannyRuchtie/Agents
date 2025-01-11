# Multi-Agent Orchestrator Demo

This project demonstrates a master orchestrator agent coordinating multiple specialized sub-agents using LangChain v0.3.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```
Or create a `.env` file with:
```
OPENAI_API_KEY=your-api-key-here
```

## Usage

Run the demo:
```bash
python main.py
```

## Project Structure

- `main.py`: Contains the MasterAgent and orchestration logic
- `agents/`: Directory containing specialized agent implementations
  - `search_agent.py`: Simulated search functionality
  - `writer_agent.py`: Text composition and summarization
  - `code_agent.py`: Code generation capabilities
  - `memory_agent.py`: Memory retrieval functionality 