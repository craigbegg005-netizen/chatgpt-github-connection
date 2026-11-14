# Disk pressure: 90% full, and the two things to know before clearing it

**Date:** 2026-11-14 04:0x UTC · **Volume:** `/dev/vda`, 9.8 GB · **Trigger:** the harness warned at 90%

## What was consuming it

| Path | Size | What it is |
|---|---|---|
| `/root/.bun/install/cache` | 949 MB | bun's package cache |
| `/root/workspace/.bun/install/cache` | 949 MB | **a second copy** — different inode, not a symlink |
| `/root/workspace/.npm/_npx` | 233 MB | npx's downloaded packages |
| `/root/workspace/.npm/_cacache` | 93 MB | npm's cache |
| `/root/workspace/.letta/logs/remote` | 63 MB | remote-session logs |

**Note the two bun caches.** `du` reports them separately and `stat` confirms different inodes, so they are
genuinely 1.9 GB between them rather than one directory counted twice. That is the single biggest win and
the least obvious.

## What I cleared, and the result

Cleared the five paths above — all regenerable by design. **90% → 68%**, 1003 MB free → **3.3 GB free**.

Verified afterwards that nothing of value went with them: the repo is clean at its head, the venv is
present, the memory repo is clean and pushed, and the reserve file is untouched.

## 🔴 The thing a future session must NOT delete

`/root/workspace/.letta/state/disk-reserve` is a **512 MB file** that the harness maintains deliberately.
It is not junk and it is not a stale artifact — **it is the safety margin.** Deleting it to "free space"
removes the buffer that keeps writes from failing, which is the opposite of the intent.

**The rule: free space from caches, never from the reserve.** If `disk-reserve` is the largest thing left,
the honest answer is that the volume is genuinely full and something else has to give.

## This recurs

Caches regrow with use. The five paths above are the ones to check first, and the command is:

```bash
du -xh --max-depth=2 /root 2>/dev/null | sort -h | tail -20
```
