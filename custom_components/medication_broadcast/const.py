"""Constants for the Medication Broadcast Assistant.

Everything that needs to stay consistent across the integration lives here.
It keeps the rest of the code clearer and avoids string-littered files.

Icon attribution is required under the Flaticon licence, so it is kept
both here and inside icons/ATTRIBUTION.txt. Note to self do check this
""""

# Domain -------------------------------------------------------------
DOMAIN = "medication_broadcast"

# Global config keys -------------------------------------------------
CONF_TTS_SERVICE = "tts_service"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_DEFAULT_MEDIA_PLAYERS = "default_media_players"
CONF_MEDS = "meds"

# Per-med config fields ----------------------------------------------
CONF_ID = "id"
CONF_NAME = "name"
CONF_ENABLED = "enabled"
CONF_INSTRUCTIONS = "instructions"
CONF_SCHEDULE = "schedule"
CONF_MEDIA_PLAYERS = "media_players"
CONF_MESSAGE_TEMPLATE = "message_template"
CONF_TEMPORARY = "temporary"   # Runtime temporary course flag

# Schedule fields ----------------------------------------------------
CONF_TYPE = "type"
CONF_TIME = "time"
CONF_DOSE_TIMES = "dose_times"
CONF_START = "start"
CONF_START_DATE = "start_date"
CONF_INTERVAL = "interval"
CONF_LEAD_MINUTES = "lead_minutes"
CONF_WEEKDAYS = "weekdays"
CONF_COURSE_LENGTH_DAYS = "course_length_days"

# Escalation + caregiver ---------------------------------------------
CONF_ESCALATION_MINUTES = "escalation_minutes"
CONF_CAREGIVER_NOTIFY = "caregiver_notify"
CONF_CAREGIVER_NOTIFY_SERVICE = "caregiver_notify_service"

# Refill / ordering --------------------------------------------------
CONF_REFILL_DATE = "refill_date"
CONF_REFILL_DAYS_BEFORE = "refill_days_before"

# Schedule type identifiers ------------------------------------------
SCHEDULE_DAILY = "daily"
SCHEDULE_WEEKDAYS = "weekdays"
SCHEDULE_WEEKLY = "weekly"
SCHEDULE_EVERY_N_HOURS = "every_n_hours"
SCHEDULE_EVERY_N_DAYS = "every_n_days"
SCHEDULE_COURSE = "course"

# Service names ------------------------------------------------------
SERVICE_MARK_TAKEN = "mark_taken"
SERVICE_SNOOZE = "snooze"
SERVICE_CREATE_TEMP_COURSE = "create_temp_course"

# Icon sizes ---------------------------------------------------------
# Standardised sizes so the icon utilities can pick the closest match.
ICON_SIZES = [16, 24, 32, 64, 128, 256, 512]
DEFAULT_ICON_SIZE = 128

# Flaticon attribution -------------------------------------------------
# Required by licence. Kept short so it is clear and unambiguous.
TABLET_ICON_ATTRIBUTION = "Tablet icons created by Freepik - Flaticon"
REFILL_ICON_ATTRIBUTION = "Refill icons created by Freepik - Flaticon"

# Developer notes -----------------------------------------------------
# These notes are mainly for future reference. Nothing here affects runtime.
#
# Keeping icon paths out of this file is intentional.
# The icon_utils module handles path generation and mirroring, which keeps
# this file clean and reduces maintenance effort. Or it should
#
# In general, this file is meant to stay as minimal as possible. A tidy
# constants module usually means fewer surprises elsewhere in the integration. Again double check after pevious...
