# tav

**tav** is a terminal UI for exploring, filtering, querying, and summarizing JSON Lines (JSONL) time-series data.

Use it to inspect event streams, browse application logs, explore metrics, traces, data exports, debug event streams, and other newline-delimited JSON data directly from your terminal, without opening a Jupyter notebook, writing a script, or importing the file into Databricks or Snowflake.

<div style="display: flex; gap: 10px;">
  <img src="assets/tav_ui_details.png" width="45%" />
  <img src="assets/tav_stats.png" width="45%" />
</div>

## Why tav?

JSON Lines is great for logs, events, and streaming data, but large `.jsonl` files are hard to inspect with plain text tools.

**tav** gives you a fast, focused terminal interface for:

- viewing JSONL records as structured data
- working with timestamped / time-series events
- filtering and querying nested fields
- stats view for quick summaries
- reading files or piping data from stdin

If **tav** saves you from writing another one-off inspection script, consider starring the repo.

## Install

*Not on PyPI yet.*

```shell
uv tool install tav --from git+https://github.com/jsynowiec/tav
```

Or run from source:

```shell
git clone https://github.com/jsynowiec/tav
cd tav
uv run tav
```

## Usage

```shell
tav [INPUT] [OPTIONS]
```

### Examples

Open a JSONL file:

```shell
tav events.jsonl
```

Read JSONL from stdin:

```shell
cat events.jsonl | tav -
```

Use a custom timestamp field:

```shell
tav events.jsonl --time-field timestamp
```

Use a nested timestamp field:

```shell
tav events.jsonl --time-field $.event.created_at
```

Start in the stats view:

```shell
tav events.jsonl --stats
```

## Input format

`tav` expects JSON Lines (JSONL) format, which is a newline-delimited JSON:

```jsonl
{"timestamp":"2026-01-01T12:00:00Z","service":"api","duration_ms":42,"status":200}
{"timestamp":"2026-01-01T12:00:01Z","service":"worker","duration_ms":87,"status":200}
{"timestamp":"2026-01-01T12:00:02Z","service":"api","duration_ms":133,"status":500}
```

By default, `tav` looks for a timestamp field. You can point it to another field with `--time-field`.

## Options

```shell
Arguments:
  INPUT    Path to input JSONL file. Omit or use '-' for stdin.

Options:
  -h, --help            Show help and exit
  --time-field FIELD    Dot-path to the timestamp field, e.g. timestamp or $.timestamp
  --stats               Start in the stats view
  --version             Show version and exit
```

## Built with

`tav` is built with Python, Textual, and JMESPath.

## License

MIT
