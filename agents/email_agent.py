"""Agent for interacting with Gmail API."""
import os
import base64
import json # For parsing LLM response in process method
from pathlib import Path
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base_agent import BaseAgent
from config.settings import debug_print

# If modifying these SCOPES, delete the token.json file.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]

TOKEN_PATH = Path(__file__).resolve().parent.parent / "token.json"
CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "credentials.json"

EMAIL_SYSTEM_PROMPT = """You are an AI assistant that helps manage Gmail. Your primary task is to understand user requests related to email and translate them into actionable commands for the Gmail API.

When a user asks you to do something with their email, your first step is to determine the specific action: 'check_new', 'search_emails', or 'send_email'.

1.  **Check New Emails ('check_new')**: 
    *   If the user wants to check for new or unread emails (e.g., "any new emails?", "check my inbox").
    *   No specific parameters needed beyond the intent itself.

2.  **Search Emails ('search_emails')**:
    *   If the user wants to find specific emails (e.g., "find emails from John about the project", "search for attachments from last week").
    *   Extract a 'search_query_string' that can be passed to Gmail's search.

3.  **Send Email ('send_email')**:
    *   If the user wants to send an email (e.g., "send an email to jane@example.com", "draft a message to support").
    *   Extract 'to' (recipient's email address), 'subject', and 'body' of the email.
    *   If the subject is missing, try to infer a suitable one from the body. If the body is very short and the subject unclear, you can ask for clarification on the subject.
    *   If critical information like the recipient is missing, you must ask for it.

Your response for this initial classification step MUST be a JSON object containing:
{ "action": "<action_name>", "parameters": { <extracted_parameters_as_key_value_pairs> } }

Example for checking mail: {"action": "check_new", "parameters": {}}
Example for searching: {"action": "search_emails", "parameters": {"search_query_string": "from:boss subject:urgent"}}
Example for sending: {"action": "send_email", "parameters": {"to": "friend@example.com", "subject": "Catching up", "body": "Hey, how are you? Let's connect soon."}}

If the request is ambiguous or lacks essential information for an action (e.g., missing recipient for 'send_email'), use {"action": "clarify", "parameters": {"missing_info": "recipient_email", "original_query": "..."}}.

After this classification, the system will then call the appropriate function to interact with Gmail. For 'send_email', the system will separately ask the user for final confirmation before actually sending.
"""

class EmailAgent(BaseAgent):
    """
    Agent for managing Gmail interactions, including checking, searching, and sending emails.

    Core Functionality:
    This agent uses the Gmail API to perform email operations. It requires OAuth2
    authentication, storing credentials in `token.json` and using client secrets
    from environment variables (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).

    The `process(query: str)` method is the main entry point. It uses an LLM to:
    1. Classify the user's query into an action: 'check_new', 'search_emails', or 'send_email'.
    2. Extract necessary parameters for that action (e.g., search terms, recipient/subject/body).
    3. Calls the corresponding internal method to interact with the Gmail API.

    Internal Tools/Methods:
        - _get_credentials(): Handles Google OAuth2 authentication flow.
        - _ensure_service(): Initializes the Gmail API service.
        - check_new_emails(max_results=5): Fetches and summarizes new unread emails using an LLM.
        - search_specific_emails(search_query_string: str, max_results=3): Searches emails and summarizes results using an LLM.
        - send_email(to: str, subject: str, body_text: str): Sends an email.

    Setup:
    - Requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
    - User will be prompted for Google account authorization via a web browser on first use
      or when `token.json` is invalid/expired.
    - `SCOPES` define API permissions (currently read and send).
    """
    def __init__(self):
        super().__init__(
            agent_type="email",
            system_prompt=EMAIL_SYSTEM_PROMPT
        )
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.service = None # Gmail service, initialized after auth

        if not self.google_client_id or not self.google_client_secret:
            debug_print("EmailAgent: WARNING - GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found in .env. Gmail functionality will fail.")
        else:
            debug_print("EmailAgent: Google Client ID and Secret loaded.")

    def _get_credentials(self):
        creds = None
        if TOKEN_PATH.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
                debug_print("EmailAgent: Loaded credentials from token.json")
            except Exception as e:
                debug_print(f"EmailAgent: Error loading token.json: {e}. Will attempt re-authentication.")
                creds = None # Ensure creds is None if loading fails
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    debug_print("EmailAgent: Refreshed expired credentials.")
                except Exception as e:
                    debug_print(f"EmailAgent: Failed to refresh credentials: {e}. Need to re-authenticate.")
                    creds = None # Force re-authentication
            else:
                debug_print("EmailAgent: No valid credentials found or refresh failed. Starting OAuth flow.")
                if not self.google_client_id or not self.google_client_secret:
                    msg = "EmailAgent: Cannot authenticate. Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in environment variables."
                    debug_print(msg)
                    raise Exception(msg)

                # Construct the client_config dictionary needed by InstalledAppFlow
                # This mimics the structure of a client_secret.json file.
                client_config = {
                    "installed": {
                        "client_id": self.google_client_id,
                        "client_secret": self.google_client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        # project_id, auth_provider_x509_cert_url, redirect_uris are often in client_secret.json
                        # but for "Desktop app" type, InstalledAppFlow primarily needs client_id, client_secret, auth_uri, token_uri.
                        # If InstalledAppFlow complains about missing project_id, it might need to be added here if available from your setup.
                    }
                }
                try:
                    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                    # The `run_local_server` method opens a browser tab and waits for user authorization.
                    # It handles the code exchange and token retrieval.
                    # port=0 means it will pick an available port.
                    creds = flow.run_local_server(port=0)
                    debug_print("EmailAgent: OAuth flow completed. Credentials obtained.")
                except Exception as e:
                    debug_print(f"EmailAgent: OAuth flow failed: {e}")
                    raise Exception(f"EmailAgent: OAuth flow failed: {e}")

            # Save the credentials for the next run
            try:
                with open(TOKEN_PATH, 'w') as token_file:
                    token_file.write(creds.to_json())
                debug_print(f"EmailAgent: Saved credentials to {TOKEN_PATH}")
            except Exception as e:
                debug_print(f"EmailAgent: Error saving token.json: {e}")
        return creds

    async def _ensure_service(self):
        """Ensures the Gmail API service is initialized."""
        if not self.service:
            try:
                creds = self._get_credentials()
                if not creds:
                    raise Exception("EmailAgent: Failed to obtain credentials. Service not initialized.")
                self.service = build('gmail', 'v1', credentials=creds)
                debug_print("EmailAgent: Gmail API service initialized successfully.")
            except Exception as e:
                debug_print(f"EmailAgent: Failed to initialize Gmail service: {str(e)}")
                self.service = None
                raise # Re-raise the exception to be handled by the caller

    async def check_new_emails(self, max_results=5) -> str:
        await self._ensure_service()
        if not self.service:
            return "EmailAgent: Gmail service is not available. Cannot check emails."
        try:
            # List unread messages
            results = self.service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return "Looks like your inbox is all clear! No new unread emails right now."

            email_details_for_summary = []
            for msg_ref in messages:
                msg = self.service.users().messages().get(userId='me', id=msg_ref['id'], format='metadata', metadataHeaders=['subject', 'from']).execute()
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])
                subject = "[No Subject]"
                sender = "[Unknown Sender]"
                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                    if header['name'].lower() == 'from':
                        sender = header['value']
                snippet = msg.get('snippet', '[No snippet]')
                email_details_for_summary.append(f"Email from: {sender}\nSubject: {subject}\nSnippet: {snippet}\n---")
            
            if not email_details_for_summary:
                return "You have no new unread emails, or I couldn't retrieve their details at the moment."

            # Prepare a prompt for the LLM to summarize these emails conversationally
            emails_text = "\n\n".join(email_details_for_summary)
            summary_prompt = f"""You are an assistant who has just checked the user's email inbox. 
Based on the following email information, provide a concise and conversational summary of the new messages. 
Do not just list them. Synthesize the information and tell the user what's new in their inbox in a friendly, helpful tone. 
For example, 'You've got a couple of new messages. One is from LinkedIn about a job, and another is a security alert from Google.' 
If there's only one, adjust accordingly. If there are several, you can group them if it makes sense (e.g., 'You have a few updates from LinkedIn and a newsletter.').

Here are the email details:
{emails_text}

Your conversational summary:"""

            # Use the base agent's LLM call to generate the summary
            # We need to temporarily change the system prompt for this specific task
            original_system_prompt = self.system_prompt
            self.system_prompt = "You are a helpful assistant summarizing emails." # More direct for this task
            conversational_summary = await super().process(summary_prompt)
            self.system_prompt = original_system_prompt # Reset it
            
            return conversational_summary

        except HttpError as error:
            debug_print(f'EmailAgent: An API error occurred while checking emails: {error}')
            return f"I hit a snag trying to check your emails with Google: {error}"
        except Exception as e:
            debug_print(f'EmailAgent: An unexpected error occurred while checking emails: {e}')
            return f"Sorry, something unexpected went wrong while I was trying to check your emails: {e}"

    async def search_specific_emails(self, search_query_string: str, max_results=3) -> str:
        await self._ensure_service()
        if not self.service:
            return "EmailAgent: Gmail service is not available. Cannot search emails."
        try:
            debug_print(f"EmailAgent: Searching for emails matching: '{search_query_string}', max_results={max_results}")
            results = self.service.users().messages().list(userId='me', q=search_query_string, maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return f"I searched your emails for '{search_query_string}' but couldn't find anything matching that."

            email_details_for_summary = []
            for msg_ref in messages:
                # Fetch full message to get snippet and headers correctly for general search
                msg = self.service.users().messages().get(userId='me', id=msg_ref['id']).execute()
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])
                subject = "[No Subject]"
                sender = "[Unknown Sender]"
                date = "[Unknown Date]"
                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                    if header['name'].lower() == 'from':
                        sender = header['value']
                    if header['name'].lower() == 'date':
                        date = header['value']
                
                snippet = msg.get('snippet', '[No snippet available]')
                email_details_for_summary.append(f"Email from: {sender}\nDate: {date}\nSubject: {subject}\nSnippet: {snippet}\n---")
            
            if not email_details_for_summary:
                return f"I found some email references for '{search_query_string}', but I couldn't quite fetch their details."

            emails_text = "\n\n".join(email_details_for_summary)
            summary_prompt = f"""You are an assistant who has just searched the user's email inbox based on their query. 
Based on the following email information, provide a concise and conversational summary of the messages found. 
Do not just list them. Synthesize the information and tell the user what you found in a friendly, helpful tone. 

Search query was: '{search_query_string}'
Here are the email details found:
{emails_text}

Your conversational summary of the search results:"""

            original_system_prompt = self.system_prompt
            self.system_prompt = "You are a helpful assistant summarizing email search results."
            conversational_summary = await super().process(summary_prompt)
            self.system_prompt = original_system_prompt
            
            return conversational_summary

        except HttpError as error:
            debug_print(f'EmailAgent: An API error occurred while searching emails: {error}')
            return f"I ran into a Google API issue while searching your emails for '{search_query_string}': {error}"
        except Exception as e:
            debug_print(f'EmailAgent: An unexpected error occurred while searching emails: {e}')
            return f"Oops, something unexpected happened while I was searching your emails for '{search_query_string}': {e}"

    async def send_email(self, to: str, subject: str, body_text: str) -> str:
        # Before calling this, ensure SCOPES include gmail.send or similar
        if ("https://www.googleapis.com/auth/gmail.send" not in SCOPES and 
            "https://mail.google.com/" not in SCOPES):
            return "EmailAgent: Cannot send email. Missing required 'send' permissions. Please update SCOPES and re-authenticate (delete token.json)."

        await self._ensure_service()
        if not self.service:
            return "EmailAgent: Gmail service is not available. Cannot send email."

        try:
            message = MIMEText(body_text)
            message['to'] = to
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message_request = {'raw': raw_message}

            sent_message = self.service.users().messages().send(userId='me', body=send_message_request).execute()
            debug_print(f"EmailAgent: Message sent. Message ID: {sent_message['id']}")
            return f"Alright, your email to {to} with the subject '{subject}' has been sent!"
        except HttpError as error:
            debug_print(f'EmailAgent: An API error occurred while sending email: {error}')
            return f"I hit a Google API snag while trying to send your email: {error}"
        except Exception as e:
            debug_print(f'EmailAgent: An unexpected error occurred while sending email: {e}')
            return f"Yikes, something unexpected went wrong when I tried to send your email: {e}"

    async def process(self, query: str) -> str:
        debug_print(f"EmailAgent received query: {query}")
        
        try:
            # First, ensure service can be initialized. This might trigger OAuth.
            # Wrapped in try-except in case _get_credentials itself raises an issue that needs user feedback.
            try:
                await self._ensure_service() 
            except Exception as e:
                debug_print(f"EmailAgent: Initial service check failed: {e}")
                # Provide a more user-friendly message if auth fails here
                if "OAuth flow failed" in str(e) or "Failed to obtain credentials" in str(e):
                    return f"I need to connect to your Google account to manage emails, but something went wrong with the authorization. Please ensure you have enabled the Gmail API in your Google Cloud project and that your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correctly set up. Details: {str(e)}"
                return f"EmailAgent: Could not connect to Gmail service: {str(e)}"
            
            if not self.service:
                 return "EmailAgent: Gmail service could not be initialized. Please check your setup and authentication."

            # Use the LLM to classify the query and extract parameters
            # The system_prompt (EMAIL_SYSTEM_PROMPT) is designed for this classification task
            raw_classification = await super().process(query) # LLM call for classification
            debug_print(f"EmailAgent classification response: {raw_classification}")

            classification = json.loads(raw_classification)
            action = classification.get("action")
            params = classification.get("parameters", {})

            if action == "check_new":
                return await self.check_new_emails()
            elif action == "search_emails":
                search_query = params.get("search_query_string")
                if not search_query:
                    return "Sure, I can search your emails! What exactly are you looking for?"
                return await self.search_specific_emails(search_query)
            elif action == "send_email":
                to = params.get("to")
                subject = params.get("subject")
                body = params.get("body")

                if not to:
                    return "I can help send that email, but who should I address it to? Please let me know the recipient's email."
                if not subject and not body: # Or if body is too short to infer subject
                    return "Okay, I'm ready to send an email. What would you like the subject and body to be?"
                if not subject: # Try to infer subject if body exists
                    subject_inference_prompt = f"Given the email body: \n\n'{body}'\n\nSuggest a concise and appropriate subject line for this email. Respond with ONLY the subject line."
                    original_sys_prompt = self.system_prompt
                    self.system_prompt = "You are an assistant helping to create email subject lines."
                    inferred_subject = await super().process(subject_inference_prompt)
                    self.system_prompt = original_sys_prompt
                    subject = inferred_subject.strip()
                    debug_print(f"EmailAgent: Inferred subject: '{subject}'")
                    if not subject: # If LLM failed to provide a subject
                         return "I couldn't quite make out a subject for your email. Could you tell me what it should be?"

                # CONFIRMATION STEP BEFORE SENDING
                # More conversational lead-in to the confirmation managed by MasterAgent if needed
                # EmailAgent now focuses on stating what it WILL DO, MasterAgent confirms
                return await self.send_email(to, subject, body) # Direct send for now

            elif action == "clarify":
                missing_info = params.get("missing_info", "some details")
                original_query = params.get("original_query", query)
                return f"To help with your email request about '{original_query}', I just need a little more info on the following: {missing_info}. Could you fill me in?"
            else:
                debug_print(f"EmailAgent: Unknown action from classification: {action}. Query: {query}")
                # Fallback to a more general response or re-prompting
                return "I'm not quite sure how to handle that email request. I can check for new emails, search your inbox, or help you send a message. What would you like to do?"

        except json.JSONDecodeError as e:
            debug_print(f"EmailAgent: Failed to parse JSON from LLM: {raw_classification}. Error: {e}")
            return "I had a little trouble understanding the specifics of your email task. Could you try rephrasing?"
        except HttpError as e:
            debug_print(f"EmailAgent: Google API HTTP Error in process(): {e}")
            error_content = e.content.decode() if e.content else "No details"
            if e.resp.status == 401:
                # Specific handling for auth errors like invalid_grant (token expired/revoked)
                if "invalid_grant" in error_content.lower():
                    # Attempt to clear the token and ask the user to retry, which should trigger re-auth
                    if TOKEN_PATH.exists():
                        try:
                            TOKEN_PATH.unlink()
                            debug_print("EmailAgent: Deleted token.json due to invalid_grant error.")
                        except OSError as ose:
                            debug_print(f"EmailAgent: Error deleting token.json: {ose}")
                    return "It seems my authorization with Google needs a refresh. I've cleared the old one. If you try again, I'll guide you through reconnecting!"
                return f"Hmm, there's an authentication hiccup with Google: {error_content}. Let's make sure I'm properly authorized and your credentials are set."
            elif e.resp.status == 403:
                 if "access_denied" in error_content.lower() or "insufficient permissions" in error_content.lower() or "forbidden" in error_content.lower() or "scope" in error_content.lower():
                    return f"It looks like I don't have the right permissions for that action with your Gmail (Error 403: Forbidden). My current permissions are for: {SCOPES}. If you were trying to send an email or do something similar, I might need broader access. Details: {error_content}"
                 return f"Google says I'm not allowed to do that with your Gmail account (Error 403: Forbidden). Best to check my permissions. Details: {error_content}"
            return f"A Google API error popped up: {e.resp.status} - {error_content}. Might be worth checking your Gmail API setup and quotas."
        except Exception as e:
            debug_print(f"EmailAgent: Error in process method: {type(e).__name__} - {e}")
            import traceback
            debug_print(traceback.format_exc())
            return f"I encountered an unexpected issue while trying to process your email request: {str(e)}"

# Example Usage (for testing locally, not part of the agent file)
# async def main():
#     # Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are in your .env or environment
#     agent = EmailAgent()
    
#     # --- Test Authentication and Service Initialization (Implicitly in process) ---
#     # First call might trigger OAuth flow in browser
#     print("--- Testing initial connection (may trigger OAuth) ---")
#     # A simple query to test if service can be established.
#     # If .env vars are missing, this will print the warning from __init__ and then fail here.
#     try:
#        print(await agent.process("Can you check my email?")) # This will try to classify and then call check_new_emails
#     except Exception as e:
#         print(f"Test Error: {e}")
#         if "OAuth flow failed" in str(e) or "Missing GOOGLE_CLIENT_ID" in str(e):
#             print("Please ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in .env and credentials.json is not needed/handled, or that you complete the OAuth flow.")
#         return

#     # --- Test Checking Emails (after successful auth) ---
#     print("\n--- Testing Check New Emails ---")
#     print(await agent.process("any new mail?"))
#     print(await agent.process("What's new in my inbox?"))

#     # --- Test Searching Emails ---
#     print("\n--- Testing Search Emails ---")
#     print(await agent.process("find emails from myself about testing"))
#     print(await agent.process("search for messages with attachment sent last month"))

#     # --- Test Sending Emails (will require 'send' scope and confirmation logic) ---
#     print("\n--- Testing Send Email ---")
#     # The current process() sends directly after LLM classification. 
#     # True confirmation would need user interaction handled by MasterAgent.
#     print(await agent.process("Send an email to test@example.com with subject 'Hello from Agent' and body 'This is a test message.'"))
#     print(await agent.process("Draft an email to my_friend@example.com. The subject is Dinner Plans. The body is Let's grab dinner next week!"))
#     print(await agent.process("email john.doe@work.com about the report. it's ready")) # Test subject inference

#     # --- Test Clarification ---
#     print("\n--- Testing Clarification ---")
#     print(await agent.process("send an email")) # Missing recipient
#     print(await agent.process("search my emails")) # Missing search query

# if __name__ == "__main__":
#    import asyncio
#    # Load .env variables if you're using python-dotenv
#    # from dotenv import load_dotenv
#    # load_dotenv()
#    asyncio.run(main()) 