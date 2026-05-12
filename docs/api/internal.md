# Internal API

These endpoints are excluded from the OpenAPI schema (`include_in_schema=False`) and are not intended for external or frontend use.

## `POST /data/send`

Persists a raw data payload to the configured storage backend via the persistence service. Used by the automated pipeline to save processed insight records.

### Request

```json
{
  "data": { }
}
```

| Field  | Type   | Required | Description                                         |
|--------|--------|----------|-----------------------------------------------------|
| `data` | object | yes      | Arbitrary JSON object to be saved                   |

### Response `200 OK`

Empty body (`null`). The endpoint does not return a confirmation payload.

### Errors

| Status | Condition                              |
|--------|----------------------------------------|
| 422    | Request body is missing or malformed   |

See [errors.md](errors.md) for the response envelope.
