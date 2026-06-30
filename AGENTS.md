## Standards

- Must comply with the ECMA-404 JSON data standard.
- Must use valid JMESPath for element query operations.

## Testing

Key patterns to follow:

- Standalone functions — no test classes, ever
- Use @pytest.mark.parametrize for every test that covers multiple inputs/outputs
- tmp_path fixture — for file-based I/O tests
- Plain assert — no unittest-style assertions
- Check both exit code and message — error tests assert result.exit_code != 0 AND the error string in result.stderr
- Test naming style: test_<behavior_being_tested> — descriptive, e.g. test_array_root_writes_each_item_per_line

## Work validation

Run `uv run ruff check --fix`, `uv run ruff format`, `uv run ty check --fix` and `uv pytest` when finishing work.

All checks and tests must pass before claiming the work is done.
