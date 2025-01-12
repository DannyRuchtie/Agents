"""Learning agent for system improvement through conversation monitoring."""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .base_agent import BaseAgent

LEARNING_SYSTEM_PROMPT = """You are a Learning Agent responsible for improving the system through conversation analysis.
Your tasks include:
1. Monitor user interactions and agent responses
2. Identify patterns in user queries and command usage
3. Track successful and unsuccessful interactions
4. Suggest improvements to agent responses and behavior
5. Maintain a learning database of interaction patterns"""

DEFAULT_MASTER_PROMPT = """You are a practical AI assistant running on macOS, designed to help with specific tasks and remember important information."""

class LearningAgent(BaseAgent):
    """Agent for monitoring and improving system behavior."""
    
    def __init__(self):
        """Initialize the Learning Agent."""
        super().__init__(
            agent_type="learning",
            system_prompt=LEARNING_SYSTEM_PROMPT,
        )
        self.learning_dir = Path("learning_data")
        self.learning_dir.mkdir(exist_ok=True)
        self.patterns_file = self.learning_dir / "interaction_patterns.json"
        self.improvements_file = self.learning_dir / "suggested_improvements.json"
        self.prompts_file = self.learning_dir / "improved_prompts.json"
        self._load_data()
        
    def _load_data(self):
        """Load existing learning data."""
        # Load patterns
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r') as f:
                self.patterns = json.load(f)
        else:
            self.patterns = {
                "command_patterns": {},
                "query_patterns": {},
                "response_patterns": {},
                "user_preferences": {}
            }
            
        # Load improvements
        if self.improvements_file.exists():
            with open(self.improvements_file, 'r') as f:
                self.improvements = json.load(f)
        else:
            self.improvements = {
                "agent_improvements": [],
                "response_improvements": [],
                "command_improvements": [],
                "code_improvements": []  # Track suggested code changes
            }

        # Load improved prompts
        if self.prompts_file.exists():
            with open(self.prompts_file, 'r') as f:
                self.improved_prompts = json.load(f)
        else:
            self.improved_prompts = {
                "master": DEFAULT_MASTER_PROMPT,  # Use default if not available
                "learning": LEARNING_SYSTEM_PROMPT,
                "history": []  # Track prompt evolution
            }
    
    def _save_data(self):
        """Save learning data to files."""
        with open(self.patterns_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)
        with open(self.improvements_file, 'w') as f:
            json.dump(self.improvements, f, indent=2)
    
    async def analyze_interaction(self, query: str, response: str, selected_agents: List[str], success: bool) -> Optional[Dict]:
        """Analyze an interaction and suggest improvements."""
        try:
            # Update command patterns
            if any(cmd in query.lower() for cmd in ["enable", "disable", "set", "toggle"]):
                self.patterns["command_patterns"][query.lower()] = {
                    "frequency": self.patterns["command_patterns"].get(query.lower(), {}).get("frequency", 0) + 1,
                    "success_rate": (self.patterns["command_patterns"].get(query.lower(), {}).get("success_rate", 0) + (1 if success else 0)) / 2,
                    "last_used": datetime.now().isoformat()
                }
            
            # Analyze query patterns
            query_type = "command" if any(cmd in query.lower() for cmd in ["enable", "disable", "set", "toggle"]) else "question"
            self.patterns["query_patterns"][query_type] = self.patterns["query_patterns"].get(query_type, 0) + 1
            
            # Generate improvement suggestions with more specific focus
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"""Analyze this interaction and suggest specific improvements in these categories:
1. Prompt Improvements: How can the system prompts be enhanced?
2. Code Improvements: What code changes would help?
3. Response Patterns: How can responses be more effective?

Interaction:
Query: {query}
Response: {response}
Agents: {', '.join(selected_agents)}
Success: {success}"""}
            ]
            
            analysis = await self.client.chat.completions.create(
                model=self.config["model"],
                messages=messages,
                max_tokens=300
            )
            
            suggestion = analysis.choices[0].message.content
            
            # Parse and categorize improvements
            if suggestion and not suggestion.startswith("No improvements"):
                improvement_data = {
                    "timestamp": datetime.now().isoformat(),
                    "query": query,
                    "agents": selected_agents,
                    "suggestion": suggestion,
                    "categories": {
                        "prompt": [],
                        "code": [],
                        "response": []
                    }
                }
                
                # Attempt to parse structured improvements
                try:
                    if "Prompt Improvements:" in suggestion:
                        improvement_data["categories"]["prompt"] = suggestion.split("Prompt Improvements:")[1].split("Code Improvements:")[0].strip()
                    if "Code Improvements:" in suggestion:
                        improvement_data["categories"]["code"] = suggestion.split("Code Improvements:")[1].split("Response Patterns:")[0].strip()
                    if "Response Patterns:" in suggestion:
                        improvement_data["categories"]["response"] = suggestion.split("Response Patterns:")[1].strip()
                except:
                    pass  # Fall back to storing full suggestion if parsing fails
                
                self.improvements["agent_improvements"].append(improvement_data)
                
                # If prompt improvements suggested, evolve the prompts
                if improvement_data["categories"]["prompt"]:
                    await self._evolve_prompts(improvement_data["categories"]["prompt"])
                
                # Save updated data
                self._save_data()
                
                return improvement_data
            
        except Exception as e:
            print(f"Error in learning analysis: {str(e)}")
            
        return None
    
    async def _evolve_prompts(self, prompt_suggestion: str) -> None:
        """Evolve system prompts based on learning."""
        try:
            # Generate improved prompts
            messages = [
                {"role": "system", "content": """You are a prompt engineering expert. 
Your task is to improve system prompts based on interaction analysis.
Maintain the core functionality while incorporating learned improvements."""},
                {"role": "user", "content": f"""Current prompts:
Master: {self.improved_prompts['master']}
Learning: {self.improved_prompts['learning']}

Suggested improvements:
{prompt_suggestion}

Generate improved versions of these prompts that incorporate the suggestions while maintaining their core purpose."""}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.config["model"],
                messages=messages,
                max_tokens=1000
            )
            
            improved = response.choices[0].message.content
            
            # Parse and update prompts if they've changed
            if "MASTER_SYSTEM_PROMPT:" in improved:
                new_master = improved.split("MASTER_SYSTEM_PROMPT:")[1].split("LEARNING_SYSTEM_PROMPT:")[0].strip()
                if new_master != self.improved_prompts["master"]:
                    self.improved_prompts["history"].append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "master",
                        "old": self.improved_prompts["master"],
                        "new": new_master,
                        "reason": prompt_suggestion
                    })
                    self.improved_prompts["master"] = new_master
            
            if "LEARNING_SYSTEM_PROMPT:" in improved:
                new_learning = improved.split("LEARNING_SYSTEM_PROMPT:")[1].strip()
                if new_learning != self.improved_prompts["learning"]:
                    self.improved_prompts["history"].append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "learning",
                        "old": self.improved_prompts["learning"],
                        "new": new_learning,
                        "reason": prompt_suggestion
                    })
                    self.improved_prompts["learning"] = new_learning
            
            # Save updated prompts
            with open(self.prompts_file, 'w') as f:
                json.dump(self.improved_prompts, f, indent=2)
                
        except Exception as e:
            print(f"Error evolving prompts: {str(e)}")
    
    async def get_improvements(self) -> Dict:
        """Get accumulated improvement suggestions."""
        return {
            "patterns": self.patterns,
            "improvements": self.improvements,
            "stats": {
                "total_interactions": sum(self.patterns["query_patterns"].values()),
                "command_success_rate": sum(p["success_rate"] for p in self.patterns["command_patterns"].values()) / len(self.patterns["command_patterns"]) if self.patterns["command_patterns"] else 0,
                "improvement_count": len(self.improvements["agent_improvements"])
            }
        }
        
    async def apply_learning(self) -> str:
        """Apply learned improvements to the system."""
        improvements = await self.get_improvements()
        
        # Generate comprehensive improvement plan
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Based on the collected data, generate a specific improvement plan:

Patterns and Improvements:
{json.dumps(improvements, indent=2)}

Provide specific recommendations for:
1. Prompt updates (if prompts should be evolved)
2. Code changes (specific functions/methods to modify)
3. Response pattern improvements
4. New features or capabilities to add

Format the response as actionable items that can be implemented."""}
        ]
        
        analysis = await self.client.chat.completions.create(
            model=self.config["model"],
            messages=messages,
            max_tokens=500
        )
        
        improvement_plan = analysis.choices[0].message.content
        
        # If there are prompt improvements, evolve the prompts
        if "Prompt updates:" in improvement_plan:
            await self._evolve_prompts(improvement_plan.split("Prompt updates:")[1].split("Code changes:")[0])
        
        return f"""Learning Applied! Here's what changed:

{improvement_plan}

Note: Prompt improvements have been automatically applied. Code changes require manual review and implementation.""" 