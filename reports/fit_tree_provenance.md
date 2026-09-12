# The tree every current-code arm ran on is a copy with no recorded version

**2026-09-12.** Found while checking, for an unrelated reason, whether upstream had moved past our
pin. `scripts/identify_fit_tree_provenance.py`.

## What went wrong

`villa-spiral-current/` is the tree that fitted and rendered every current-code arm. It is a **copy**,
not a checkout: no `.git`, no build log recording what was copied, nothing in this repo pinning it.

Worse, it *looks* like a checkout. `git -C villa-spiral-current rev-parse HEAD` returns a commit —
`50969a5`, "Update marketing-engine submodule" — because the directory sits inside the enclosing
workspace repo and git walks up. **That is an unrelated commit from an unrelated project**, and it is
the kind of answer that gets believed because a command returned it.

`reports/decoupling_does_not_cleanly_reproduce.md` accordingly stated a version for the renders that
was not the one used.

## What it actually is

Recovered by content — comparing every tracked file against candidate commits in the `villa/`
submodule:

| subtree | matches | files |
|---|---|---:|
| `spiral-fitting` | **`be09a8503`** | 100% exact |
| `lasagna` | **`d8c5f488a`** | 252/252 exact |
| `vesuvius` | **`d8c5f488a`** | 647/647 exact |

**The tree is not one ref.** The fit runs `be09a8503`; the flatten and the `tifxyz` reader the render
imports run `d8c5f488a`. Any provenance statement has to name the subtrees separately, and the
previous single-commit phrasing could not be right for all of them.

## The validity question this raises, and why it comes out clean

If the tree had changed between the baseline arms and the ablated ones, the comparison would be
confounded — different code, not just different anchors.

It did not. Every file was written **2026-09-07 10:00** in one copy and nothing has been modified
since. The arms ran between **09-07 21:25** and **09-12 02:52**, all after it.

So all six current-code arms — `curbase_s1..s3` and `nosamecur_s1..s3` — ran on an identical tree,
and the `anchor10cov` pilot is running on the same one. **This is a stronger validity argument than
the one it replaces**, which had to reason that a version delta between arms was inert.

## What is fixed

* `scripts/identify_fit_tree_provenance.py` recovers provenance by content for any such copy, and
  reports **per subtree**, refusing to summarise a mixed tree as one commit.
* The verdict report's validity section now states the real provenance.
* `repro/spiral_fits/` (vendored 2026-09-12) records which driver used which tree.

## The general lesson

**A command returning a commit hash is not evidence that it described the thing you asked about.**
Inside nested repositories, `git -C <dir>` answers about the nearest enclosing repository, not about
`<dir>`. The existing rule — run `git rev-parse --show-toplevel` in the same command before any git
*write* — turns out to be just as necessary before believing a git *read*.
