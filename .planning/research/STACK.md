# Stack Research

**Domain:** Python CLI + FastAPI web app with Google Cast integration
**Researched:** 2026-06-04 (Milestone v1.2 - Embedded Post Rendering)
**Confidence:** HIGH

---

## Milestone v1.3: LAN Casting Support Additions

The following additions extend the existing stack for LAN-accessible SSL certificates and mobile device support.

### New External Tools

| Tool | Version | Purpose | Why Recommended |
|------|---------|---------|-----------------|
| **mkcert** | v1.4.4+ | Locally-trusted SSL certificate generation | Zero-config CA creation, trusted by system stores, industry standard for local dev HTTPS. 58K+ GitHub stars. Maintained by FiloSottile. |

### New Python Dependencies

| Package | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| **psutil** | 7.2.0+ | Network interface enumeration | Enumerate all LAN IPs for certificate generation. Cross-platform, actively maintained, widely adopted. Alternative: stdlib socket trick for primary IP only. |

### No Changes Required (Already Integrated)

| Technology | Purpose | Why It Works |
|------------|---------|--------------|
| **cryptography** (existing) | Self-signed cert fallback | Keep as fallback when mkcert unavailable. |
| **FastAPI** (existing) | Web framework | No changes needed. |
| **uvicorn** (existing) | ASGI server | Already supports `ssl_keyfile` and `ssl_certfile`. |
| **Typer** (existing) | CLI framework | Use for `xbm lan-cert` command. |

---

## mkcert Integration

### Installation (External Binary)

```bash
# macOS (Homebrew)
brew install mkcert
brew install nss  # for Firefox support

# Linux (Ubuntu/Debian)
sudo apt install libnss3-tools
brew install mkcert  # or download binary

# Windows
choco install mkcert
# or
scoop install mkcert
```

### Python Integration Points

#### 1. Certificate Generation

```python
import subprocess
from pathlib import Path

def generate_lan_certs(
    lan_ip: str,
    cert_path: Path,
    key_path: Path,
    mkcert_bin: str = "mkcert"
) -> tuple[Path, Path]:
    """Generate certificates for LAN IP using mkcert.

    Args:
        lan_ip: LAN IP address (e.g., "192.168.1.100")
        cert_path: Path to save certificate file
        key_path: Path to save private key file
        mkcert_bin: Path to mkcert binary (default: "mkcert" from PATH)

    Returns:
        Tuple of (cert_path, key_path)

    Raises:
        subprocess.CalledProcessError: If mkcert fails
        FileNotFoundError: If mkcert not installed
    """
    # Generate cert with localhost, 127.0.0.1, and LAN IP
    result = subprocess.run(
        [
            mkcert_bin,
            "-cert-file", str(cert_path),
            "-key-file", str(key_path),
            "localhost",
            "127.0.0.1",
            lan_ip,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return cert_path, key_path
```

#### 2. CA Installation and CA Root Location

```python
def install_mkcert_ca(mkcert_bin: str = "mkcert") -> Path:
    """Install mkcert CA and return CA root directory.

    Args:
        mkcert_bin: Path to mkcert binary

    Returns:
        Path to CA root directory (contains rootCA.pem)

    Raises:
        subprocess.CalledProcessError: If installation fails
    """
    # Install CA (user sees prompts, so don't capture stdout)
    subprocess.run([mkcert_bin, "-install"], check=True)

    # Get CA root directory
    result = subprocess.run(
        [mkcert_bin, "-CAROOT"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def get_ca_cert_path(mkcert_bin: str = "mkcert") -> Path:
    """Get path to root CA certificate for mobile installation.

    Returns:
        Path to rootCA.pem file
    """
    result = subprocess.run(
        [mkcert_bin, "-CAROOT"],
        capture_output=True,
        text=True,
        check=True,
    )
    ca_root = Path(result.stdout.strip())
    return ca_root / "rootCA.pem"
```

#### 3. LAN IP Detection

```python
import socket
from contextlib import closing

def get_primary_lan_ip() -> str:
    """Get primary outbound IP address.

    Uses UDP socket connect trick - most reliable method.
    Doesn't actually send data, just determines routing.

    Returns:
        Primary LAN IP address, or "127.0.0.1" if detection fails.
    """
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
            # Connect to public DNS (doesn't send data)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


# Alternative: All interface IPs with psutil
def get_all_lan_ips() -> list[str]:
    """Get all non-loopback IPv4 addresses.

    Requires: pip install psutil>=7.2.0

    Returns:
        List of LAN IP addresses.
    """
    import psutil

    ips = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                if not ip.startswith("127."):  # Skip loopback
                    ips.append(ip)
    return ips
```

#### 4. Uvicorn SSL Configuration (Already Implemented)

```python
# Current implementation in src/cli/main.py:1932-1937
uvicorn.run(
    app,
    host=host,  # Change from "127.0.0.1" to "0.0.0.0" for LAN
    port=port,
    ssl_keyfile=str(key_path),
    ssl_certfile=str(cert_path),
)
```

---

## Mobile CA Installation Workflow

### iOS (iPhone/iPad)

1. **Transfer CA certificate:**
   - AirDrop `rootCA.pem` to device, OR
   - Email it to yourself, OR
   - Serve via HTTP from development machine

2. **Install profile:**
   - Open the certificate file on iOS
   - Settings > Profile Downloaded > Install

3. **Enable full trust (REQUIRED):**
   - Settings > General > About > Certificate Trust Settings
   - Toggle ON for the root CA

### Android

1. **Transfer CA certificate:**
   - Copy `rootCA.pem` to device via USB/cloud/email

2. **Install certificate:**
   - Settings > Security > Install from storage > CA certificate
   - Or: Settings > Certificate management > Install a certificate > CA certificate

3. **App trust configuration (for WebView/Browser):**
   - Android 7+ doesn't trust user CAs by default in apps
   - For Chrome/browser testing: Works with user CA for regular browsing
   - For custom apps: Requires `network_security_config.xml`

---

## CLI Command Design

```python
# Proposed new command: xbm lan-cert
@app.command("lan-cert")
def lan_cert(
    install_ca: bool = typer.Option(False, "--install-ca", "-i", help="Install mkcert CA"),
    show_ca: bool = typer.Option(False, "--show-ca", "-s", help="Show CA certificate location"),
    generate: bool = typer.Option(False, "--generate", "-g", help="Generate new LAN certificates"),
    force: bool = typer.Option(False, "--force", "-f", help="Regenerate existing certificates"),
) -> None:
    """Manage LAN-accessible SSL certificates.

    LAN-01: User can generate locally-trusted certificates.
    LAN-02: User can install CA on mobile devices.
    LAN-03: Web server binds to LAN IP with proper certificate.

    Examples:
        xbm lan-cert --install-ca         # Install mkcert CA
        xbm lan-cert --show-ca            # Show CA location for mobile install
        xbm lan-cert --generate           # Generate certs for detected LAN IP
        xbm lan-cert --generate --force   # Regenerate existing certs
    """
```

---

## Settings Changes

```python
# Add to src/config/settings.py
class Settings(BaseSettings):
    # ... existing settings ...

    # LAN configuration
    lan_enabled: bool = False  # Bind to 0.0.0.0 for LAN access
    lan_cert_path: Path = Path("data/lan.crt")
    lan_key_path: Path = Path("data/lan.key")
```

---

## File Structure Changes

```
src/web/
├── certs.py              # EXISTING: Self-signed cert generation
├── lan_certs.py          # NEW: mkcert-based LAN certificate management
└── ...

src/cli/
├── main.py               # MODIFY: Add lan-cert command
└── ...

data/
├── localhost.crt         # EXISTING: Self-signed certs (localhost only)
├── localhost.key          # EXISTING
├── lan.crt               # NEW: mkcert-generated certs (LAN IPs)
└── lan.key               # NEW
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **mkcert** | Self-signed certs (existing) | When mkcert not installed and user doesn't want to install it. Requires manual CA trust on each device. |
| **mkcert** | trustme library | Testing only. Not suitable for LAN access - certificates not trusted by system. |
| **mkcert** | openssl self-signed | When you need full control over certificate attributes. More complex, no automatic system trust. |
| **psutil** | socket stdlib only | When you only need primary outbound IP. Use UDP connect trick - zero dependencies. |
| **psutil** | netifaces2 | When you need Rust-based implementation. Drop-in replacement for netifaces. |
| **mkcert** | mkdev (newer tool) | When you need mDNS broadcasting and reverse proxy built-in. Less mature than mkcert. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **trustme library** | Certificates not trusted by system, only works in test context | mkcert for LAN, trustme only for unit tests |
| **socket.gethostbyname(socket.gethostname())** | Often returns `127.0.0.1` on many systems | UDP socket connect trick for primary IP |
| **Global mkcert CA sharing** | Security risk - rootCA-key.pem gives MITM power | Each developer runs own `mkcert -install` |
| **Self-signed certs for LAN** | Browser warnings, doesn't work with Google Cast | mkcert generates system-trusted certs |
| **Hardcoded LAN IP** | IP changes on different networks | Detect at runtime with socket or psutil |

---

## Security Considerations

1. **Never share rootCA-key.pem** - It can intercept all HTTPS traffic from your machine
2. **Only distribute rootCA.pem** - The public certificate for device trust
3. **Development only** - mkcert certificates are NOT for production
4. **Per-developer CA** - Each developer should run their own `mkcert -install`
5. **Certificate rotation** - Regenerate if CA key compromised (rare in dev)

---

## Installation

```bash
# External tool: mkcert (system-wide, not Python package)
# macOS
brew install mkcert

# Linux (after installing libnss3-tools)
brew install mkcert  # or download binary from GitHub releases

# Windows
choco install mkcert

# Python dependencies (optional, for full interface enumeration)
pip install psutil>=7.2.0
```

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| mkcert v1.4.4 | Python subprocess | Stable release, no breaking changes expected |
| psutil 7.2.2 | Python >=3.6 | Active development, backwards compatible |
| cryptography (existing) | mkcert certs | Both generate PEM format, interchangeable for uvicorn |
| uvicorn (existing) | mkcert certs | Uses ssl_keyfile/ssl_certfile parameters |

---

## Sources

### mkcert and SSL Certificates

- [mkcert GitHub Repository](https://github.com/FiloSottile/mkcert) — HIGH confidence (official)
- [mkcert README](https://github.com/FiloSottile/mkcert/blob/master/README.md) — HIGH confidence (official docs)
- [Uvicorn SSL Settings](https://github.com/Kludex/uvicorn/blob/main/uvicorn/config.py) — HIGH confidence (source code)
- [Uvicorn SSL Context Factory PR](https://github.com/Kludex/uvicorn/pull/2920) — HIGH confidence (merged April 2026)
- [Python Local HTTPS with Mkcert](https://woile.dev/blog/local-https-development-in-python-with-mkcert.html) — MEDIUM confidence (community)
- [Plain Framework MkcertManager](https://plainframework.com/docs/plain-dev/plain/dev/mkcert.py) — MEDIUM confidence (reference implementation)

### IP Detection

- [Stack Overflow: Finding Local IP Addresses](https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib) — MEDIUM confidence (community)
- [psutil PyPI](https://pypi.org/project/psutil/) — HIGH confidence (official)

### Mobile Device CA Installation

- [Android Network Security Config](https://developer.android.com/privacy-and-security/security-config) — HIGH confidence (official Android docs)
- [Apple QA1948: HTTPS and Test Servers](https://developer.apple.com/library/archive/qa/qa1948/_index.html) — HIGH confidence (official Apple docs)

### Existing Project Files

- [src/web/certs.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/certs.py) — HIGH confidence (project reference)
- [src/config/settings.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/config/settings.py) — HIGH confidence (project reference)
- [src/cli/main.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/cli/main.py) — HIGH confidence (project reference)

---

## Integration Summary

| Component | Change Type | Description |
|-----------|-------------|-------------|
| `src/web/lan_certs.py` | ADD | mkcert-based certificate generation module |
| `src/cli/main.py` | MODIFY | Add `lan-cert` command |
| `src/config/settings.py` | MODIFY | Add `lan_enabled`, `lan_cert_path`, `lan_key_path` |
| `data/lan.crt` | ADD | mkcert-generated certificate (gitignored) |
| `data/lan.key` | ADD | mkcert-generated private key (gitignored) |
| `xbm web` command | MODIFY | Add `--lan` flag to bind to 0.0.0.0 |
| External: mkcert | INSTALL | User runs `brew install mkcert` or equivalent |

---

*Stack research for: LAN Casting Support milestone*
*Researched: 2026-06-07*
*Previous research: Milestone v1.2 (Embedded Post Rendering)*

---

## Milestone v1.2: Embedded Post Rendering Additions

The following additions extend the existing stack for embedded post (retweet/quote tweet) rendering.

### X API v2 Expansions for Referenced Tweets

| Expansion | Returns | Use Case |
|-----------|---------|----------|
| `referenced_tweets.id` | Tweet object(s) | Get the original tweet for retweets/quotes |
| `referenced_tweets.id.author_id` | User object(s) | Get author of the referenced tweet |
| `referenced_tweets.id.attachments.media_keys` | Media object(s) | Get media from the referenced tweet |

### Required Tweet Fields for Embedded Content

| Field | Why Needed |
|-------|------------|
| `referenced_tweets` | Detect if post is retweet/quote and get reference ID |
| `created_at` | Original post timestamp |
| `public_metrics` | Like/retweet counts for embedded post |
| `attachments` | Media in embedded post |
| `entities` | URLs, mentions in embedded post |
| `conversation_id` | Thread context (optional) |

### Tweepy Handling for Referenced Tweets

**No new library versions required.** Tweepy 4.16+ already supports referenced tweets via expansions.

**Critical:** Access embedded tweets from `response.includes['tweets']`, NOT from `response.data`.

```python
# Current expansions (Milestone 1.1)
EXPANSIONS = "author_id,attachments.media_keys"

# Required expansions for embedded posts (Milestone v1.2)
EXPANSIONS = "author_id,attachments.media_keys,referenced_tweets.id,referenced_tweets.id.author_id"
```

**Accessing embedded tweets:**

```python
def _store_tweet(self, tweet, fetch_result):
    # Check if this is a retweet or quote
    if tweet.referenced_tweets:
        for ref in tweet.referenced_tweets:
            if ref.type in ('retweeted', 'quoted'):
                # Get the embedded tweet from includes
                embedded_tweet = fetch_result.includes.get('tweets', {}).get(ref.id)
                if embedded_tweet:
                    embedded_author = fetch_result.includes.get('users', {}).get(embedded_tweet.author_id)
                    # Store embedded content
                    self._store_embedded_post(tweet.id, embedded_tweet, embedded_author)
```

---

## Database Schema Changes

### New Table: embedded_posts

Stores the original tweet content for retweets and quote tweets.

```sql
-- Milestone v1.2: Store embedded post content
-- RT-01: Retweets show original tweet content
-- RT-02: Quote tweets show original + user's commentary
CREATE TABLE IF NOT EXISTS embedded_posts (
    x_post_id TEXT NOT NULL,              -- The bookmark post ID
    referenced_type TEXT NOT NULL,        -- 'retweeted' or 'quoted'
    referenced_id TEXT NOT NULL,          -- The original tweet ID
    referenced_created_at TIMESTAMP,       -- Original tweet date
    referenced_text TEXT,                  -- Original tweet text
    referenced_author_id TEXT,             -- Original author ID
    referenced_author_username TEXT,       -- Original author @handle
    referenced_author_display_name TEXT,  -- Original author display name
    referenced_media_urls TEXT,            -- JSON array of media URLs
    referenced_link_urls TEXT,             -- JSON array of link URLs
    referenced_public_metrics TEXT,        -- JSON: like_count, retweet_count, etc.
    FOREIGN KEY (x_post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE,
    PRIMARY KEY (x_post_id, referenced_type)
);

-- Index for lookup when rendering
CREATE INDEX IF NOT EXISTS idx_embedded_posts_post ON embedded_posts(x_post_id);
```

### Migration to Existing posts Table

No changes to existing posts table schema. The current `text` column will contain:
- **Original posts:** The full post text
- **Retweets:** "RT @username: [original text]" (truncated) OR just "RT @username: ..."
- **Quote tweets:** The user's commentary text

The `embedded_posts` table stores the full original content separately.

---

## API Client Changes

### XClient Expansions Update

```python
# src/api/x_client.py - Updated constants
class XClient:
    # Added: referenced_tweets expansions for embedded posts
    EXPANSIONS = "author_id,attachments.media_keys,referenced_tweets.id,referenced_tweets.id.author_id"
    TWEET_FIELDS = "created_at,public_metrics,attachments,entities,referenced_tweets"
    USER_FIELDS = "username,name,profile_image_url"
    MEDIA_FIELDS = "url,preview_image_url,height,width,alt_text"
```

### BookmarkFetchResult Update

```python
@dataclass
class BookmarkFetchResult:
    tweets: list[Any] = field(default_factory=list)
    users: dict[str, Any] = field(default_factory=dict)
    media: dict[str, Any] = field(default_factory=dict)
    referenced_tweets: dict[str, Any] = field(default_factory=dict)  # NEW
    referenced_users: dict[str, Any] = field(default_factory=dict)   # NEW
    next_token: Optional[str] = None
    result_count: int = 0
    rate_limit: RateLimitInfo = field(default_factory=RateLimitInfo)
```

### Processing Logic Update

```python
# src/services/sync.py - Updated _store_tweet method
def _store_tweet(self, tweet: Any, fetch_result: BookmarkFetchResult) -> None:
    """Store a single tweet with author, media, and embedded content."""
    # ... existing author/media extraction ...

    # NEW: Extract embedded posts (retweets/quotes)
    if hasattr(tweet, 'referenced_tweets') and tweet.referenced_tweets:
        for ref in tweet.referenced_tweets:
            if ref.type in ('retweeted', 'quoted'):
                embedded = fetch_result.referenced_tweets.get(ref.id)
                if embedded:
                    embedded_author = fetch_result.referenced_users.get(embedded.author_id)
                    self._store_embedded_post(
                        bookmark_id=str(tweet.id),
                        ref_type=ref.type,
                        ref_tweet=embedded,
                        ref_author=embedded_author
                    )

    # Store main post (existing logic)
    post = {
        'x_post_id': str(tweet.id),
        'created_at': tweet.created_at.isoformat(),
        'text': tweet.text,
        'author_id': str(tweet.author_id),
        'author_username': author.username if author else '',
        'author_display_name': author.name if author else '',
        'media_urls': [...],
        'link_urls': [...],
        'bookmarked_at': None,
    }
    self._posts_repo.upsert_post(post)
```

---

## Repository Changes

### New Repository: EmbeddedPostsRepository

```python
# src/repositories/embedded_posts.py

class EmbeddedPostsRepository:
    """Repository for embedded_posts table operations."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert_embedded(self, embedded: dict[str, Any]) -> None:
        """Insert or update embedded post content."""
        self._conn.execute(
            """
            INSERT INTO embedded_posts (
                x_post_id, referenced_type, referenced_id, referenced_created_at,
                referenced_text, referenced_author_id, referenced_author_username,
                referenced_author_display_name, referenced_media_urls,
                referenced_link_urls, referenced_public_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(x_post_id, referenced_type) DO UPDATE SET
                referenced_created_at = excluded.referenced_created_at,
                referenced_text = excluded.referenced_text,
                referenced_author_id = excluded.referenced_author_id,
                referenced_author_username = excluded.referenced_author_username,
                referenced_author_display_name = excluded.referenced_author_display_name,
                referenced_media_urls = excluded.referenced_media_urls,
                referenced_link_urls = excluded.referenced_link_urls,
                referenced_public_metrics = excluded.referenced_public_metrics
            """,
            (
                embedded['x_post_id'],
                embedded['referenced_type'],
                embedded['referenced_id'],
                embedded['referenced_created_at'],
                embedded['referenced_text'],
                embedded['referenced_author_id'],
                embedded['referenced_author_username'],
                embedded['referenced_author_display_name'],
                json.dumps(embedded.get('referenced_media_urls', [])),
                json.dumps(embedded.get('referenced_link_urls', [])),
                json.dumps(embedded.get('referenced_public_metrics', {})),
            )
        )
        self._conn.commit()

    def get_embedded(self, x_post_id: str) -> Optional[dict[str, Any]]:
        """Get embedded post data for a bookmark."""
        row = self._conn.execute(
            "SELECT * FROM embedded_posts WHERE x_post_id = ?",
            (x_post_id,)
        ).fetchone()
        return self._row_to_dict(row) if row else None
```

---

## Template Changes

### Updated Post Rendering (browse.html)

```html
{% for post in posts %}
<div class="bg-white rounded-lg shadow p-4">
    {% if post.embedded %}
    <!-- Retweet or Quote tweet -->
    <div class="{% if post.referenced_type == 'quoted' %}border-l-4 border-gray-200 pl-3 mb-3{% endif %}">
        {% if post.referenced_type == 'quoted' %}
        <!-- User's commentary -->
        <p class="text-gray-800 mb-2">{{ post.text }}</p>
        <p class="text-xs text-gray-500 mb-2">Quoted @{{ post.embedded.author_username }}:</p>
        {% else %}
        <!-- Retweet -->
        <p class="text-xs text-gray-500 mb-1">
            <span class="icon-retweet"></span> Retweeted
        </p>
        {% endif %}

        <!-- Embedded original post -->
        <div class="bg-gray-50 rounded p-3">
            <div class="flex items-center mb-2">
                <span class="font-semibold">@{{ post.embedded.author_username }}</span>
                <span class="text-xs text-gray-500 ml-2">{{ post.embedded.created_at[:10] }}</span>
            </div>
            <p class="text-gray-800">{{ post.embedded.text }}</p>
            {% if post.embedded.media_urls %}
            <div class="grid grid-cols-2 gap-2 mt-2">
                {% for media_url in post.embedded.media_urls %}
                <img src="{{ media_url }}" class="rounded max-h-48 object-cover" />
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>
    {% else %}
    <!-- Regular post -->
    <p class="text-gray-800">{{ post.text }}</p>
    {% endif %}

    <!-- Author and actions -->
    <div class="flex items-center justify-between mt-3">
        <span class="text-sm text-gray-500">@{{ post.author_username }}</span>
        <a href="https://x.com/{{ post.author_username }}/status/{{ post.x_post_id }}"
           target="_blank" class="text-blue-500 hover:text-blue-700 text-sm">
            View on X
        </a>
    </div>
</div>
{% endfor %}
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Tweepy < 4.14** | Missing full referenced_tweets support in includes | Tweepy 4.16+ |
| **Fetching embedded tweets separately** | Wastes API calls, data already in response | Extract from `includes` |
| **Storing embedded content in posts.text** | Loses author info, can't format properly | Separate `embedded_posts` table |
| **Only storing referenced_tweets.id** | Need full tweet content for rendering | Store all embedded fields |
| **Ignoring referenced_tweets field** | Shows truncated "RT @user: ..." text | Parse and display full original |

---

## Cast Receiver Considerations

Embedded posts require additional rendering logic in the Cast receiver template:

```html
<!-- src/web/templates/receiver.html - Post card -->
<div class="post-card">
    {% if post.embedded %}
    <div class="embedded-post">
        {% if post.referenced_type == 'quoted' %}
        <p class="commentary">{{ post.text }}</p>
        <blockquote class="quoted-tweet">
            <strong>@{{ post.embedded.author_username }}</strong>
            <p>{{ post.embedded.text }}</p>
        </blockquote>
        {% else %}
        <!-- Retweet: show original with retweet indicator -->
        <div class="retweet-indicator">Retweeted</div>
        <div class="original-post">
            <strong>@{{ post.embedded.author_username }}</strong>
            <p>{{ post.embedded.text }}</p>
        </div>
        {% endif %}
    </div>
    {% else %}
    <p>{{ post.text }}</p>
    {% endif %}
</div>
```

---

## Installation

No new dependencies required. The existing Tweepy 4.16+ installation supports referenced_tweets expansions.

---

## Version Compatibility

No changes. All existing versions support this feature:
- Python 3.10+ (existing)
- Tweepy 4.16+ (existing, supports referenced_tweets)
- SQLite 3.x (existing)

---

## Sources

### X API v2 Referenced Tweets

- [X API Expansions Documentation](https://docs.x.com/x-api/fundamentals/expansions) — HIGH confidence (official)
- [X API Tweet Fields](https://docs.x.com/x-api/fundamentals/fields) — HIGH confidence (official)
- [Tweepy Expansions and Fields](https://docs.tweepy.org/en/stable/expansions_and_fields.html) — HIGH confidence (official)
- [Tweepy Models Documentation](https://docs.tweepy.org/en/stable/v2_models.html) — HIGH confidence (official)

### Tweepy Referenced Tweets Handling

- [Tweepy GitHub tweet.py](https://github.com/tweepy/tweepy/blob/master/tweepy/tweet.py) — HIGH confidence (source code)
- [Tweepy Discussion #1673: Extended tweets and expansions](https://github.com/tweepy/tweepy/discussions/1673) — HIGH confidence (community verified)

### Existing Project Files

- [src/api/x_client.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/api/x_client.py) — HIGH confidence (project reference)
- [src/services/sync.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/services/sync.py) — HIGH confidence (project reference)
- [src/db/schema.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/db/schema.py) — HIGH confidence (project reference)
- [src/repositories/posts.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/repositories/posts.py) — HIGH confidence (project reference)
- [src/web/templates/browse.html](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/templates/browse.html) — HIGH confidence (project reference)

---

## Integration Summary (v1.2)

| Component | Change Type | Description |
|-----------|-------------|-------------|
| `XClient.EXPANSIONS` | MODIFY | Add `referenced_tweets.id,referenced_tweets.id.author_id` |
| `XClient.TWEET_FIELDS` | MODIFY | Add `referenced_tweets` field |
| `BookmarkFetchResult` | MODIFY | Add `referenced_tweets` and `referenced_users` dicts |
| `SyncService._store_tweet()` | MODIFY | Extract and store embedded content |
| `schema.py` | ADD | `embedded_posts` table and migration |
| `EmbeddedPostsRepository` | ADD | New repository for embedded posts |
| `browse.html` | MODIFY | Render embedded posts with nested display |
| `receiver.html` | MODIFY | Cast receiver template for embedded posts |
| `PostsRepository.get_by_id()` | MODIFY | Join with embedded_posts table |

---

*Stack research for: Embedded post rendering (retweets, quote tweets)*
*Researched: 2026-06-04*
*Previous research: Milestone 1.1 (Web App + Cast)*