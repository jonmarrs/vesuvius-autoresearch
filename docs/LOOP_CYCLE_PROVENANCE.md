# Code and configuration identities in loop records

`cycles.jsonl` retains the settings and code identity captured when the loop
launches each cycle. This supports comparison of unchanged-training controls
and tweaks against the same starting conditions.

Previously, the code epoch combined HEAD with Git status lines. Editing an
already modified file twice left those lines unchanged. The live replicate
rule also accepted observations from different baseline configs when the
checkpoint and validation sample matched. Both could mix different conditions.

| Field | Meaning |
| --- | --- |
| `commit`, `code_changes` | HEAD and Git status for the existing `LOOP_CODE_PATHS`. |
| `code_sha256` | SHA-256 of that identity, the binary Git diff against HEAD, including tracked submodule changes, and the names and contents of untracked runtime files outside submodules. |
| `baseline_config` | The baseline settings normalized to this cycle's budget and `pinned=False`, before applying its tweak. |
| `baseline_config_sha256` | SHA-256 of that captured dictionary serialized with sorted keys and compact JSON separators. |
| `config` | The proposed settings written to `config_temp.json` for this cycle. A control equals its normalized baseline. |

The code digest uses raw bytes so text decoding cannot erase differences.
Git failures, unreadable files, or a changed HEAD/status during capture produce
no code identity. Untracked files inside Villa remain excluded, as in the
existing code-state policy; that checkout contains untracked model assets.
The digest identifies the Git-visible state at launch. It does not archive
dirty source files, freeze code throughout training, or identify every installed
package. Retain the relevant source diffs with a research readout.

The live replicate rule requires recorded code and config identities. It
checks that the baseline dictionary matches its hash and pools only cycles
with the same baseline hash, checkpoint bytes, budget, validation protocol,
input fingerprint and complete patch counts. Code epochs include the content
digest, so different edits with identical Git status lines remain separate.
The registered scoring function, thresholds and published readouts are unchanged.

Old journal rows remain preserved. They cannot support the live rule when
these identities are missing; the rule needs new eligible replicates and
comparators after rollout. Do not backfill guessed identities to make old
observations count. The existing single-cycle F1 promotion path remains active.

Roll out the repository change on the research host at a cycle boundary using
the existing stop/pull/start workflow. Keep the journal and promotion backups.
This repository change does not itself restart the host or collect a GPU result.

For a confirmatory control comparison, register a new window and analysis
before collecting its measurements. Also use the recorded warm-start details
to distinguish continued training from fresh or partial initialization. These
recording changes do not establish a new quality or cross-scroll result.
