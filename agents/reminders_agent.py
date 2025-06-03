import objc
from Foundation import NSDate
from EventKit import EKEventStore, EKEntityTypeReminder
from agents.base_agent import BaseAgent
from config.settings import is_debug_mode, debug_print
import re
import datetime
import time
from Foundation import NSRunLoop, NSDefaultRunLoopMode

class RemindersAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_type="reminders")
        self.store = EKEventStore.alloc().init()
        self.access_granted = False
        self._request_access()
        if not self.access_granted:
            print("WARNING: RemindersAgent does not have access to Reminders. Functionality will be limited.")
            debug_print("RemindersAgent: Access to Reminders was not granted upon initialization.")

    def _request_access(self):
        access_event = {'granted': False, 'completed': False, 'error': None}

        def handler(_granted, _error):
            nonlocal access_event
            if _error:
                print(f"RemindersAgent: Error requesting access to Reminders: {_error.localizedDescription()}")
                debug_print(f"RemindersAgent: Access request error details: {_error}")
                access_event['error'] = _error
            access_event['granted'] = _granted
            access_event['completed'] = True

        self.store.requestAccessToEntityType_completion_(EKEntityTypeReminder, handler)

        timeout_seconds = 10
        start_time = time.time()
        while not access_event['completed'] and (time.time() - start_time) < timeout_seconds:
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )

        if not access_event['completed']:
            debug_print("RemindersAgent: Access request timed out.")
            print("RemindersAgent: Timed out waiting for Reminders access permission.")
            self.access_granted = False
        elif access_event['error']:
            self.access_granted = False
        elif not access_event['granted']:
            debug_print("RemindersAgent: Access to Reminders not granted by user.")
            print("RemindersAgent: Access to Reminders was not granted.")
            self.access_granted = False
        else:
            debug_print("RemindersAgent: Access to Reminders granted.")
            self.access_granted = True

    def _get_all_reminders(self):
        if not self.access_granted:
            debug_print("RemindersAgent: Cannot fetch reminders, access not granted or previously failed.")
            return []

        predicate = self.store.predicateForRemindersInCalendars_(None)
        fetched_data = {'reminders': [], 'completed': False, 'error': None}

        def completion_handler(result_or_error):
            nonlocal fetched_data
            ek_reminders = None
            error_obj = None

            NSError_class = objc.lookUpClass("NSError")
            if isinstance(result_or_error, NSError_class):
                error_obj = result_or_error
            else:
                ek_reminders = result_or_error

            if error_obj:
                print(f"RemindersAgent: Error fetching reminders: {error_obj.localizedDescription()}")
                debug_print(f"RemindersAgent: Fetch reminders error details: {error_obj}")
                fetched_data['error'] = error_obj
            else:
                if ek_reminders is not None:
                    for r in ek_reminders:
                        fetched_data['reminders'].append(r)
            fetched_data['completed'] = True

        self.store.fetchRemindersMatchingPredicate_completion_(predicate, completion_handler)

        timeout_seconds = 5
        start_time = time.time()
        while not fetched_data['completed'] and (time.time() - start_time) < timeout_seconds:
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )

        if not fetched_data['completed']:
            debug_print("RemindersAgent: Fetch reminders timed out.")
            print("RemindersAgent: Timed out while fetching reminders.")
            return []
        if fetched_data['error']:
            return []

        return fetched_data['reminders']

    def _find_reminders(self, keyword=None, date=None):
        reminders = self._get_all_reminders()
        results = []
        for reminder in reminders:
            if keyword and keyword.lower() not in reminder.title().lower():
                continue
            if date and reminder.dueDateComponents() and reminder.dueDateComponents().date() != date:
                continue
            results.append(reminder)
        return results

    def _add_reminder(self, title, due_date_input=None):
        reminder = objc.lookUpClass('EKReminder').reminderWithEventStore_(self.store)
        reminder.setTitle_(title)

        actual_due_date = None # This will be the final datetime.datetime object

        if due_date_input:
            if isinstance(due_date_input, datetime.datetime):
                if due_date_input.year == 1900 and due_date_input.month == 1 and due_date_input.day == 1:
                    actual_due_date = datetime.datetime.combine(datetime.date.today(), due_date_input.time())
                else:
                    actual_due_date = due_date_input
            elif isinstance(due_date_input, str) and due_date_input.strip():
                try:
                    parsed_time = datetime.datetime.strptime(due_date_input, "%H:%M").time()
                    actual_due_date = datetime.datetime.combine(datetime.date.today(), parsed_time)
                except ValueError:
                    debug_print(f"RemindersAgent: Could not parse due_date string '{due_date_input}' as HH:MM.")
                    actual_due_date = None

        if actual_due_date:
            comp = objc.lookUpClass('NSDateComponents').alloc().init()
            comp.setYear_(actual_due_date.year)
            comp.setMonth_(actual_due_date.month)
            comp.setDay_(actual_due_date.day)
            comp.setHour_(actual_due_date.hour)
            comp.setMinute_(actual_due_date.minute)
            reminder.setDueDateComponents_(comp)
        
        reminder.setCalendar_(self.store.defaultCalendarForNewReminders())
        success = self.store.saveReminder_commit_error_(reminder, True, None)
        if not success:
            return f"Error adding reminder: The operation failed."
        return f"Added reminder: {title}"

    def _complete_reminder(self, keyword):
        reminders = self._find_reminders(keyword=keyword)
        if not reminders:
            return f"No reminder found with keyword '{keyword}'."
        
        completed_count = 0
        errors = []
        for reminder in reminders:
            reminder.setCompleted_(True)
            success = self.store.saveReminder_commit_error_(reminder, True, None)
            if success:
                completed_count += 1
            else:
                errors.append(f"Failed to complete reminder: {reminder.title()}")

        if errors:
            return f"Completed {completed_count} reminder(s). Errors: {'; '.join(errors)}"
        return f"Marked {completed_count} reminder(s) as complete."

    def _delete_reminder(self, keyword):
        reminders = self._find_reminders(keyword=keyword)
        if not reminders:
            return f"No reminder found with keyword '{keyword}'."

        deleted_count = 0
        errors = []
        for reminder in reminders:
            success = self.store.removeReminder_commit_error_(reminder, True, None)
            if success:
                deleted_count += 1
            else:
                errors.append(f"Failed to delete reminder: {reminder.title()}")
        
        if errors:
            return f"Deleted {deleted_count} reminder(s). Errors: {'; '.join(errors)}"
        return f"Deleted {deleted_count} reminder(s)."

    def _parse_natural_language(self, query):
        # Expanded parsing for more flexible queries
        add_match = re.match(r"remind me to (.+) (at|on|by)? (.+)?", query, re.IGNORECASE)
        if add_match:
            title = add_match.group(1)
            time_str = add_match.group(3)
            due_date = None
            if time_str:
                try:
                    due_date = datetime.datetime.strptime(time_str, "%H:%M")
                except Exception:
                    due_date = None
            return ("add", title, due_date)
        complete_match = re.match(r"mark (.+) as complete", query, re.IGNORECASE)
        if complete_match:
            return ("complete", complete_match.group(1), None)
        delete_match = re.match(r"delete (.+) reminder", query, re.IGNORECASE)
        if delete_match:
            return ("delete", delete_match.group(1), None)
        search_match = re.match(r"find (.+) reminder", query, re.IGNORECASE)
        if search_match:
            return ("search", search_match.group(1), None)
        # New: list all reminders
        if re.match(r"(what are my reminders|list all reminders|show reminders|reminders list)", query, re.IGNORECASE):
            return ("list", None, None)
        return (None, None, None)

    async def process(self, query: str) -> str:
        action, arg, date = self._parse_natural_language(query)
        if action == "add":
            return self._add_reminder(arg, date)
        elif action == "complete":
            return self._complete_reminder(arg)
        elif action == "delete":
            return self._delete_reminder(arg)
        elif action == "search":
            reminders = self._find_reminders(keyword=arg)
            if not reminders:
                return f"No reminders found for '{arg}'."
            return "\n".join([reminder.title() for reminder in reminders])
        elif action == "list":
            reminders = self._get_all_reminders()
            if not reminders:
                return "You have no reminders."
            return "Here are your reminders:\n" + "\n".join([reminder.title() for reminder in reminders])
        # Fallback: try to use LLM to extract intent and arguments
        else:
            # Use the LLM to try to extract intent and arguments from the query
            prompt = (
                "You are an assistant that helps manage Apple Reminders. "
                "Given the following user query, extract the intended action (add, complete, delete, search, list) and the relevant arguments (title, time, etc). "
                "If the query is to list all reminders, return action 'list'. "
                "If you can't determine the intent, return action 'unknown'. "
                f"\nUser query: {query}\n"
                "Respond in the format: action|argument|date (date can be blank if not present)."
            )
            try:
                llm_response = await super().process(prompt)
                # Parse the LLM's response
                parts = llm_response.strip().split("|")
                action = None
                if len(parts) >= 1:
                    action = parts[0].strip().lower()
                if len(parts) >= 2:
                    arg = parts[1].strip()
                if len(parts) >= 3:
                    date = parts[2].strip()
                else:
                    if len(parts) <3 : date = None

                # Map to actions
                if action == "add":
                    return self._add_reminder(arg, date)
                elif action == "complete":
                    return self._complete_reminder(arg)
                elif action == "delete":
                    return self._delete_reminder(arg)
                elif action == "search":
                    reminders = self._find_reminders(keyword=arg)
                    if not reminders:
                        return f"No reminders found for '{arg}'."
                    return "\n".join([reminder.title() for reminder in reminders])
                elif action == "list":
                    reminders = self._get_all_reminders()
                    if not reminders:
                        return "You have no reminders."
                    return "Here are your reminders:\n" + "\n".join([reminder.title() for reminder in reminders])
                else:
                    return "Sorry, I couldn't understand your reminder request."
            except Exception as e:
                return f"Sorry, I couldn't process your reminder request due to an error: {e}" 