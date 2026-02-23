# Architecture

## Purpose

- Build a garbage-collection calendar site backed by structured JSON data.
- Define API and page behavior based on `data/municipalities.json` and `data/calendars.json`.
- Core routes:
  - `GET /{slug}/{type}`
  - `GET /{slug}/{type}/{wardSlug}`

## Data Source

- File: `data/municipalities.json`
- Top-level keys:
  - `source_url`
  - `slug_source_url`
  - `generated_at`
  - `municipalities[]`
- File: `data/calendars.json`
  - Array of calendar entries
  - Each entry:
    - `municipality.slug`
    - `municipality.type`
    - `wardSlug` (optional)
    - `calendars[]`:
      - `name`
      - `iCalendar`
      - `googleCalendar`

## Domain Model

- `municipality` (top-level record):
  - `code` (string)
  - `name` (string)
  - `kana` (string)
  - `slug` (string)
  - `type` (`city` | `town` | `vill`)
  - `wards` (optional array of ward)
- `ward` (nested under municipality only):
  - `code` (string)
  - `name` (string)
  - `kana` (string)
  - `slug` (string)
  - `type` (currently `city`)
- `calendar entry`:
  - target municipality key: `(slug, type)`
  - optional target ward key: `wardSlug`
  - `calendars[]` for download/open links

## Identity Rules

- Top-level municipality lookup key:
  - `(slug, type)` is unique in `municipalities[]`.
- Ward is not a top-level entity.
- Ward lookup key:
  - `(parentMunicipality.slug, parentMunicipality.type, ward.slug)`
- Calendar lookup key:
  - municipality page: `(slug, type)`
  - ward page: `(slug, type, wardSlug)`

## Route and Endpoint Specification

### Page Routes (Static Build / SSG)

#### 1) `GET /{slug}/{type}`
- Municipality page.
- Displays municipality info and calendar list matched by `(slug, type)`.
- If no calendar entry exists, page still resolves and shows "no calendars yet".

#### 2) `GET /{slug}/{type}/{wardSlug}`
- Ward page under municipality.
- Displays parent + ward info and calendar list matched by `(slug, type, wardSlug)`.
- If ward exists but calendar entry is missing, page still resolves and shows empty-state.

- These pages are pre-rendered at build time.
- Runtime does not resolve data dynamically for page HTML.

## Static Build Strategy

### Build Input
- `data/municipalities.json`
- `data/calendars.json`

### Build Output (HTML)
- Municipality page:
  - route: `/{slug}/{type}`
  - file: `/{slug}/{type}/index.html`
- Ward page:
  - route: `/{slug}/{type}/{wardSlug}`
  - file: `/{slug}/{type}/{wardSlug}/index.html`

Examples:
- `/kodaira/city` -> `kodaira/city/index.html`
- `/kyoto/city/nishikyo` -> `kyoto/city/nishikyo/index.html`

### Page Generation Rules
- Generate one municipality page per `municipalities[]`.
- Generate ward pages only for wards present in `municipality.wards[]`.
- Calendar binding:
  - municipality page uses `calendarIndex[(slug,type)]`.
  - ward page uses `wardCalendarIndex[(slug,type,wardSlug)]`.
- If no calendar data exists, still generate the page and show an empty-state.

### Build-Time Validation
- Fail build if duplicate `(slug,type)` exists in municipalities.
- Fail build if a calendar target municipality does not exist.
- Fail build if a ward calendar target does not exist under the parent municipality.
- Warn (not fail) on municipality/ward pages with no calendars.

### Deploy Model
- Publish generated HTML/CSS/JS as static assets.
- Any data update requires rebuild + redeploy.

### JSON API (optional but recommended)

#### 1) GET `/api/{slug}/{type}`

- Purpose: Resolve one municipality.
- Path params:
  - `slug`: municipality slug
  - `type`: `city` | `town` | `vill`
- Behavior:
  - Find exact municipality by `(slug, type)`.
- Response:
  - `200 OK` with municipality payload.
  - Include `wards` if present in source.
- Errors:
  - `400 Bad Request`: invalid `type`.
  - `404 Not Found`: no municipality for `(slug, type)`.

Example:

- `GET /tokyo-nakano/city`
- `GET /esashi-1/town`

#### 2) GET `/api/{slug}/{type}/{wardSlug}`

- Purpose: Resolve ward under a municipality.
- Path params:
  - `slug`: municipality slug
  - `type`: municipality type
  - `wardSlug`: ward slug
- Behavior:
  1. Resolve municipality by `(slug, type)`.
  2. Search `municipality.wards[]` by `wardSlug`.
- Response:
  - `200 OK` with ward payload and parent summary.
- Errors:
  - `400 Bad Request`: invalid `type`.
  - `404 Not Found`: municipality not found.
  - `404 Not Found`: ward not found under resolved municipality.

Example:

- `GET /kyoto/city/nishikyo`

## Response Shapes

### Municipality Response (`GET /api/{slug}/{type}`)

```json
{
  "code": "26100",
  "name": "京都市",
  "kana": "ｷｮｳﾄｼ",
  "slug": "kyoto",
  "type": "city",
  "calendars": [
    {
      "name": "燃えるごみ",
      "iCalendar": "https://example.com/a.ics",
      "googleCalendar": "https://calendar.google.com/calendar/u/0?cid=..."
    }
  ],
  "wards": [
    {
      "code": "26111",
      "name": "西京区",
      "kana": "ﾆｼｷｮｳｸ",
      "slug": "nishikyo",
      "type": "city"
    }
  ]
}
```

### Ward Response (`GET /api/{slug}/{type}/{wardSlug}`)

```json
{
  "municipality": {
    "code": "26100",
    "name": "京都市",
    "slug": "kyoto",
    "type": "city"
  },
  "ward": {
    "code": "26111",
    "name": "西京区",
    "kana": "ﾆｼｷｮｳｸ",
    "slug": "nishikyo",
    "type": "city"
  },
  "calendars": [
    {
      "name": "燃えるごみ",
      "iCalendar": "https://example.com/b.ics",
      "googleCalendar": "https://calendar.google.com/calendar/u/0?cid=..."
    }
  ]
}
```

## Loading Strategy

- Load `data/municipalities.json` and `data/calendars.json` once at process start.
- Build in-memory indexes:
  - `municipalityIndex[(slug,type)] -> municipality`
  - `wardIndex[(slug,type,wardSlug)] -> ward + parent`
  - `calendarIndex[(slug,type)] -> calendars[]`
  - `wardCalendarIndex[(slug,type,wardSlug)] -> calendars[]`
- Rebuild indexes only on process restart (initial scope).

## Validation

- Enforce `type in {"city","town","vill"}` before lookup.
- Use exact slug match (case-sensitive as stored).
- Do not normalize/transform slugs in request path.
- Validate calendar URLs (`http/https`) when loading.

## Non-Goals (Current Scope)

- No fuzzy search endpoint.
- No separate ward top-level endpoint.
- No pagination/filtering endpoints.
- No live reloading of `municipalities.json`.
- No calendar editing UI (read-only publishing site).
