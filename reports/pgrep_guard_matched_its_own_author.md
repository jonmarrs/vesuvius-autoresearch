# A process guard that matched the shell which wrote it

**2026-09-12.** Cost: one wedged handoff, caught before it cost compute. Third variant of the same
trap in a single session, and the only one that was not obvious once seen.

## What happened

`await_arm2_then_chain.sh` existed to hand off from a standalone fit to the study chain. Its condition:

```bash
if [ "$n" -ge 120 ] && ! pgrep -f "[f]it_spiral.py" >/dev/null 2>&1; then
```

The `[f]` bracket trick is the standard defence against `pgrep -f` matching its own invocation, and it
works. It did not help, because the process it matched was not the `pgrep`.

**It matched the shell that created the script.** The waiter was written with a heredoc inside a tool
call, so that shell's `argv` contained the entire script text — including the literal string
`fit_spiral.py`, three times, in the comments explaining the race. That shell stayed alive. So the
guard saw a "running fit" forever and the waiter slept through two polls after the real fit had exited,
logging that a fit was still running while no interpreter existed.

## Why it was invisible

* `ps | grep fit_spiral` showed a hit, so "a fit is running" *looked* confirmed.
* The hit's command line is ~2 KB of heredoc, so in truncated output it reads as a plausible process.
* The condition that failed and the condition that was reported were not the same thing: the log said
  `n=$n or fit still running` — an *or*, which never says which side failed. **A diagnostic that
  cannot distinguish its own branches is not a diagnostic.**

## The fix that matters

**Do not identify a process by text that also appears in your own source.** Match the thing itself:
scan `/proc/*/comm` for the *interpreter* and check `cmdline` only for processes that are actually
Python, which excludes every shell whose argv merely quotes the script name:

```bash
for p in /proc/[0-9]*; do
  case "$(cat "$p/comm" 2>/dev/null)" in
    *python*) tr '\0' ' ' < "$p/cmdline" | grep -q "fit_spiral.py" && echo "running" ;;
  esac
done
```

**And write long-lived scripts to disk with a file write, not a shell heredoc**, so the text never
enters any process's argv in the first place.

In this instance the waiter was simply deleted: arm 2's fit had verifiably finished (120 meshes, gate
passed), so the chain was launched directly. The guard was solving a problem that no longer existed.

## The three variants seen today

1. `pgrep -f "pytest tests/"` matched the shell running the `pgrep` → false "still running".
2. `pkill -9 -f fit_spiral.py` matched and killed **my own shell** mid-command.
3. This one: a guard inside a script matched the shell that *authored* the script.

The common root is that a process's command line is data an unrelated process can contain. `[f]oo`
only defends against the first. The general rule is **match on the executable, not on a string**.
