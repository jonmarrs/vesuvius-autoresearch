# October 2026 Progress Prize — second filed response

**Submitted by the owner; verified directly against the Google Forms email
receipt.** The receipt is dated **October 31, 2026 at 1:58:08 p.m. Pacific**
(**20:58:08 UTC**), before the 11:59 p.m. Pacific deadline. This is the receipt's
date, not a separately recorded form-submission timestamp. It adds Villa
**#2141** and **#2259** to the
[engineering entry filed on October 29](PRIZE_FILING_2026-10_SUBMITTED.md).
Both merged on October 30 (2:04 and 2:37 p.m. Pacific), after that entry was
filed, so it does not credit them.

Villa's prize page asks for small fixes made in one month to be bundled into a
single submission. The first response's receipt has no edit link, so these two
went in as a second response on the same October form. Its first sentence
names the first entry. The form was accepting responses when checked at 1:19
p.m. Pacific.

The URL field and the **335-word** contribution below match the email's HTML
answer fields after CRLF-to-LF normalization and trimming surrounding whitespace;
paragraph breaks are preserved. The identity fields, individual classification
and terms agreement were also verified against the intended answers.

The initial record relied on the owner's pasted response copy and report that
submission was complete by 1:59 p.m. Pacific. Direct mailbox review now confirms
the original receipt and its timestamp. The
[redacted record](../reports/evidence/october_prize_second_submission_2026-10-31.json)
keeps those times, public answer fields and content hashes. No local raw email
archive was created for this verification. Email address, name, team wording,
Discord name, message IDs and raw headers are excluded from the public record.

The [separate research entry](PRIZE_FILING_2026-10_RESEARCH_FORM_ANSWERS.md)
remains unsubmitted in this workflow.

## URL field as received

```text
https://github.com/ScrollPrize/villa/pull/2141
https://github.com/ScrollPrize/villa/pull/2259
https://github.com/jonmarrs/vesuvius-autoresearch
```

## Contribution as received

```text
This adds to my October engineering entry of October 29 (Villa #2022, #2044 and #2155). These two fixes merged on October 30, after that entry was filed, and are not credited in it.

(1) Which scroll data. PHerc. Paris 4 / Scroll 1: Villa's published spiral-fitting track stores (for example tracks/m7_ds2_z3000_18000_surf.dbm), and the command-line tools of Villa's VC3D release (VC3D-e2254eb-2026-10-22) that render scroll surfaces.

(2) How this helps people read the scrolls.

- #2141 (merged 2026-10-30): open Villa's published SQLite track stores read-only on every supported Python version. The published PHerc. Paris 4 stores are WAL databases; on Python 3.10 and 3.11 the reader failed to open one from a read-only directory ("attempt to write a readonly database") and left -wal/-shm files beside it in a writable one. With the fix a checkpointed store opens from a read-only directory without creating sidecars, and committed WAL pages stay visible.
- #2259 (merged 2026-10-30): document how to run the release's command-line tools on headless Linux. On Debian 13 with no display, calling the extracted vc_render_tifxyz directly segfaulted with no output; launching it through the bundled AppRun printed its help and exited 0. The docs now give a Debian/Ubuntu package command for the host libraries, the extraction and AppRun commands, and why the wrapper is required.

(3) What this enables. Spiral fitting can read the published track stores from read-only or shared dataset directories, and users on headless servers can launch the release's render tools by following the docs, as issue #2153 needed.

(4) Evidence. #2141's six reader tests cover sidecar-free reads, a read-only directory, recognized SQLite stores, committed WAL pages and a file symlink; an earlier version was validated on Windows by @vincentl065, the author of the original fallback. A store with an un-checkpointed WAL still needs SQLite's normal locking and may still fail in a read-only directory. #2259 compares the two launch paths on the same release (SHA-256 46365113…); it checked tool startup, not a render. The real-data render that needed it is reported in #2153.
```
