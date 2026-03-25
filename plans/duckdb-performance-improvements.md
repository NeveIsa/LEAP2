# DuckDB Write Performance Improvements

## Context

DuckDB is an OLAP (analytical) database optimized for bulk reads and columnar scans, not frequent small writes. LEAP2's hot path — logging every RPC call — does a synchronous, row-at-a-time INSERT with an immediate commit, which is the worst-case write pattern for DuckDB. This document outlines improvements to reduce the write bottleneck.

## Applied

### 1. `preserve_insertion_order = false`

**Status:** Done (2026-03-25)

Disables DuckDB's internal bookkeeping that tracks row insertion order. Reduces overhead on every write and lowers memory pressure. No functional impact since network requests arrive in nondeterministic order and all queries use explicit `ORDER BY`.

See `plans/configurable-db-backend.md` for full details.

## Proposed

### 2. Write-behind buffer

**Impact:** High
**Complexity:** Medium

Accumulate log entries in an in-memory buffer (or thread-safe queue) and flush to DuckDB in batches on a timer (e.g., every 500ms) or when a size threshold is reached (e.g., 50 rows). This converts many small INSERTs into fewer bulk INSERTs.

**Design sketch:**
- A background thread or `asyncio.Task` owns the flush loop
- `add_log()` appends to the buffer and returns immediately (fire-and-forget)
- Flush uses a single multi-row INSERT or DuckDB's Appender API
- On server shutdown, flush remaining buffer
- Trade-off: logs may be lost if the server crashes before a flush. Acceptable for educational experiment logs; could add a configurable `sync_mode` for critical experiments.

### 3. Async fire-and-forget logging

**Impact:** High
**Complexity:** Low–Medium

Move `storage.add_log()` off the RPC request path entirely. Currently, the client blocks until the log write commits. Instead:
- Submit the log write to a background task (`asyncio.create_task` or `asyncio.to_thread`)
- Return the RPC result to the student immediately
- The log persists asynchronously

This directly reduces request latency. Combines well with the write-behind buffer (#2).

### 4. Bulk COPY / Appender API for batch inserts

**Impact:** Medium
**Complexity:** Low

Replace SQLAlchemy ORM row inserts with DuckDB's native bulk-load mechanisms:
- **`COPY ... FROM`** for loading from files (CSV, Parquet)
- **DuckDB Appender API** (`duckdb.connect().appender()`) for programmatic batch inserts

The Appender API bypasses SQL parsing entirely and writes directly to DuckDB's columnar storage. This is significantly faster than ORM `session.add()` for batch operations like `bulk_add_students()`.

**Caveat:** Requires dropping down from SQLAlchemy ORM to raw `duckdb` connection for these paths.

### 5. WAL / checkpoint tuning

**Impact:** Low–Medium
**Complexity:** Low

DuckDB's WAL (Write-Ahead Log) checkpointing can be tuned:
- `checkpoint_threshold`: Controls how much WAL data accumulates before a checkpoint (default: 16MB). Increasing this reduces checkpoint frequency, improving write throughput at the cost of longer recovery time.
- `wal_autocheckpoint`: Can be disabled for bulk load scenarios, with a manual checkpoint at the end.

```sql
SET checkpoint_threshold = '64MB';
```

### 6. Configurable SQLite backend for write-heavy experiments

**Impact:** High
**Complexity:** Medium

Already planned in `plans/configurable-db-backend.md`. SQLite with WAL mode handles concurrent small writes much better than DuckDB. Experiments that don't need analytical queries can opt into SQLite via frontmatter (`db: sqlite`).

## Priority Order

1. **Async fire-and-forget** (#3) — biggest latency win, lowest complexity
2. **Write-behind buffer** (#2) — biggest throughput win, pairs with #3
3. **SQLite backend** (#6) — already planned, solves the problem at the architecture level
4. **Bulk Appender** (#4) — targeted win for batch operations
5. **WAL tuning** (#5) — incremental improvement
