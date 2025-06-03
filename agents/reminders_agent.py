import objc
from Foundation import NSDate
from EventKit import EKEventStore, EKEntityTypeReminder
from agents.base_agent import BaseAgent
from config.settings import is_debug_mode, debug_print
import re
import datetime

class RemindersAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_type="reminders")
        self.store = EKEventStore.alloc().init()
        self._request_access()

    def _request_access(self):
        granted = False
        def handler(_granted, _error):
            nonlocal granted
            granted = _granted
        self.store.requestAccessToEntityType_completion_(EKEntityTypeReminder, handler)
        if not granted:
            debug_print("RemindersAgent: Access to Reminders not granted.")

    def _get_all_reminders(self):
        predicate = self.store.predicateForRemindersInCalendars_(None)
        reminders = []
        def callback(reminders_list):
            for reminder in reminders_list or []:
                reminders.append(reminder)
        self.store.fetchRemindersMatchingPredicate_completion_(predicate, callback)
        return reminders

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

    def _add_reminder(self, title, due_date=None):
        reminder = objc.lookUpClass('EKReminder').reminderWithEventStore_(self.store)
        reminder.setTitle_(title)
        if due_date:
            comp = objc.lookUpClass('NSDateComponents').alloc().init()
            comp.setYear_(due_date.year)
            comp.setMonth_(due_date.month)
            comp.setDay_(due_date.day)
            comp.setHour_(due_date.hour)
            comp.setMinute_(due_date.minute)
            reminder.setDueDateComponents_(comp)
        reminder.setCalendar_(self.store.defaultCalendarForNewReminders())
        error = None
        self.store.saveReminder_commit_error_(reminder, True, error)
        return f"Added reminder: {title}" if not error else f"Error: {error}"

    def _complete_reminder(self, keyword):
        reminders = self._find_reminders(keyword=keyword)
        if not reminders:
            return f"No reminder found with keyword '{keyword}'."
        for reminder in reminders:
            reminder.setCompleted_(True)
            error = None
            self.store.saveReminder_commit_error_(reminder, True, error)
        return f"Marked {len(reminders)} reminder(s) as complete."

    def _delete_reminder(self, keyword):
        reminders = self._find_reminders(keyword=keyword)
        if not reminders:
            return f"No reminder found with keyword '{keyword}'."
        for reminder in reminders:
            error = None
            self.store.removeReminder_commit_error_(reminder, True, error)
        return f"Deleted {len(reminders)} reminder(s)."

    def _parse_natural_language(self, query):
        # Very basic parsing for demo purposes
        add_match = re.match(r"remind me to (.+) (at|on|by)? (.+)?", query, re.IGNORECASE)
        if add_match:
            title = add_match.group(1)
            time_str = add_match.group(3)
            due_date = None
            if time_str:
                try:
                    due_date = datetime.datetime.strptime(time_str, "%A at %I%p")
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
        else:
            return "Sorry, I couldn't understand your reminder request." 