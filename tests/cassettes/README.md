# Cassettes

`pytest-recording` (VCR) is in the stack so you can record real Tavily
web-search responses once and replay them offline:

```bash
pytest --record-mode=once tests/   # records into this folder on first run
```

The asserted **safety** tests (`test_injection.py`) do not depend on a recorded
cassette: they inject the malicious payload through a deterministic in-process
fake (`monkeypatch` of `_tavily_search`), so the prompt-injection invariant is
verified with zero network and zero flakiness in CI. Record cassettes here if
you add tests that exercise the live web-search code path end to end.
