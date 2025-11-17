"""Core scheduling + broadcast logic for Medication Broadcast Assistant.

Notes to future me:

- This is the actual brain. Everything else is UI or bureaucracy.
- Keep it explicit and boring. Clever code breaks at 3 a.m.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_ID,
    CONF_NAME,
    CONF_ENABLED,
    CONF_INSTRUCTIONS,
    CONF_SCHEDULE,
    CONF_MEDIA_PLAYERS,
    CONF_DEFAULT_MEDIA_PLAYERS,
    CONF_TTS_SERVICE,
    CONF_NOTIFY_SERVICE,
    CONF_MESSAGE_TEMPLATE,
    CONF_TYPE,
    CONF_TIME,
    CONF_DOSE_TIMES,
    CONF_START,
    CONF_START_DATE,
    CONF_INTERVAL,
    CONF_LEAD_MINUTES,
    CONF_WEEKDAYS,
    CONF_COURSE_LENGTH_DAYS,
    CONF_ESCALATION_MINUTES,
    CONF_CAREGIVER_NOTIFY,
    CONF_CAREGIVER_NOTIFY_SERVICE,
    CONF_REFILL_DATE,
    CONF_REFILL_DAYS_BEFORE,
    SCHEDULE_DAILY,
    SCHEDULE_WEEKDAYS,
    SCHEDULE_WEEKLY,
    SCHEDULE_EVERY_N_HOURS,
    SCHEDULE_EVERY_N_DAYS,
    SCHEDULE_COURSE,
)


_LOGGER = logging.getLogger(__name__)


@dataclass
class Medication:
    """Runtime representation of one medication schedule."""

    med_id: str
    name: str
    enabled: bool
    instructions: str
    schedule_type: str

    # Schedule parameters
    time: Optional[str] = None              # single time "HH:MM"
    dose_times: List[str] = field(default_factory=list)  # multiple daily dose times
    start: Optional[str] = None             # ISO datetime (interval types)
    start_date: Optional[str] = None        # YYYY-MM-DD
    interval: Optional[int] = None          # hours or days
    lead_minutes: int = 0
    weekdays: List[int] = field(default_factory=list)
    course_length_days: Optional[int] = None

    # Escalation / caregiver
    escalation_minutes: Optional[int] = None
    caregiver_notify: bool = False
    caregiver_notify_service: Optional[str] = None

    # Refill / ordering
    refill_date: Optional[date] = None
    refill_days_before: Optional[int] = None
    refill_reminder_at: Optional[datetime] = None

    # Output routing
    media_players: List[str] = field(default_factory=list)
    message_template: Optional[str] = None

    # Book-keeping
    temporary: bool = False   # set True for temp courses created via service

    # Internal state
    next_trigger: Optional[datetime] = None   # next reminder (lead) time
    due_at: Optional[datetime] = None         # next dose due time
    course_end: Optional[datetime] = None
    pending_ack: bool = False
    escalated: bool = False
    escalation_at: Optional[datetime] = None


class MedicationManager:
    """Translate configuration into timers, TTS calls, and sensor state."""

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        self.hass = hass
        self.config = config

        self._meds: Dict[str, Medication] = {}
        self._unsub: Dict[str, Any] = {}
        self._escalation_unsub: Dict[str, Any] = {}
        self._refill_unsub: Dict[str, Any] = {}

        # Global routing options
        self._tts_service: str = config.get(CONF_TTS_SERVICE, "tts.google_translate_say")
        self._notify_service: Optional[str] = config.get(CONF_NOTIFY_SERVICE)
        self._default_players: List[str] = config.get(CONF_DEFAULT_MEDIA_PLAYERS, [])

    async def async_setup(self) -> None:
        """Set up from YAML or config entry data."""
        meds_conf = self.config.get("meds", [])

        if not meds_conf:
            _LOGGER.warning("%s: no meds defined. Decorative integration, that.", DOMAIN)

        for med_conf in meds_conf:
            med = self._create_medication(med_conf)
            self._meds[med.med_id] = med

            if not med.enabled:
                _LOGGER.info("Medication %s is disabled; not scheduling.", med.med_id)
                continue

            self._schedule_next(med, initial=True)
            self._schedule_refill(med)

    # --------------------------------------------------------------------- utils

    def _create_medication(self, conf: ConfigType) -> Medication:
        """Build a Medication instance from YAML config."""
        med_id = conf.get(CONF_ID)
        if not med_id:
            raise ValueError("Medication entry missing 'id' field")

        schedule = conf.get(CONF_SCHEDULE, {})
        schedule_type = schedule.get(CONF_TYPE, SCHEDULE_DAILY)

        dose_times = schedule.get(CONF_DOSE_TIMES, []) or []
        if dose_times and schedule.get(CONF_TIME):
            _LOGGER.info(
                "Medication %s has both 'time' and 'dose_times'; using dose_times only.",
                med_id,
            )

        escalation_minutes = schedule.get(CONF_ESCALATION_MINUTES)
        if escalation_minutes is not None and escalation_minutes <= 0:
            escalation_minutes = None

        # Refill / order alert
        refill_dt: Optional[date] = None
        refill_str = schedule.get(CONF_REFILL_DATE)
        if refill_str:
            try:
                year, month, day = [int(x) for x in refill_str.split("-")]
                refill_dt = date(year, month, day)
            except Exception:
                _LOGGER.error("Medication %s has invalid refill_date '%s'", med_id, refill_str)

        refill_days_before: Optional[int] = schedule.get(CONF_REFILL_DAYS_BEFORE)
        if refill_days_before is not None and refill_days_before < 0:
            refill_days_before = None

        med = Medication(
            med_id=med_id,
            name=conf.get(CONF_NAME, med_id),
            enabled=conf.get(CONF_ENABLED, True),
            instructions=conf.get(CONF_INSTRUCTIONS, ""),
            schedule_type=schedule_type,
            time=None if dose_times else schedule.get(CONF_TIME),
            dose_times=dose_times,
            start=schedule.get(CONF_START),
            start_date=schedule.get(CONF_START_DATE),
            interval=schedule.get(CONF_INTERVAL),
            lead_minutes=schedule.get(CONF_LEAD_MINUTES, 0),
            weekdays=schedule.get(CONF_WEEKDAYS, []),
            course_length_days=schedule.get(CONF_COURSE_LENGTH_DAYS),
            escalation_minutes=escalation_minutes,
            caregiver_notify=schedule.get(CONF_CAREGIVER_NOTIFY, False),
            caregiver_notify_service=schedule.get(CONF_CAREGIVER_NOTIFY_SERVICE),
            refill_date=refill_dt,
            refill_days_before=refill_days_before,
            media_players=conf.get(CONF_MEDIA_PLAYERS, []),
            message_template=conf.get(CONF_MESSAGE_TEMPLATE),
            temporary=False,
        )

        # Course end
        if med.schedule_type == SCHEDULE_COURSE:
            if med.start_date and med.course_length_days:
                first_time = med.dose_times[0] if med.dose_times else (med.time or "08:00")
                start_dt = self._combine_date_time(med.start_date, first_time)
                med.course_end = start_dt + timedelta(days=med.course_length_days)
            else:
                _LOGGER.error(
                    "Medication %s is a course but missing start_date/course_length_days",
                    med.med_id,
                )

        return med

    def _combine_date_time(self, date_str: str, time_str: str) -> datetime:
        """Combine a date and time string into a localised datetime."""
        year, month, day = [int(x) for x in date_str.split("-")]
        hour, minute = [int(x) for x in time_str.split(":")]
        return dt_util.as_local(datetime(year, month, day, hour, minute, 0, 0))

    @staticmethod
    def _parse_iso_or_none(value: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime or return None."""
        if not value:
            return None
        dt = dt_util.parse_datetime(value)
        if dt is None:
            return None
        return dt_util.as_local(dt)

    def _now(self) -> datetime:
        return dt_util.as_local(dt_util.utcnow())

    # ------------------------------------------------------------------- schedule

    def _schedule_next(self, med: Medication, *, initial: bool = False) -> None:
        """Calculate and register the next reminder + due time."""
        now = self._now()
        med.pending_ack = False
        med.escalated = False
        med.escalation_at = None

        if not med.enabled:
            self._cancel_timer(med.med_id)
            self._cancel_escalation_timer(med.med_id)
            _LOGGER.debug("Medication %s disabled; skipping schedule.", med.med_id)
            return

        base_due: Optional[datetime] = None

        try:
            if med.schedule_type == SCHEDULE_EVERY_N_HOURS:
                base_due = self._due_every_n_hours(med, now)
            elif med.schedule_type == SCHEDULE_EVERY_N_DAYS:
                base_due = self._due_every_n_days(med, now)
            elif med.schedule_type in (SCHEDULE_DAILY, SCHEDULE_WEEKDAYS, SCHEDULE_WEEKLY):
                base_due = self._due_daily_like(med, now)
            elif med.schedule_type == SCHEDULE_COURSE:
                base_due = self._due_course(med, now)
            else:
                _LOGGER.error(
                    "Medication %s has unknown schedule type %s",
                    med.med_id,
                    med.schedule_type,
                )
        except ValueError as exc:
            _LOGGER.error("Medication %s configuration error: %s", med.med_id, exc)
            base_due = None

        if base_due is None:
            _LOGGER.info(
                "Medication %s has no next dose (course finished or config invalid).",
                med.med_id,
            )
            med.due_at = None
            med.next_trigger = None
            self._cancel_timer(med.med_id)
            self._cancel_escalation_timer(med.med_id)
            return

        med.due_at = base_due
        med.next_trigger = self._apply_lead(base_due, med)

        self._cancel_timer(med.med_id)

        @callback
        def _fire(_now: datetime) -> None:
            self._handle_fire(med.med_id)

        self._unsub[med.med_id] = async_track_point_in_time(
            self.hass, _fire, med.next_trigger
        )

        if initial:
            _LOGGER.info(
                "Scheduled %s due at %s (reminder at %s)",
                med.med_id,
                med.due_at,
                med.next_trigger,
            )
        else:
            _LOGGER.debug(
                "Rescheduled %s due at %s (reminder at %s)",
                med.med_id,
                med.due_at,
                med.next_trigger,
            )

    def _schedule_refill(self, med: Medication) -> None:
        """Schedule a one-shot refill reminder, if configured."""
        self._cancel_refill_timer(med.med_id)

        if not med.refill_date or med.refill_days_before is None:
            return

        reminder_day = med.refill_date - timedelta(days=med.refill_days_before)
        reminder_dt = datetime.combine(reminder_day, datetime.min.time())
        reminder_dt = dt_util.as_local(reminder_dt.replace(hour=9, minute=0))

        now = self._now()
        if reminder_dt <= now:
            _LOGGER.info(
                "Refill reminder for %s is in the past; not scheduling automatically.",
                med.med_id,
            )
            return

        med.refill_reminder_at = reminder_dt

        @callback
        def _refill(_now: datetime) -> None:
            self._handle_refill(med.med_id)

        self._refill_unsub[med.med_id] = async_track_point_in_time(
            self.hass, _refill, reminder_dt
        )
        _LOGGER.info(
            "Refill reminder for %s scheduled at %s", med.med_id, reminder_dt.isoformat()
        )

    def _cancel_timer(self, med_id: str) -> None:
        unsub = self._unsub.pop(med_id, None)
        if unsub is not None:
            unsub()

    def _cancel_escalation_timer(self, med_id: str) -> None:
        unsub = self._escalation_unsub.pop(med_id, None)
        if unsub is not None:
            unsub()

    def _cancel_refill_timer(self, med_id: str) -> None:
        unsub = self._refill_unsub.pop(med_id, None)
        if unsub is not None:
            unsub()

    def _apply_lead(self, due: datetime, med: Medication) -> datetime:
        return due - timedelta(minutes=med.lead_minutes or 0)

    def _require_interval(self, med: Medication) -> int:
        if not med.interval or med.interval <= 0:
            raise ValueError("interval must be a positive integer")
        return med.interval

    # ---- base due-time calculations ------------------------------------------

    def _due_every_n_hours(self, med: Medication, now: datetime) -> datetime:
        interval = self._require_interval(med)
        base = self._parse_iso_or_none(med.start) or now

        while base <= now:
            base = base + timedelta(hours=interval)
        return base

    def _due_every_n_days(self, med: Medication, now: datetime) -> datetime:
        interval = self._require_interval(med)
        if med.start_date:
            base = self._combine_date_time(med.start_date, med.time or "08:00")
        else:
            base = now

        while base <= now:
            base = base + timedelta(days=interval)
        return base

    def _daily_dose_times(self, med: Medication) -> List[str]:
        """Return sorted list of 'HH:MM' times for a day."""
        if med.dose_times:
            return sorted(med.dose_times)
        if med.time:
            return [med.time]
        raise ValueError("daily/weekly/course requires 'time' or 'dose_times'")

    def _day_allowed(self, med: Medication, dt_day: datetime) -> bool:
        if med.schedule_type == SCHEDULE_DAILY:
            return True
        if med.schedule_type == SCHEDULE_WEEKDAYS:
            return dt_day.weekday() < 5
        if med.schedule_type == SCHEDULE_WEEKLY:
            return dt_day.weekday() in med.weekdays
        return True

    def _due_daily_like(self, med: Medication, now: datetime) -> datetime:
        times = self._daily_dose_times(med)
        candidate_day = now.date()

        while True:
            base_day = datetime.combine(candidate_day, datetime.min.time())
            base_day = dt_util.as_local(base_day)

            if self._day_allowed(med, base_day):
                for t_str in times:
                    h, m = [int(x) for x in t_str.split(":")]
                    candidate = base_day.replace(hour=h, minute=m, second=0, microsecond=0)
                    if candidate > now:
                        return candidate

            candidate_day = candidate_day + timedelta(days=1)

    def _due_course(self, med: Medication, now: datetime) -> Optional[datetime]:
        if not med.start_date or not med.course_end:
            raise ValueError("course requires start_date and course_length_days")

        times = self._daily_dose_times(med)
        start_day = datetime.strptime(med.start_date, "%Y-%m-%d").date()
        candidate_day = max(start_day, now.date())

        while True:
            if candidate_day > med.course_end.date():
                _LOGGER.info("Course for %s finished.", med.med_id)
                return None

            base_day = datetime.combine(candidate_day, datetime.min.time())
            base_day = dt_util.as_local(base_day)

            for t_str in times:
                h, m = [int(x) for x in t_str.split(":")]
                candidate = base_day.replace(hour=h, minute=m, second=0, microsecond=0)
                if candidate > now and candidate <= med.course_end:
                    return candidate

            candidate_day = candidate_day + timedelta(days=1)

    # ------------------------------------------------------------------- actions

    def _targets_for(self, med: Medication) -> List[str]:
        return med.media_players or self._default_players

    async def async_mark_taken(self, med_id: str) -> None:
        """Mark a dose taken and reschedule from now."""
        med = self._meds.get(med_id)
        if not med:
            _LOGGER.warning("mark_taken called for unknown med %s", med_id)
            return

        med.pending_ack = False
        med.escalated = False        # noqa: E221
        self._cancel_escalation_timer(med.med_id)

        _LOGGER.debug("Marking dose taken for %s", med_id)
        self._schedule_next(med, initial=False)

    async def async_snooze(self, med_id: str, minutes: int) -> None:
        """Snooze the reminder for a dose by N minutes."""
        med = self._meds.get(med_id)
        if not med:
            _LOGGER.warning("snooze called for unknown med %s", med_id)
            return

        if not med.next_trigger:
            _LOGGER.debug("snooze called for %s with no active reminder", med_id)
            return

        med.next_trigger = med.next_trigger + timedelta(minutes=minutes)
        _LOGGER.info("Snoozed %s by %s minutes → %s", med.med_id, minutes, med.next_trigger)

        self._cancel_timer(med.med_id)

        @callback
        def _fire(_now: datetime) -> None:
            self._handle_fire(med.med_id)

        self._unsub[med.med_id] = async_track_point_in_time(
            self.hass, _fire, med.next_trigger
        )

    def _message_for(self, med: Medication, *, escalated: bool = False) -> str:
        """Render spoken / pushed message."""
        if med.message_template:
            return med.message_template.format(
                name=med.name,
                instructions=med.instructions,
            )

        if escalated:
            base = f"Important. Second reminder for {med.name}."
        else:
            base = f"Medication reminder for {med.name}."

        if med.instructions:
            return f"{base} {med.instructions}"
        return base

    def _schedule_escalation(self, med: Medication) -> None:
        """Schedule a single escalation, relative to due time."""
        self._cancel_escalation_timer(med.med_id)

        if not med.escalation_minutes or not med.due_at:
            return

        med.escalation_at = med.due_at + timedelta(minutes=med.escalation_minutes)

        now = self._now()
        if med.escalation_at <= now:
            return

        @callback
        def _escalate(_now: datetime) -> None:
            self._handle_escalation(med.med_id)

        self._escalation_unsub[med.med_id] = async_track_point_in_time(
            self.hass, _escalate, med.escalation_at
        )

    def _handle_fire(self, med_id: str) -> None:
        """Reminder callback (lead-time)."""
        med = self._meds.get(med_id)
        if not med:
            return

        if not med.enabled:
            _LOGGER.debug("Timer fired for disabled med %s; ignoring.", med_id)
            return

        _LOGGER.info("Medication reminder firing for %s", med.med_id)

        message = self._message_for(med, escalated=False)
        targets = self._targets_for(med)

        if targets:
            self._call_tts(targets, message)
        else:
            _LOGGER.warning("No media players configured for %s; nothing to say.", med.med_id)

        if self._notify_service:
            self._call_notify(self._notify_service, message)

        med.pending_ack = True
        med.escalated = False
        self._schedule_escalation(med)

        # Next dose schedule; due_at now refers to the upcoming dose.
        self._schedule_next(med, initial=False)

    def _handle_escalation(self, med_id: str) -> None:
        """Escalation callback when dose is overdue + margin and still not acked."""
        med = self._meds.get(med_id)
        if not med:
            return

        if not med.pending_ack or med.escalated:
            return

        med.escalated = True
        _LOGGER.info("Escalation firing for %s", med.med_id)

        message = self._message_for(med, escalated=True)
        targets = self._targets_for(med)

        if targets:
            self._call_tts(targets, message)

        if med.caregiver_notify and med.caregiver_notify_service:
            self._call_notify(
                med.caregiver_notify_service,
                message + " Caregiver has been notified.",
            )

        self._cancel_escalation_timer(med.med_id)

    def _handle_refill(self, med_id: str) -> None:
        """Refill reminder callback (order medication)."""
        med = self._meds.get(med_id)
        if not med:
            return

        _LOGGER.info("Refill reminder firing for %s", med.med_id)

        message = f"Medication refill reminder for {med.name}. Please order more."

        targets = self._targets_for(med)
        if targets:
            self._call_tts(targets, message)

        if self._notify_service:
            self._call_notify(self._notify_service, message)

        self._cancel_refill_timer(med.med_id)

    # ------------------------------------------------------------------- temp course

    async def async_create_temp_course(self, data: Dict[str, Any]) -> str:
        """Create a temporary course (e.g. antibiotics) on the fly."""
        med_id = data.get("med_id")
        if not med_id:
            raise ValueError("create_temp_course requires med_id")

        existing = self._meds.get(med_id)
        if existing and not existing.temporary:
            raise ValueError(f"Medication {med_id} already exists and is not temporary")

        name = data.get("name", med_id)
        instructions = data.get("instructions", "")

        # dose_times can be a list or a comma-separated string
        raw_dose_times = data.get("dose_times")
        dose_times: list[str] = []
        if isinstance(raw_dose_times, list):
            dose_times = [str(t).strip() for t in raw_dose_times if str(t).strip()]
        elif isinstance(raw_dose_times, str):
            dose_times = [part.strip() for part in raw_dose_times.split(",") if part.strip()]

        time_str = None if dose_times else data.get("time")
        course_length = int(data.get("course_length_days", 7))
        lead_minutes = int(data.get("lead_minutes", 0))
        escalation_minutes = data.get("escalation_minutes")
        if escalation_minutes is not None:
            escalation_minutes = int(escalation_minutes)

        caregiver_notify = bool(data.get("caregiver_notify", False))
        caregiver_notify_service = data.get("caregiver_notify_service")
        media_players = data.get("media_players") or []
        message_template = data.get("message_template")

        start_date_str = data.get("start_date")
        if not start_date_str:
            today = dt_util.as_local(dt_util.utcnow()).date()
            start_date_str = today.isoformat()

        med = Medication(
            med_id=med_id,
            name=name,
            enabled=True,
            instructions=instructions,
            schedule_type=SCHEDULE_COURSE,
            time=time_str,
            dose_times=dose_times,
            start=None,
            start_date=start_date_str,
            interval=None,
            lead_minutes=lead_minutes,
            weekdays=[],
            course_length_days=course_length,
            escalation_minutes=escalation_minutes,
            caregiver_notify=caregiver_notify,
            caregiver_notify_service=caregiver_notify_service,
            refill_date=None,
            refill_days_before=None,
            media_players=media_players,
            message_template=message_template,
            temporary=True,
        )

        first_time = med.dose_times[0] if med.dose_times else (med.time or "08:00")
        start_dt = self._combine_date_time(med.start_date, first_time)
        med.course_end = start_dt + timedelta(days=course_length)

        self._meds[med_id] = med
        self._schedule_next(med, initial=True)

        _LOGGER.info(
            "Created temporary course %s (%s days, times %s)",
            med.med_id,
            course_length,
            med.dose_times or [med.time],
        )

        return med_id

    # ------------------------------------------------------------------- helpers

    def _call_tts(self, targets: List[str], message: str) -> None:
        try:
            domain, service_name = self._tts_service.split(".", 1)
        except ValueError:
            _LOGGER.error("Invalid tts_service '%s'", self._tts_service)
            return

        payload = {"entity_id": targets, "message": message}
        self.hass.async_create_task(
            self.hass.services.async_call(domain, service_name, payload)
        )

    def _call_notify(self, service: str, message: str) -> None:
        try:
            domain, service_name = service.split(".", 1)
        except ValueError:
            _LOGGER.error("Invalid notify service '%s'", service)
            return

        payload = {"message": message, "title": "Medication"}
        self.hass.async_create_task(
            self.hass.services.async_call(domain, service_name, payload)
        )

    # ------------------------------------------------------------------- sensor API

    def medication_ids(self) -> List[str]:
        return list(self._meds.keys())

    def get_medication(self, med_id: str) -> Optional[Medication]:
        return self._meds.get(med_id)

    def all_medications(self) -> List[Medication]:
        return list(self._meds.values())
