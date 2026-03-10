# tav

The Time-Series Viewer, **tav**, is a simple, convenient terminal tool for viewing Time-Series data stored in JSON Lines (JSONL) format. It provides an easy-to-use interface for analyzing, filtering and querying the data, as well as some basic stats and aggregated metrics.

## Run Locally

```shell
git clone https://github.com/jsynowiec/tav && cd tav
uv run tav
```

## Usage

```shell
tav [INPUT] [OPTIONS]

Arguments:
  INPUT    Path to input JSONL file including TSS data. Omit or use '-' for stdin.

Options:
  --time-field JSONPATH   JSONPath pointing to the timestamp in the TSS data.
                          If not provided, the tool will try to auto-guess it from the top-level fields.
  --stats                 Start in the stats view.
  --help                  Show help and exit.
```
