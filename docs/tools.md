# Agent Tool Reference

The agent has access to 10 typed tools. All write operations require explicit user confirmation before execution.

## Profile

| Tool | Action | Required params |
|---|---|---|
| `get_profile` | Read name, DOB, email, phone, bio | — |
| `update_profile` | Update one field | `field` (`name`/`dob`/`email`/`phone`/`bio`), `value` |

`dob` expects `YYYY-MM-DD`. Relative strings (`today`, `tomorrow`) are resolved automatically.
Setting `value` to `""` clears the field.

## Hobbies

| Tool | Action | Required params |
|---|---|---|
| `list_hobbies` | List all hobbies and skill levels | — |
| `add_hobby` | Add or update a hobby | `name`, `skill_level` (`beginner`/`intermediate`/`advanced`) |
| `remove_hobby` | Delete a hobby ⚠️ | `name` |

`add_hobby` upserts — if the hobby exists it updates the skill level.

## Events

| Tool | Action | Required params |
|---|---|---|
| `list_events` | List all events ordered by date | — |
| `create_event` | Schedule a new event | `title`, `date` (`YYYY-MM-DD`), `location` |
| `cancel_event` | Delete an event by ID ⚠️ | `event_id` (integer) |

Relative dates (`next Friday`, `tomorrow`) are resolved before writing.

## Settings

| Tool | Action | Required params |
|---|---|---|
| `get_settings` | Read all settings | — |
| `update_setting` | Change one setting ⚠️ | `key`, `value` |

Valid keys and allowed values:

| Key | Values |
|---|---|
| `theme` | `light` \| `dark` |
| `language` | any string |
| `notifications` | `on` \| `off` |
| `timezone` | IANA timezone string (e.g. `America/New_York`) |

⚠️ = destructive action — requires user confirmation before execution.
