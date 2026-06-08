"""LAN SSL certificate management using mkcert.

CERT-04: System detects LAN IP automatically for certificate generation.
CERT-02: User can generate LAN-accessible SSL certificates via CLI.

Uses mkcert (external tool) to generate locally-trusted certificates
valid for localhost, 127.0.0.1, LAN IP, and ::1 (IPv6).
"""

import socket
import subprocess
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend


def get_lan_ip() -> Optional[str]:
    """Detect primary outbound LAN IP address using UDP socket trick.

    Per D-03: Uses UDP socket connect (stdlib only, no external deps).
    Connects to public DNS (8.8.8.8:80) to determine routing table,
    then reads local socket address. No data is actually sent.

    Returns:
        LAN IP address (e.g., "192.168.1.100") or None if detection fails.
    """
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
            # Connect to public DNS to determine routing
            # No data is actually sent
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except OSError:
        return None


def check_mkcert_installed() -> bool:
    """Check if mkcert CLI tool is installed and accessible.

    Returns:
        True if mkcert binary is in PATH and executable.
    """
    try:
        result = subprocess.run(
            ['mkcert', '-help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_mkcert_ca_root() -> Path:
    """Get the mkcert CA root directory path.

    Returns:
        Path to the mkcert CA directory (contains rootCA.pem).

    Raises:
        FileNotFoundError: If mkcert is not installed.
        RuntimeError: If mkcert -CAROOT fails.
    """
    if not check_mkcert_installed():
        raise FileNotFoundError("mkcert is not installed")

    result = subprocess.run(
        ['mkcert', '-CAROOT'],
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode != 0:
        raise RuntimeError(f"mkcert -CAROOT failed: {result.stderr}")

    return Path(result.stdout.strip())


def get_ca_certificate_path() -> Path:
    """Get path to root CA certificate for mobile device installation.

    Returns:
        Path to rootCA.pem file.

    Raises:
        FileNotFoundError: If mkcert is not installed.
    """
    ca_root = get_mkcert_ca_root()
    return ca_root / "rootCA.pem"


def generate_lan_certificates(
    lan_ip: str,
    cert_path: Path,
    key_path: Path,
    hosts: Optional[list[str]] = None,
) -> tuple[Path, Path]:
    """Generate LAN-accessible SSL certificates using mkcert.

    Per D-02: Certificates stored in data/lan.crt and data/lan.key.
    Per D-10: Includes IPv6 localhost (::1) in SANs.

    Args:
        lan_ip: LAN IP address to include in certificate.
        cert_path: Path to save certificate file.
        key_path: Path to save private key file.
        hosts: Additional hostnames/IPs. Defaults to localhost + loopback + LAN IP + ::1.

    Returns:
        Tuple of (cert_path, key_path).

    Raises:
        FileNotFoundError: If mkcert is not installed.
        RuntimeError: If certificate generation fails.
    """
    if not check_mkcert_installed():
        raise FileNotFoundError(
            "mkcert is not installed. "
            "Install with: brew install mkcert (macOS), "
            "choco install mkcert (Windows), or "
            "apt install mkcert (Linux)."
        )

    # Ensure parent directories exist
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # Default hosts: localhost, 127.0.0.1, LAN IP, ::1
    if hosts is None:
        hosts = ["localhost", "127.0.0.1", lan_ip, "::1"]
    elif lan_ip not in hosts:
        hosts.append(lan_ip)

    # Build mkcert command
    cmd = [
        'mkcert',
        '-cert-file', str(cert_path),
        '-key-file', str(key_path),
    ] + hosts

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"mkcert failed: {result.stderr}")

    return cert_path, key_path


def backup_old_certificates(
    cert_path: Path,
    key_path: Path,
) -> Optional[tuple[Path, Path]]:
    """Backup existing certificate files before regeneration.

    Per D-05: Creates .bak files before overwriting.

    Args:
        cert_path: Path to certificate file.
        key_path: Path to private key file.

    Returns:
        Tuple of (backup_cert_path, backup_key_path) if files existed, None otherwise.
    """
    if not cert_path.exists() and not key_path.exists():
        return None

    backup_cert = cert_path.with_suffix('.crt.bak')
    backup_key = key_path.with_suffix('.key.bak')

    if cert_path.exists():
        backup_cert.write_bytes(cert_path.read_bytes())
    if key_path.exists():
        backup_key.write_bytes(key_path.read_bytes())

    return (backup_cert, backup_key)


def get_certificate_info(cert_path: Path) -> dict:
    """Read certificate file and extract metadata.

    Used by MAINT-01: Certificate status and expiration checking.

    Args:
        cert_path: Path to certificate file.

    Returns:
        Dict with:
        - path: Path to certificate
        - exists: bool
        - created: datetime or None
        - expires: datetime or None
        - days_until_expiry: int or None
        - sans: list of Subject Alternative Names
        - is_expired: bool or None
        - is_expiring_soon: bool (True if < 30 days, per D-04)

    Raises:
        FileNotFoundError: If certificate file doesn't exist.
    """
    if not cert_path.exists():
        return {
            'path': cert_path,
            'exists': False,
            'created': None,
            'expires': None,
            'days_until_expiry': None,
            'sans': [],
            'is_expired': None,
            'is_expiring_soon': None,
        }

    # Read and parse certificate
    cert_pem = cert_path.read_bytes()
    cert = x509.load_pem_x509_certificate(cert_pem, default_backend())

    # Extract SANs
    sans = []
    try:
        san_ext = cert.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        )
        sans = [
            str(name.value) for name in san_ext.value
        ]
    except x509.ExtensionNotFound:
        pass

    # Calculate days until expiry
    now = datetime.utcnow()
    expires = cert.not_valid_after_utc.replace(tzinfo=None)
    days_until_expiry = (expires - now).days

    return {
        'path': cert_path,
        'exists': True,
        'created': cert.not_valid_before_utc.replace(tzinfo=None),
        'expires': expires,
        'days_until_expiry': days_until_expiry,
        'sans': sans,
        'is_expired': days_until_expiry < 0,
        'is_expiring_soon': 0 <= days_until_expiry < 30,  # D-04: warn if < 30 days
    }


__all__ = [
    "get_lan_ip",
    "check_mkcert_installed",
    "get_mkcert_ca_root",
    "get_ca_certificate_path",
    "generate_lan_certificates",
    "backup_old_certificates",
    "get_certificate_info",
]