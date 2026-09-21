# Telemetry Pipeline API Examples

## 1. Batch Ingest

```bash
curl -X POST http://localhost:8080/api/v1/telemetry/ingest \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "points": [
      {
        "asset_id": "550e8400-e29b-41d4-a716-446655440000",
        "property_code": "temperature",
        "timestamp": "2026-09-07T12:00:00Z",
        "value": 22.5,
        "data_type": "FLOAT",
        "unit": "degC",
        "quality": "GOOD",
        "source_adapter": "bacnet"
      }
    ]
  }'
```

Response:
```json
{
  "success": true,
  "data": { "total": 1, "accepted": 1, "rejected": 0 },
  "error": null
}
```

## 2. Query with Aggregation

```bash
curl -X GET "http://localhost:8080/api/v1/telemetry/query?asset_id=550e8400-e29b-41d4-a716-446655440000&property_code=temperature&start_time=2026-09-01T00:00:00Z&end_time=2026-09-07T23:59:59Z&aggregate=avg&group_by=property" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## 3. Quality Score

```bash
curl -X GET "http://localhost:8080/api/v1/telemetry/quality/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## 4. Create Continuous Aggregate

```bash
curl -X POST http://localhost:8080/api/v1/telemetry/aggregates \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "550e8400-e29b-41d4-a716-446655440000",
    "level": "1h",
    "properties": ["temperature", "humidity"]
  }'
```

## 5. Get Config

```bash
curl -X GET http://localhost:8080/api/v1/telemetry/config \
  -H "Authorization: Bearer $JWT_TOKEN"
```
