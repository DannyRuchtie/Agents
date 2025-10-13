"""Shared help text for user-facing help commands."""

HELP_TEXT = """\

Available Commands:

Conversation:
- help - Show this help message.
- exit - Exit the assistant.
- reflect [n] - Analyze the last n conversation turns (default 6) and suggest improvements.

Voice Output (optional):
- voice status - Show voice output status.
- voice on / voice off - Enable or disable voice output.
- voice stop - Stop the current speech.
- voice voice <name> - Change the OpenAI voice model (e.g. alloy, echo, nova).
- voice speed <value> - Adjust the OpenAI TTS speed (0.25 - 4.0).
"""
