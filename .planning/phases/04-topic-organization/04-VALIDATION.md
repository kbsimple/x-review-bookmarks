---
phase: 4
slug: topic-organization
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-24
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pyproject.toml (tool.pytest) |
| **Quick run command** | `pytest tests/ -x -v` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -v`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | ORG-01 | T-4-01 | Parameterized queries for tag ops | unit | `pytest tests/test_tags_repository.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | ORG-01 | T-4-01 | SQL injection prevention | unit | `pytest tests/test_tags_repository.py -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | ORG-02 | T-4-01 | Parameterized queries for topic ops | unit | `pytest tests/test_topics_repository.py -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | ORG-02 | T-4-01 | Input validation on topic names | unit | `pytest tests/test_topics_repository.py -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | ORG-03 | N/A | N/A | unit | `pytest tests/test_embedding_service.py -x` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 2 | ORG-03 | N/A | N/A | unit | `pytest tests/test_clustering_service.py -x` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 2 | ORG-03 | N/A | N/A | unit | `pytest tests/test_topic_suggester.py -x` | ❌ W0 | ⬜ pending |
| 04-04-02 | 04 | 2 | ORG-04 | N/A | N/A | unit | `pytest tests/test_topic_suggester.py -x` | ❌ W0 | ⬜ pending |
| 04-05-01 | 05 | 3 | CLI-04 | T-4-01 | Input validation on CLI args | integration | `pytest tests/test_cli.py::test_tag_command -x` | ❌ W0 | ⬜ pending |
| 04-05-02 | 05 | 3 | CLI-04 | T-4-01 | Input validation on CLI args | integration | `pytest tests/test_cli.py::test_topic_command -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tags_repository.py` — stubs for ORG-01 tag CRUD
- [ ] `tests/test_topics_repository.py` — stubs for ORG-02 topic management, ORG-04 approval
- [ ] `tests/test_embedding_service.py` — stubs for ORG-03 embedding generation
- [ ] `tests/test_clustering_service.py` — stubs for ORG-03 clustering logic
- [ ] `tests/test_topic_suggester.py` — stubs for ORG-03, ORG-04 suggestion workflow
- [ ] Update `tests/conftest.py` — add fixtures for tags, topics, embeddings tables
- [ ] Install dependencies: `pip install sentence-transformers scikit-learn`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Model download from HuggingFace | ORG-03 | Network dependency, one-time setup | Verify `sentence-transformers` can download `all-MiniLM-L6-v2` model |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending