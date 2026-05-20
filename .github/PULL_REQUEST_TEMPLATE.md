<!--
This is the default PR description. Fill in each section with concrete,
specific content. The point is evidence of evaluation, not polished prose.
See .github/TEST_REPORT_TEMPLATE.md for the standalone template.
-->

## What changed

One or two sentences describing the change.

## Why

One or two sentences on the problem or motivation.

## Verification

For each test you ran: the exact command, captured output (or a trimmed
excerpt of the relevant lines), and one line interpreting it.

### smoke_test.py

```sh
uv run python scripts/smoke_test.py
```

```
<paste actual captured output here>
```

Interpretation: <one line — e.g. "11/11 passed, all major code paths exercised">.

### <additional test specific to this change>

```sh
<exact command>
```

```
<captured output>
```

Interpretation: <one line on what this proves>.

## Edge cases considered

- <case>: <how handled, or why it's safe to ignore>

## What was NOT tested

Be specific about gaps.

- <thing>: <reason or planned follow-up>

## Reviewer focus

The part of this PR I'd most like a reviewer to scrutinize: <one sentence>.
