# Phase 1: Foundation and Authentication - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 01-foundation-and-authentication
**Areas discussed:** Token storage, Database location, Schema, OAuth scopes

---

## Token Storage

| Option | Description | Selected |
|--------|-------------|----------|
| data/tokens.json | Simple JSON file in project directory. Easy to inspect/debug. Consistent with x-api pattern. | |
| ~/.config/x-bookmarks/tokens.json | OS-appropriate config directory. More standard for CLI tools. | |
| System keyring | Uses OS keychain/keyring. Most secure. Requires extra dependency. | |

**User's choice:** Default to data/tokens.json with config option to override
**Notes:** Sensible default with configurability for users who need it.

---

## Database Location

| Option | Description | Selected |
|--------|-------------|----------|
| data/bookmarks.db | Simple, consistent with token storage. Easy to find/backup. | ✓ |
| ~/.local/share/x-bookmarks/bookmarks.db | OS-appropriate data directory. More standard for CLI tools. | |
| Configurable via settings | Maximum flexibility. Requires config setup. | |

**User's choice:** data/bookmarks.db
**Notes:** Co-located with tokens for simplicity.

---

## Database Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Users + tokens only | Minimal Phase 1 schema. Posts table added in Phase 2. Clean phase boundaries. | ✓ |
| Include posts table now | Complete schema from start. Makes Phase 2 slightly simpler. | |

**User's choice:** Users + tokens only
**Notes:** Clean separation of concerns. Schema grows with functionality.

---

## OAuth Scopes

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal for bookmarks | tweet.read, users.read, bookmark.read, offline.access. No unnecessary permissions. | ✓ |
| Match x-api scopes | Use x-api scopes as-is (includes list permissions). Add bookmark.read later. | |

**User's choice:** Minimal for bookmarks
**Notes:** Purpose-specific permissions only. No list permissions needed.

---

## Claude's Discretion

- Token refresh logic — standard OAuth 2.0 flow, implement with tweepy
- Error messages for auth failures — follow x-auth.py patterns
- Database migration approach — simple initialization script, migrations deferred

## Deferred Ideas

None — discussion stayed within phase scope.