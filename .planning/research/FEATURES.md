# Feature Research: LAN SSL Certificate Setup

**Domain:** Local development HTTPS / LAN-accessible web applications
**Researched:** 2026-06-07
**Confidence:** HIGH (mkcert official docs, Plain Framework implementation, multiple community sources)

## Context

This is a **subsequent milestone** (v1.3) adding LAN-accessible HTTPS to an existing app. The app already provides:

- OAuth 2.0 PKCE authentication with X API
- SQLite storage with posts, tags, topics, review state
- FastAPI web app running on localhost:8443 with self-signed SSL
- Google Cast integration for TV viewing
- Embedded post rendering (retweets, quote tweets)

Research below focuses **only** on new features for LAN SSL certificate setup to enable mobile device access.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist for LAN HTTPS. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **mkcert binary management** | Users expect CLI to handle tool installation, not manual setup | MEDIUM | Auto-download from `dl.filippo.io` if not installed; detect platform/architecture |
| **Local CA installation** | HTTPS requires trusted CA; users won't accept browser warnings | LOW | `mkcert -install` once per machine; requires admin/password on some platforms |
| **Certificate generation** | SSL certificates must exist for HTTPS to work | LOW | `mkcert localhost 127.0.0.1 <LAN_IP>` generates certs in project directory |
| **LAN IP binding** | Access from other devices requires binding to 0.0.0.0 or specific LAN IP | LOW | Detect LAN IP automatically; bind FastAPI to all interfaces |
| **Clear status feedback** | Users need to know if setup succeeded or failed | LOW | Typer/Rich output showing CA status, certificate locations, expiration dates |
| **Cross-platform support** | Users run macOS, Linux, Windows | MEDIUM | CA storage differs per platform; path handling varies |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Automatic LAN IP detection** | Eliminates manual IP lookup step | LOW | Use `socket.gethostbyname(socket.gethostname())` or netifaces library |
| **One-command setup** | Single CLI command does all setup | MEDIUM | `x-bookmarked-posts setup-lan` installs mkcert, creates CA, generates certs |
| **Certificate status command** | Users can verify setup before troubleshooting | LOW | Show CA installed, cert paths, expiration date, trusted IPs |
| **Mobile device guidance** | Most users struggle with iOS/Android CA installation | LOW | Print clear instructions after setup; link to docs |
| **Certificate renewal detection** | 2-year cert expiry sneaks up on users | MEDIUM | Store timestamp; warn if approaching expiration; offer regenerate command |
| **Alternative: lancert.dev integration** | No CA installation needed on mobile devices | MEDIUM | Uses pre-issued Let's Encrypt certs for private IPs; less secure but zero-config |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Self-signed certificates** | No external tool dependency | Browser warnings on every device; users bypass warnings incorrectly | mkcert creates trusted CA; same UX as production HTTPS |
| **Production certificate handling** | "Could use this for deployment" | mkcert explicitly warns against production use; root key gives complete MITM power | Document clearly: development only; point to Let's Encrypt for production |
| **CA key sharing between team members** | "Consistent certs across team" | Security nightmare: anyone with rootCA-key.pem can intercept all HTTPS | Each developer has own CA; share only rootCA.pem for mobile devices (not key) |
| **Wildcard DNS domains (.dev, .app)** | "Like production subdomains" | Google HSTS preload forces HTTPS; breaks local development | Use `.test` or `.local` domains for local development |

---

## Feature Dependencies

```
[FastAPI HTTPS Server]
    └──requires──> [SSL Certificate Files]
                        └──requires──> [mkcert binary installed]
                        └──requires──> [Local CA created (mkcert -install)]

[Mobile Device Trust]
    └──requires──> [rootCA.pem exported]
    └──requires──> [Manual device installation]

[Certificate Renewal]
    └──enhances──> [Long-term reliability]
    └──requires──> [Timestamp tracking]

[LAN IP Detection]
    └──enhances──> [Automatic certificate generation]
    └──conflicts──> [Static IP requirements] (if user changes IP, certs regenerate)
```

### Dependency Notes

- **FastAPI HTTPS requires certificate files:** Cannot bind with SSL without valid cert/key PEM files
- **Certificate generation requires mkcert binary:** Must download or find in PATH before generating
- **Local CA requires `mkcert -install`:** First-time setup creates root CA in system trust store (may prompt for password)
- **Mobile device trust requires manual CA export:** Cannot automate iOS/Android installation; must guide users through settings
- **Certificate renewal requires timestamp tracking:** Store generation time to detect expiration (certificates valid 2 years)
- **LAN IP detection enhances automation:** Eliminates manual IP lookup but certificates become IP-specific

---

## User Workflow Phases

### Phase 1: Initial Setup (One-time per machine)

```
User runs: x-bookmarked-posts setup-lan

CLI actions:
1. Check if mkcert installed → if not, download to ~/.local/bin/
2. Run `mkcert -install` → creates CA in system trust store
3. Detect LAN IP (e.g., 192.168.1.50)
4. Generate certs: mkcert localhost 127.0.0.1 192.168.1.50
5. Store certs in ~/.config/x-bookmarked-posts/certs/
6. Print success message with:
   - CA location (mkcert -CAROOT)
   - Certificate files location
   - Expiration date (2 years)
   - Instructions for mobile device trust
```

**User experience by platform:**
- **macOS:** May prompt for password to add CA to keychain
- **Linux:** No password if libnss3-tools installed
- **Windows:** May require admin for system trust store

### Phase 2: Running the Server

```
User runs: x-bookmarked-posts web --lan

CLI actions:
1. Load certificates from stored location
2. Detect current LAN IP (may differ from initial setup)
3. Warn if IP changed since certificate generation
4. Bind FastAPI to 0.0.0.0:8443 with SSL
5. Print URLs:
   - Local: https://localhost:8443
   - LAN: https://192.168.1.50:8443
```

### Phase 3: Mobile Device Trust (Manual)

```
CLI outputs guidance:

"To access from mobile devices, install the CA certificate:

  iOS:
  1. Open https://localhost:8443/ca on this computer
  2. Download rootCA.pem
  3. AirDrop or email to iOS device
  4. Settings > Profile Downloaded > Install
  5. Settings > General > About > Certificate Trust Settings > Enable

  Android:
  1. Download rootCA.pem
  2. Settings > Security > Install certificate > CA certificate
  3. Select file and confirm

  CA certificate location: /Users/you/.local/share/mkcert/rootCA.pem"
```

### Phase 4: Certificate Renewal (2-year cycle)

```
User runs: x-bookmarked-posts cert-status

CLI outputs:
  CA Status: ✓ Installed
  CA Location: /Users/you/.local/share/mkcert
  CA Expires: 2031-06-07 (5 years)

  Certificate: ~/.config/x-bookmarked-posts/certs/localhost+3.pem
  Expires: 2028-06-07 (1 year, 8 months)
  Trusted IPs: localhost, 127.0.0.1, 192.168.1.50

  Recommendation: Certificates valid. No action needed.

---

User runs: x-bookmarked-posts cert-status (when expired)

CLI outputs:
  ⚠ Certificate expired on 2028-06-07

  Run: x-bookmarked-posts renew-certs
```

---

## MVP Definition

### Launch With (v1.3 — LAN Casting Support)

Minimum viable product — what's needed to enable mobile browser access.

- [x] FastAPI web app running on localhost:8443 with HTTPS — **Already complete** (Milestone 2)
- [ ] **CLI command to check mkcert status** — `cert-status` shows if CA installed, cert locations, expiration
- [ ] **CLI command to setup LAN certificates** — `setup-lan` installs mkcert, creates CA, generates certs
- [ ] **Automatic LAN IP detection** — Detect IP at setup time; bind to 0.0.0.0 with detected IP in cert
- [ ] **Mobile device CA installation instructions** — Clear guidance in CLI output and documentation
- [ ] **Server binds to LAN-accessible address** — FastAPI binds to 0.0.0.0 with certificate for LAN IP

### Add After Validation (v1.x)

Features to add once core LAN access is working.

- [ ] **Certificate expiration warning** — Alert user when certificates approaching expiration
- [ ] **LAN IP change detection** — Warn if current IP differs from certificate IP; offer regenerate
- [ ] **Certificate regeneration command** — `renew-certs` to regenerate expired certs
- [ ] **QR code for mobile access** — Display QR code with LAN URL for easy mobile scanning

### Future Consideration (v2+)

Features to defer until LAN casting is validated.

- [ ] **lancert.dev integration** — Alternative: use pre-issued Let's Encrypt certs (no CA installation needed)
- [ ] **mDNS/Bonjour advertising** — Auto-discover service on LAN without knowing IP
- [ ] **Custom domain support** — `.test` domains with /etc/hosts or DNSMasq integration

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| mkcert binary auto-install | HIGH | MEDIUM | P1 |
| Local CA installation | HIGH | LOW | P1 |
| Certificate generation (localhost + LAN IP) | HIGH | LOW | P1 |
| LAN IP detection | HIGH | LOW | P1 |
| Mobile device instructions | MEDIUM | LOW | P1 |
| Certificate status command | MEDIUM | LOW | P2 |
| Certificate expiration tracking | LOW | MEDIUM | P2 |
| LAN IP change detection | MEDIUM | MEDIUM | P2 |
| QR code for mobile access | LOW | LOW | P3 |
| lancert.dev integration | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for v1.3 launch (enables LAN casting)
- P2: Should have, add after core validation
- P3: Nice to have, future consideration

---

## Implementation Complexity Notes

### mkcert Binary Management (MEDIUM)

**Platform detection:**
```python
import platform
import shutil

def get_mkcert_binary():
    # Check system PATH first
    if shutil.which("mkcert"):
        return shutil.which("mkcert")

    # Download from dl.filippo.io/mkcert/latest?for={os}/{arch}
    os_map = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}
    arch_map = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}

    os_name = os_map.get(platform.system(), "linux")
    arch = arch_map.get(platform.machine().lower(), "amd64")
    url = f"https://dl.filippo.io/mkcert/latest?for={os_name}/{arch}"
    # Download, chmod +x, store in ~/.local/bin/
```

**Reference:** Plain Framework mkcert.py implementation ([source](https://plainframework.com/docs/plain-dev/plain/dev/mkcert.py))

### Certificate Generation (LOW)

**Command execution:**
```python
import subprocess
from pathlib import Path

def generate_certs(lan_ip: str, cert_dir: Path) -> tuple[Path, Path]:
    cert_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run([
        "mkcert",
        "-cert-file", str(cert_dir / "cert.pem"),
        "-key-file", str(cert_dir / "key.pem"),
        "localhost", "127.0.0.1", lan_ip
    ], check=True)

    # Store timestamp for renewal tracking
    (cert_dir / ".timestamp").write_text(str(time.time()))

    return cert_dir / "cert.pem", cert_dir / "key.pem"
```

### LAN IP Detection (LOW)

```python
import socket

def get_lan_ip() -> str:
    """Get primary LAN IP address."""
    try:
        # Create socket to external address (doesn't send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
```

### CA Location Discovery (LOW)

```python
def get_ca_root() -> Path | None:
    """Find mkcert CA directory."""
    result = subprocess.run(["mkcert", "-CAROOT"], capture_output=True, text=True)
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return None
```

---

## Certificate Storage Locations (Cross-Platform)

| Platform | CA Storage Location | Access Method |
|----------|---------------------|---------------|
| **macOS** | `~/Library/Application Support/mkcert/` | System Keychain via `security` command |
| **Linux** | `~/.local/share/mkcert/` | NSS database (`certutil`) |
| **Windows** | `%APPDATA%\mkcert\` | Windows Certificate Store |

**Custom location:** Set `CAROOT` environment variable to override default.

---

## Mobile Device Installation Details

### iOS (Full Steps)

1. Transfer `rootCA.pem` to device (AirDrop, email, HTTP server)
2. Open file → iOS shows "Profile Downloaded" prompt
3. Settings → General → VPN & Device Management → Profile → Install
4. Settings → General → About → Certificate Trust Settings
5. Enable full trust for the certificate (required for HTTPS)

**Key difference from Android:** iOS requires **two steps** — profile install AND trust enable.

### Android (Full Steps)

1. Transfer `rootCA.pem` to device
2. Settings → Security → Install certificate → CA certificate
3. Select file and confirm
4. For Android 7+, apps must explicitly trust user certificates (not default)

**Key limitation:** Android 7+ doesn't trust user CAs by default; development builds must opt-in.

---

## Competitor Feature Analysis

| Feature | mkcert (standard) | lancert.dev | Self-signed |
|---------|-------------------|-------------|-------------|
| **Setup complexity** | Install binary + run `-install` | None (API download) | OpenSSL commands |
| **Mobile trust required** | Yes (manual) | No (Let's Encrypt) | Yes (manual) |
| **Browser warnings** | No (trusted locally) | No (globally trusted) | Yes (every device) |
| **Security model** | Local CA (good for dev) | Public keys (no confidentiality) | None (trivially MITM'd) |
| **Certificate validity** | 2 years | 90 days (Let's Encrypt) | User-defined |
| **Production safe** | No (explicitly) | No (explicitly) | No |
| **LAN support** | Yes (specify IPs) | Yes (private IPs) | Yes (specify IPs) |

**Recommendation:** Use mkcert as primary approach; lancert.dev as optional alternative for users who want zero-config mobile setup.

---

## Sources

- [mkcert GitHub Repository](https://github.com/FiloSottile/mkcert) — HIGH confidence (official)
- [mkcert README](https://github.com/FiloSottile/mkcert/blob/master/README.md) — HIGH confidence (official)
- [Plain Framework mkcert.py](https://plainframework.com/docs/plain-dev/plain/dev/mkcert.py) — HIGH confidence (reference implementation)
- [lancert.dev](https://lancert.dev/) — HIGH confidence (official)
- [Local HTTPS with mkcert (Woile)](https://woile.dev/blog/local-https-development-in-python-with-mkcert.html) — MEDIUM confidence (community)
- [Certificate Store Locations (Microsoft)](https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/SecCrypto/system-store-locations.md) — HIGH confidence (official)
- [Linux Certificate Trust Stores (Red Hat)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/securing_networks/using-shared-system-certificates) — HIGH confidence (official)
- [NSS certutil Documentation (Mozilla)](https://devdoc.net/web/developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS/Reference/NSS_tools_:_certutil.html) — HIGH confidence (official)
- [Let's Encrypt: Certificates for Localhost](https://letsencrypt.org/docs/certificates-for-localhost/) — HIGH confidence (official)

---
*Feature research for: LAN Casting Support (v1.3)*
*Researched: 2026-06-07*