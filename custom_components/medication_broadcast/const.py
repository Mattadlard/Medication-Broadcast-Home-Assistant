"""Constants for Medication Broadcast Assistant.

Icon attribution (required by Flaticon licence):

Tablet icon:
    "Tablet icons created by Freepik - Flaticon"
    https://www.flaticon.com/free-icons/tablet

Refill icon:
    "Refill icons created by Freepik - Flaticon"
    https://www.flaticon.com/free-icons/refill
"""

DOMAIN = "medication_broadcast"

CONF_TTS_SERVICE = "tts_service"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_DEFAULT_MEDIA_PLAYERS = "default_media_players"
CONF_MEDS = "meds"

# Per-med configuration
CONF_ID = "id"
CONF_NAME = "name"
CONF_ENABLED = "enabled"
CONF_INSTRUCTIONS = "instructions"
CONF_SCHEDULE = "schedule"
CONF_MEDIA_PLAYERS = "media_players"
CONF_MESSAGE_TEMPLATE = "message_template"
CONF_TEMPORARY = "temporary"  # runtime flag for temp courses

# Schedule fields
CONF_TYPE = "type"
CONF_TIME = "time"                    # "HH:MM"
CONF_DOSE_TIMES = "dose_times"        # ["HH:MM", ...] or string in service
CONF_START = "start"                  # ISO datetime for interval types
CONF_START_DATE = "start_date"        # "YYYY-MM-DD"
CONF_INTERVAL = "interval"            # int (hours or days)
CONF_LEAD_MINUTES = "lead_minutes"
CONF_WEEKDAYS = "weekdays"
CONF_COURSE_LENGTH_DAYS = "course_length_days"

# Escalation / caregiver
CONF_ESCALATION_MINUTES = "escalation_minutes"          # minutes after due
CONF_CAREGIVER_NOTIFY = "caregiver_notify"
CONF_CAREGIVER_NOTIFY_SERVICE = "caregiver_notify_service"

# Refill / ordering
CONF_REFILL_DATE = "refill_date"                        # "YYYY-MM-DD"
CONF_REFILL_DAYS_BEFORE = "refill_days_before"          # e.g. 7

# Schedule types
SCHEDULE_DAILY = "daily"
SCHEDULE_WEEKDAYS = "weekdays"
SCHEDULE_WEEKLY = "weekly"
SCHEDULE_EVERY_N_HOURS = "every_n_hours"
SCHEDULE_EVERY_N_DAYS = "every_n_days"
SCHEDULE_COURSE = "course"

# Services
SERVICE_MARK_TAKEN = "mark_taken"
SERVICE_SNOOZE = "snooze"
SERVICE_CREATE_TEMP_COURSE = "create_temp_course"

# Centralised icon URLs (optional – for docs / custom cards / future use)
TABLET_ICON_URL = "https://cdn-icons-png.flaticon.com/512/2966/2966327.png"
REFILL_ICON_URL = "https://cdn-icons-png.flaticon.com/512/12697/12697553.png"

TABLET_ICON_ATTRIBUTION = (
    "Tablet icons created by Freepik - Flaticon "
    "https://www.flaticon.com/free-icons/tablet"
)

REFILL_ICON_ATTRIBUTION = (
    "Refill icons created by Freepik - Flaticon "
    "https://www.flaticon.com/free-icons/refill"
)
