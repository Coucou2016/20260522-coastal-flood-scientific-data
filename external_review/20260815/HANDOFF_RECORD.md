# External ChatGPT handoff record

## Source baseline

- Source control: `NOT_A_GIT_REPOSITORY` (the workspace has no `.git` directory).
- Review package: `chatgpt_review_package_v3.zip`
- Package size: `66,446,661` bytes
- Package SHA-256: `aec9039ad7eec1e337835b0aa6490ffc90a93db4c35597c3cc9b775bc2928924`
- Packaged files: `315`
- Staged uncompressed bytes: `80,731,072`
- Credential scan: `0` forbidden filenames; `0` credential-pattern hits.
- Archive validation: CRC passed; `0` duplicate members; `0` unsafe paths; `0` symlinks.
- Excluded: `.git`, `.env*`, credentials, browser state, caches/bytecode, `data/raw`, upstream raster/NetCDF products, local DTM rasters, and Base64 standalone HTML/Markdown.
- Note: v1 was rejected because it contained Python bytecode caches and derived Base64 Markdown; v2 failed a final CRC check. Only the rebuilt and independently verified v3 package is authorized for external review.

## External conversations

### Task A: algorithm, statistics, and reproducibility

- Conversation: https://chatgpt.com/c/6a8087b7-824c-83ea-934d-ec41a081aafe
- Task specification: `TASK_A_ALGORITHM_STATISTICS_REPRODUCIBILITY.md`
- Requested delivery directory: `external_review/20260815/chatgpt_A_delivery/`
- Status at handoff: task conversation created; the corrected v3 package is awaiting connector re-authorization before delivery. No external review result has been accepted.

### Task B: manuscript, figures, report, and submission coherence

- Conversation: https://chatgpt.com/c/6a8088b4-f630-83ea-9b1c-117163811b50
- Task specification: `TASK_B_MANUSCRIPT_FIGURES_REPORT.md`
- Requested delivery directory: `external_review/20260815/chatgpt_B_delivery/`
- Status at handoff: task conversation created; the corrected v3 package is awaiting connector re-authorization before delivery. No external review result has been accepted.

## Transport

The ChatGPT web file chooser did not emit a usable chooser event in the Codex in-app browser. An OAuth-protected ChatGPT2LocalBridge connector was prepared as the fallback transport, but its authorization expired before the corrected v3 package could be delivered. The v3 archive remains the only authorized review package; delivery and external review are pending user re-authorization. The connector policy allows this project root and denies common secret-file patterns.
