# Medication-Broadcast-Home-Assistant
I built this because "take your meds on time" sounds simple, and then reality gets involved. Patches every 96 hours. Antibiotics for 7 days, 3 times a day. Weekly injections on Thursdays. Refill dates that sneak up on you and catch you short.  I wanted Home Assistant to nag properly. Not just a single notification.

# Medication Broadcast Assistant

I built this because "take your meds on time" sounds simple, and then reality gets involved. Patches every 96 hours. Antibiotics for 7 days, 3 times a day. Weekly injections on Thursdays. Refill dates that sneak up on you and catch you short.

I wanted Home Assistant to nag properly. Not just a single notification that disappears under a pile of junk, but structured reminders through speakers, with escalation if I ignore them, and sensible handling of awkward schedules.

This integration is the result.

---

## What this thing actually does

Medication Broadcast Assistant sits on top of Home Assistant and turns your medication schedule into:

- Spoken reminders on your chosen speakers  
- Optional mobile notifications  
- Clear "next dose" sensors for each medication  
- Binary sensors that show when something is due or overdue  
- Refill reminders before you run out  

It handles simple cases like "every morning at 08:30" and more irritating realities like "change this patch every 96 hours with a 15 minute warning and escalate if I ignore it for 30 minutes, and tell my partner if I am still pretending it does not exist".

You define your meds and schedules in YAML. The integration deals with the timing, tracking and shouty bits.

---

## Core idea

The mental model is straightforward:

- Each medication is a schedule plus some text  
- The schedule decides when a dose is due  
- A "lead time" decides when to bother you beforehand  
- The system broadcasts a reminder on your speakers and, optionally, via notify  
- If you do not mark it taken, it can escalate after a grace period  
- Sensors exist so your dashboard can show what is next, what is due and how late you are  

It is not pretending to be a clinical system. It is a blunt automation layer so you do not have to keep the entire regime in your head.

---

## What it supports

### Schedule types

You get several schedule types:

- `daily`  
  - One or more dose times every day  
  - Example: 08:30 every day, or 08:00 and 20:00  

- `weekdays`  
  - Same as daily, but Monday to Friday  

- `weekly`  
  - Specific weekdays at a specific time  
  - Example: Thursday at 19:00 for a weekly injection  

- `every_n_hours`  
  - Interval based, in hours  
  - Example: 96 hours for a patch, where "every 4 days" is a bit hand-wavy  

- `every_n_days`  
  - Interval based, in days, starting from a given date  

- `course`  
  - Fixed length courses like antibiotics  
  - Example: from 1 January for 7 days, 3 doses per day, then it stops itself  

You can define:

- Single `time` like `"08:30"`  
- Or a list of `dose_times` like `["08:00", "14:00", "20:00"]`  
- Or a comma separated string for temporary courses like `"08:00, 14:00, 20:00"`  

Pick whatever matches the chaos you are dealing with.

---

## Reminders and escalation

Each medication can have:

- `lead_minutes`  
  - How many minutes before the due time the reminder should play  
  - Example: reminder at 19:45 for a 20:00 patch change  

- `escalation_minutes`  
  - How long after the due time it should escalate if you have not acknowledged anything  
  - Escalation is a second, slightly sharper broadcast  

You can also optionally set:

- `caregiver_notify`  
- `caregiver_notify_service`  

If both are set, escalation will also send a notification via that service, with a warning that the caregiver has been notified. Gentle social pressure, automated and relentless.

You can snooze an active reminder by a number of minutes if you are in the middle of something and cannot deal with it right that second.

---

## Temporary courses

Not everything is permanent. Sometimes a doctor announces a 7 day antibiotic course and your life acquires a small, tedious side quest.

Editing YAML every time is a faff, so there is a service:

`medication_broadcast.create_temp_course`

You call it with:

- an ID  
- a name  
- instructions  
- a length in days  
- dose times  

and it spins up a full schedule as a temporary medication. It behaves like any other:

- It has spoken reminders  
- It can escalate  
- It shows up as a sensor and a binary sensor  
- It ends after the course end  

Temporary courses are not persisted across Home Assistant restart, on purpose. Finish the course and move on.

---

## Refills and ordering

You can specify:

- `refill_date`: the date you expect to run out  
- `refill_days_before`: how many days before that you want to be nagged  

The integration will schedule a one shot refill reminder at 09:00 local time on:

`refill_date - refill_days_before`

That reminder can broadcast via your speakers and via a general notification. Use it for "order more patches a week before I run out" instead of realising you are on the last one while staring at an empty box over the bin.

Attribution for the refill icon used in related visuals is embedded in the code:

- "Refill icons created by Freepik - Flaticon"  
- https://www.flaticon.com/free-icons/refill  

---

## Sensors so the dashboard can behave

For each medication there are entities.

### Sensor

`sensor.medication_next_<id>`

- State: ISO timestamp of the next reminder, or `"none"`  
- Attributes include:
  - `due_at`  
  - `lead_minutes`  
  - `interval`  
  - `dose_times`  
  - `course_end` if applicable  
  - `pending_ack`  
  - `escalated`  
  - `overdue_minutes` (0 if not overdue or not pending)  
  - `refill_date`, `refill_reminder_at`  

You can use this to show a list of upcoming doses, or to build your own slightly neurotic dashboard that tells you what you are currently ignoring.

### Binary sensor

`binary_sensor.medication_due_<id>`

- On when:
  - the medication is enabled  
  - a dose is pending acknowledgement  
  - current time is at or past the due time  

Attributes include:

- `overdue_minutes`  
- `pending_ack`  
- `escalated`  

Use this to change colours, trigger automations, or quietly judge yourself when something has been lit up as "due" for 40 minutes while you potter about pretending you have not seen it.

---

## How it talks

The integration uses:

- your configured `tts_service`, default `tts.google_translate_say`  
- `notify_service` if you set one globally  
- per medication `media_players`, or a global `default_media_players`  

Each reminder is a simple message, either:

- custom `message_template` like `"Patch reminder for {name}. {instructions}"`  
- or a generic format that includes the medication name and instructions  

You do not need to wrestle a full templating engine to get something useful. You can ignore templates entirely and just use straight instructions if that suits you.

---

## Configuration overview

Everything starts from `configuration.yaml` like this:

```yaml
medication_broadcast:
  tts_service: tts.google_translate_say
  notify_service: notify.mobile_app_my_phone

  default_media_players:
    - media_player.living_room_speaker
    - media_player.kitchen_speaker

  meds:
    - id: estradiol_patch
      name: Estradiol patch
      enabled: true
      instructions: "Change patch and dispose of the old one."
      media_players:
        - media_player.bedroom_speaker
      message_template: "Patch reminder for {name}. {instructions}"
      schedule:
        type: every_n_hours
        interval: 96
        start: "2025-01-01T20:00:00"
        lead_minutes: 15
        escalation_minutes: 30
        caregiver_notify: true
        caregiver_notify_service: notify.partner_phone
        refill_date: "2025-03-01"
        refill_days_before: 7
