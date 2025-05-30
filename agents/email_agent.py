"""Agent for interacting with Gmail API."""
import os
import base64
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
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"] # Start with read-only
# For sending: "https://www.googleapis.com/auth/gmail.send"
# For full access: "https://mail.google.com/"

TOKEN_PATH = Path(__file__).resolve().parent.parent / "token.json" # Store in project root
CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "credentials.json" # Expecting downloaded OAuth credentials JSON

# --- Note on credentials.json vs .env --- 
# The Google library examples often use a credentials.json file downloaded from Google Cloud.
# We are using GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from .env for more flexibility.
# The _get_credentials method will be adapted to use these .env variables instead of a static credentials.json file if it's not found.

EMAIL_SYSTEM_PROMPT = """You are an AI assistant that helps manage Gmail. You can check for new emails, summarize them, send emails, and search for specific emails in the user's inbox.
When asked to check emails, provide a concise summary of new unread messages.
When asked to send an email, confirm the recipient, subject, and body before proceeding. If the subject is missing, try to generate one from the body.
When asked to search for emails, use the provided keywords to search the user's entire mailbox and summarize the findings.
Be clear and helpful.
"""

class EmailAgent(BaseAgent):
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
                    raise Exception("EmailAgent: Failed to obtain credentials.")
                self.service = build('gmail', 'v1', credentials=creds)
                debug_print("EmailAgent: Gmail API service initialized successfully.")
            except Exception as e:
                debug_print(f"EmailAgent: Failed to initialize Gmail service: {str(e)}")
                self.service = None # Ensure service is None if init fails
                # Re-raise or handle as appropriate for the calling method
                raise

    async def check_new_emails(self, max_results=5) -> str:
        await self._ensure_service()
        if not self.service:
            return "EmailAgent: Gmail service is not available. Cannot check emails."
        try:
            # List unread messages
            results = self.service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return "You have no new unread emails."

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
                return "You have no new unread emails, or I couldn't retrieve their details."

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
            return f"I encountered an API error while trying to check your emails: {error}"
        except Exception as e:
            debug_print(f'EmailAgent: An unexpected error occurred while checking emails: {e}')
            return f"Sorry, an unexpected error occurred while I was checking your emails: {e}"

    async def search_specific_emails(self, search_query_string: str, max_results=3) -> str:
        await self._ensure_service()
        if not self.service:
            return "EmailAgent: Gmail service is not available. Cannot search emails."
        try:
            debug_print(f"EmailAgent: Searching for emails matching: '{search_query_string}', max_results={max_results}")
            results = self.service.users().messages().list(userId='me', q=search_query_string, maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return f"I couldn't find any emails matching your search for '{search_query_string}'."

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
                return f"I found some references but couldn't retrieve details for emails matching '{search_query_string}'."

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
            return f"I encountered an API error while trying to search your emails for '{search_query_string}': {error}"
        except Exception as e:
            debug_print(f'EmailAgent: An unexpected error occurred while searching emails: {e}')
            return f"Sorry, an unexpected error occurred while I was searching your emails for '{search_query_string}': {e}"

    async def send_email(self, to: str, subject: str, body_text: str) -> str:
        # Before calling this, ensure SCOPES include gmail.send or similar
        # For now, this will likely fail if only gmail.readonly is used.
        if ("https://www.googleapis.com/auth/gmail.send" not in SCOPES and 
            "https://mail.google.com/" not in SCOPES):
            return "EmailAgent: Cannot send email. Missing required 'send' permissions in SCOPES. Please update SCOPES and re-authenticate (delete token.json)."

        await self._ensure_service()
        if not self.service:
            return "EmailAgent: Gmail service is not available. Cannot send email."
        try:
            message = MIMEText(body_text)
            message['to'] = to
            message['subject'] = subject
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {
                'raw': encoded_message
            }
            send_message = self.service.users().messages().send(userId="me", body=create_message).execute()
            debug_print(f'EmailAgent: Message Id: {send_message["id"]}')
            return f"Email sent successfully to {to} with subject: {subject}. Message ID: {send_message["id"]}"
        except HttpError as error:
            debug_print(f'EmailAgent: An API error occurred while sending email: {error}')
            return f"Failed to send email. API error: {error}"
        except Exception as e:
            debug_print(f'EmailAgent: An unexpected error occurred while sending email: {e}')
            return f"An unexpected error occurred: {e}"

    async def process(self, query: str) -> str:
        await self._ensure_service() # Ensure authenticated and service is ready
        if not self.service:
            return "EmailAgent: Gmail service is not available due to authentication or setup issues."

        debug_print(f"EmailAgent attempting to understand user query: {query}")

        # LLM call to determine intent and extract parameters
        intent_prompt = f"""You are an email processing AI. Given the user's query, determine the action they want to perform and extract any relevant parameters.
Possible actions are: 'check_new_emails', 'send_email', 'search_specific_emails', 'answer_query_about_emails_generally'.

If 'check_new_emails':
- Parameters: 'max_results' (integer, default to 5 if not specified or if a general request like 'check emails' is made. Look for numbers in phrases like 'last 3 emails', 'top 10 emails').

If 'send_email':
- Parameters: 'to' (string, recipient email), 'subject' (string), 'body' (string).

If 'search_specific_emails':
- Parameters: 'search_terms' (string, the keywords or phrases the user wants to search for in their emails. Extract this from queries like 'find emails about X', 'what was that email about Y', 'search for messages from Z concerning A').

If the query is a general question about email functionality, how to use the email agent, or something that doesn't fit other actions, choose 'answer_query_about_emails_generally' and the original query will be used for a general LLM response.

User Query: "{query}"

Respond ONLY with a JSON object containing 'action' (string) and 'parameters' (an object). Include all extracted parameters. If a parameter for an action is not found in the query, do not include it in the parameters object unless a default is specified (like max_results).
Example for 'check my 3 new emails': {{"action": "check_new_emails", "parameters": {{"max_results": 3}}}}
Example for 'search for emails about project phoenix': {{"action": "search_specific_emails", "parameters": {{"search_terms": "project phoenix"}}}}
Example for 'what was that email from jane about the budget?': {{"action": "search_specific_emails", "parameters": {{"search_terms": "from:jane budget"}}}}
Example for 'send an email to foo@bar.com subject hello body hi there': {{"action": "send_email", "parameters": {{"to": "foo@bar.com", "subject": "hello", "body": "hi there"}}}}
Example for 'how do I use you for email?': {{"action": "answer_query_about_emails_generally", "parameters": {{}}}}
"""
        
        try:
            # Use a different system prompt for this specific intent parsing call, or temporarily override.
            # For now, we assume super().process() uses the agent's default system_prompt, 
            # so the intent_prompt needs to be very explicit.
            # A better way would be for BaseAgent to allow passing a temporary system_prompt.
            # However, the detailed instructions in intent_prompt should guide the current BaseAgent.process well.
            parsed_intent_str = await super().process(intent_prompt) # BaseAgent handles LLM call
            debug_print(f"EmailAgent: LLM intent parsing response: {parsed_intent_str}")
            
            import json
            intent_data = json.loads(parsed_intent_str)
            action = intent_data.get("action")
            parameters = intent_data.get("parameters", {})

            if action == "check_new_emails":
                max_results = parameters.get("max_results", 5) # Default to 5 if not specified
                try: # Ensure max_results is an int
                    max_results = int(max_results)
                except ValueError:
                    max_results = 5 
                    debug_print(f"EmailAgent: Invalid max_results from LLM, defaulting to 5.")
                return await self.check_new_emails(max_results=max_results)
            
            elif action == "search_specific_emails":
                search_terms = parameters.get("search_terms")
                if search_terms:
                    return await self.search_specific_emails(search_query_string=search_terms)
                else:
                    return "You asked me to search for emails, but didn't provide any search terms. What would you like me to look for?"
            
            elif action == "send_email":
                recipient = parameters.get("to")
                subject = parameters.get("subject")
                body = parameters.get("body")

                # Attempt to generate subject from body if not provided
                if not subject and body:
                    debug_print(f"EmailAgent: Subject missing, attempting to generate from body: '{body[:100]}...'")
                    subject_generation_prompt = (
                        f"Given the following email body, please generate a concise and relevant subject line (max 10 words).\n"
                        f"Email Body:\n"
                        f"---\n"
                        f"{body}\n"
                        f"---\n"
                        f"Generated Subject:"
                    )
                    # Temporarily adjust system prompt for this specific task
                    original_system_prompt = self.system_prompt
                    self.system_prompt = "You are an AI assistant helping to compose emails by generating subject lines."
                    generated_subject_str = await super().process(subject_generation_prompt)
                    self.system_prompt = original_system_prompt # Reset it
                    
                    # Clean up the generated subject (LLMs can sometimes add quotes or prefixes)
                    generated_subject_str = generated_subject_str.strip().removeprefix("Subject:").removeprefix('"').removesuffix('"').strip()
                    
                    if generated_subject_str:
                        subject = generated_subject_str
                        debug_print(f"EmailAgent: LLM generated subject: '{subject}'")
                    else:
                        debug_print("EmailAgent: LLM failed to generate a subject or returned empty.")
                        # Subject remains None or empty, will be caught by missing_parts check

                # Check for missing parts after potential subject generation
                missing_parts = []
                if not recipient: 
                    missing_parts.append("recipient (to)")
                elif "@" not in recipient: # Basic check for a valid email format
                     missing_parts.append("a valid recipient email address (e.g., name@example.com)")
                if not subject: # Check subject again, in case generation failed or body was also missing
                    missing_parts.append("subject")
                if not body: 
                    missing_parts.append("body")

                if not missing_parts:
                    return await self.send_email(to=recipient, subject=subject, body_text=body)
                else:
                    return f"To send an email, I'm missing the following: {', '.join(missing_parts)}. Please provide all details."
            
            elif action == "answer_query_about_emails_generally":
                # Use the agent's default system prompt for a general answer to the original query
                # This requires BaseAgent to use its self.system_prompt when super().process is called.
                # We need to call super().process with the *original query* here.
                debug_print(f"EmailAgent: Handling '{query}' with general email system prompt.")
                # Re-setting system prompt for this call if BaseAgent doesn't allow temporary override.
                # This is a bit of a workaround. Ideally BaseAgent().process takes an optional system_prompt.
                original_system_prompt = self.system_prompt
                self.system_prompt = EMAIL_SYSTEM_PROMPT # Ensure it's using the email specific one
                response = await super().process(query) # Pass original query
                self.system_prompt = original_system_prompt # Reset it
                return response
            else:
                debug_print(f"EmailAgent: Unknown action parsed: {action}. Falling back to general response.")
                # Fallback for unknown action, use original query and email system prompt
                original_system_prompt = self.system_prompt
                self.system_prompt = EMAIL_SYSTEM_PROMPT
                response = await super().process(query) # Pass original query
                self.system_prompt = original_system_prompt # Reset it
                return response

        except json.JSONDecodeError:
            debug_print(f"EmailAgent: Failed to parse JSON from LLM for intent: {parsed_intent_str}. Query: {query}")
            # Fallback to general response using the original query
            original_system_prompt = self.system_prompt
            self.system_prompt = EMAIL_SYSTEM_PROMPT
            response = await super().process(query)
            self.system_prompt = original_system_prompt # Reset it
            return response
        except Exception as e:
            debug_print(f"EmailAgent: Error in process method: {str(e)}. Query: {query}")
            # Fallback to general response using the original query
            original_system_prompt = self.system_prompt
            self.system_prompt = EMAIL_SYSTEM_PROMPT
            response = await super().process(query) # Attempt to give a helpful general answer
            self.system_prompt = original_system_prompt # Reset it
            return f"I encountered an issue trying to process your email request for '{query}'. Detail: {str(e)}" 