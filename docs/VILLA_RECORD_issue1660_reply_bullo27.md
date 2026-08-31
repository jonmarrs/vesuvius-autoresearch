# RECORD, POSTED 2026-08-31 (reply on villa#1660)

https://github.com/ScrollPrize/villa/issues/1660#issuecomment-5483311900

Reply to @Bullo27, who cross-referenced #1588 (open, container images stale) and PR #1619 (closed
unmerged to stay inside villa's three-open-PR limit). Their point was correct: part 2 of #1660
duplicates an already-tracked condition, which I would have caught by searching first.

A record of what was said, not a draft. No nudges: await any reply.

---

Confirmed, and thanks for the cross-reference. I should have searched before filing. Part 2 here is downstream of #1588 and adds nothing to it.

One measured data point in support of the "refreshed image resolves it" reading, in case it is useful on #1588 or #1619: I rebuilt `vc_tifxyz2obj` from current main against `builder-ubuntu-24.04`, and the result accepts `--keep`. So the flag gap is purely the 2026-05-13 build date, not anything source side. Building just that one CMake target pulls in `libvc_core` and skips the Qt UI, flatboi, python bindings and tests, so it configures in seconds and compiles in a few minutes on four cores.

One correction to an implication in my own issue, since it would otherwise overstate what the image refresh buys. A current `vc_tifxyz2obj` was not sufficient to render here. With `--keep` working and the coarse/fine pair produced as intended (12,521 verts against 200,196), flatboi still did not converge on a clean mesh: manifold, one connected component, zero degenerate faces, over an hour at ten iterations. What actually worked was the default path, no `--strips`, where the full scroll concat is flattened by `lasagna/fit.py` instead. That converges in about 95 seconds on one GPU. So for anyone else following this: the `--strips` flatboi route is where the container symptoms bite, and it is not the route `run_single.py` takes.

Part 1, the mesh and volume frame mismatch that renders a black strip while exiting 0, is independent of #1588 and unaffected by any of the above.
