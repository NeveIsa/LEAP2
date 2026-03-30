# Database & Log Schema

## Database

Per-experiment DuckDB file at `experiments/<name>/db/experiment.db`. SQLAlchemy 2.0 ORM.

### students

| Column | Type | Constraints |
|---|---|---|
| `student_id` | VARCHAR | PRIMARY KEY |
| `name` | VARCHAR | NOT NULL |
| `email` | VARCHAR | NULL |

### logs

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY (Sequence-based autoincrement) |
| `ts` | TIMESTAMP | NOT NULL, indexed |
| `student_id` | VARCHAR | NOT NULL, indexed |
| `experiment` | VARCHAR | NOT NULL, indexed |
| `trial` | VARCHAR | NULL |
| `func_name` | VARCHAR | NOT NULL, indexed |
| `args_json` | TEXT | NOT NULL |
| `result_json` | TEXT | NULL |
| `error` | TEXT | NULL |

The `experiment` column is redundant within a single per-experiment DB but kept for portability — enables merging DBs for cross-experiment analysis and exports.

## Log Schema (Data Contract)

Every log entry returned by the API and Log Client follows this shape:

```json
{
  "id": 1,
  "ts": "2025-02-24T12:00:00Z",
  "student_id": "s001",
  "experiment": "default",
  "trial": "bisection-demo",
  "func_name": "square",
  "args": [7],
  "result": 49,
  "error": null
}
```

The DB stores raw JSON strings (`args_json`, `result_json` TEXT columns); the API parses them into `args` and `result` fields before returning.
