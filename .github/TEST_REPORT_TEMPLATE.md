# Test Report — <short title>

Copy this template into your PR description (or fill it in a separate file
linked from the PR). Replace each placeholder with the actual thing. Keep
sections short. The point is concrete evidence, not prose.

## What changed
One sentence describing the change.

## Why
One sentence on the problem or motivation.

## Verification

For each test you ran: the exact command, the captured output (or a trimmed
excerpt), and one line interpreting it.

### <test name>

Command:

```sh
<exact command, copy-pasted>
```

Output:

```
<actual captured stdout/stderr, trimmed to the relevant lines>
```

Interpretation: <one line — what this proves about the change>.

### <next test>

(repeat as needed — at minimum, one test per behavior the change touches)

## Edge cases considered

- <case>: <how handled, or why it's safe to ignore>

## What was NOT tested

Be specific about gaps. This is the section that signals honest evaluation
to the reviewer.

- <thing>: <reason or planned follow-up>

## Reviewer focus

The change I'd most like a reviewer to scrutinize: <one sentence>.
