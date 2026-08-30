# RECORD, POSTED 2026-08-30

Posted as ScrollPrize/villa#1654: https://github.com/ScrollPrize/villa/issues/1654

A record of what was said, not a draft. Corrections go to the thread as a new comment, never as a
silent edit here. No nudges: await a reply.

---

`instance-labels-harmonized` mixes uint8 and uint16 volumes, which silently splits the set into two intensity scales.

The cubes under `volumetric-instance-labels/instance-labels-harmonized/` do not share a dtype:

```
00000_02408_04560   uint16   0..65535
00064_02664_04304   uint8    8..255
00768_02152_03536   uint16   0..65535
00768_02408_03536   uint16   0..65535
01024_02152_04048   uint16   0..65535
01744_02000_04048   uint8    8..255
```

Checked on 12 of the 80 harmonized cubes; both dtypes appear.

Why it is worth a note: the README says the harmonization is of instance IDs, and it is easy to read "harmonized" as meaning the cubes are otherwise comparable. Any per-cube intensity statistic computed without normalising first lands in two clusters about 250x apart for reasons unrelated to the scan. Measuring intensity standard deviation across those 12 cubes gives 42.7 to 12901.7, entirely from the dtype split rather than from anything in the data.

That would also affect a model trained on the raw volumes without per-cube normalisation, though I have not tested that.

Two things that would remove the trap, either one being enough: a line in `README.txt` saying the volumes are a mix of `uint8` and `uint16`, or republishing to a single dtype.

Happy to send the list of which of the 80 cubes are which if that is useful.
