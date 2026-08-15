# Extracting `placement_check` into its own repository

`tools/placement_check/` is self-contained: numpy only, no import from this repo, its own
LICENSE, `.gitignore`, CI and `pyproject.toml`. Verified by copying it outside the repo,
`git init`-ing it fresh, installing from the package definition and running the suite.

It lives here for now because a tool meant for other people should not require cloning a
research repo, and the split is Jon's to make (it creates something under his account).

## Recommended: preserve history with a subtree split

```bash
cd /path/to/vesuvius-autoresearch
git subtree split --prefix=tools/placement_check -b placement-check-split

# create the empty repo on GitHub first, then:
cd /tmp && git clone <new-repo-url> placement-check && cd placement-check
git pull /path/to/vesuvius-autoresearch placement-check-split
git push origin main
```

This keeps the commits that touch those files, so authorship and the reason each guard
exists survive the move. A fresh `git init` also works and is simpler, but it throws that
away, and the guards in this module are only obviously worth having if you can see what
they were added in response to.

## After the split

1. Delete `tools/placement_check/` here and replace it with a one-line pointer, so there is
   exactly one copy. Two copies of a thing that must not drift is the failure this whole
   month was about.
2. Decide whether `repro/sota_data/register.py::placement_peak` should depend on the
   package instead of keeping its own implementation. It currently duplicates the logic.
   Either is defensible, but if both stay, add a sync test like
   `tests/test_metrics_contract_sync.py`, which exists because exactly this kind of
   duplicate silently drifted before.
3. Update the reference in
   `reports/detector/registration_offset_2026-08-07.md` and the tool's README provenance
   link to point at the new location.

## Not done deliberately

- **No PyPI publish.** That is a name grab and an ongoing maintenance promise; worth doing
  only if someone actually uses it.
- **No repo created.** Outward-facing and Jon's call.
