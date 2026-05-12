# Home API

These endpoints return the weekly automated insight records used to populate the home page. Records are scoped to the current week (Sunday start date) and grouped by category.

## `GET /get/homePage`

Returns weekly YouTube insight records for three categories.

Also accessible at `GET /` (hidden from OpenAPI schema).

### Response `200 OK`

An array of three arrays, one per YouTube category, in this order:

1. Gaming (`category = 20`)
2. Science & Tech (`category = 28`)
3. How-to & Style (`category = 26`)

Each inner array contains Supabase row objects from `automatic_table` matching the current week and that category.

```json
[
  [ /* Gaming rows */ ],
  [ /* Science & Tech rows */ ],
  [ /* How-to & Style rows */ ]
]
```

An inner array is empty `[]` when no automated runs have completed for that category this week.

### Errors

| Status | Condition                                                      |
|--------|----------------------------------------------------------------|
| 503    | Supabase query failed for Gaming, Science & Tech, or Style data |

Each category fetch fails independently; the first failure stops processing and returns 503. See [errors.md](errors.md) for the response envelope.

---

## `GET /get/homePageAppStore`

Returns weekly App Store insight records for three genres.

### Response `200 OK`

An array of three arrays, one per App Store genre, in this order:

1. Games (`genre_id = 6014`)
2. Social Networking (`genre_id = 6005`)
3. Utilities (`genre_id = 6002`)

Each inner array contains Supabase row objects from `automatic_apple_table` matching the current week and that genre.

```json
[
  [ /* Games rows */ ],
  [ /* Social Networking rows */ ],
  [ /* Utilities rows */ ]
]
```

### Errors

| Status | Condition                                                         |
|--------|-------------------------------------------------------------------|
| 503    | Supabase query failed for Games, Social, or Utilities genre data  |

See [errors.md](errors.md) for the response envelope.
