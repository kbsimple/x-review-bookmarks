"""HTTPS certificate generation for localhost.

WEB-02: Web app serves posts over HTTPS (required for Google Cast).

Generates self-signed certificates for localhost development.
"""

from pathlib import Path
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_self_signed_cert(
    cert_path: Path,
    key_path: Path,
    common_name: str = "localhost",
    days_valid: int = 365,
) -> tuple[Path, Path]:
    """Generate a self-signed certificate for localhost.

    Args:
        cert_path: Path to save the certificate file.
        key_path: Path to save the private key file.
        common_name: Common name for the certificate (default: localhost).
        days_valid: Number of days the certificate is valid (default: 365).

    Returns:
        Tuple of (cert_path, key_path).

    Note:
        Certificates are self-signed and will show a browser warning.
        This is acceptable for local development and Google Cast requires HTTPS.
    """
    # Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "X Bookmarked Posts"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=days_valid)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256())

    # Ensure parent directories exist
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # Write private key
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    # Write certificate
    cert_path.write_bytes(
        cert.public_bytes(serialization.Encoding.PEM)
    )

    # Set restrictive permissions on key file
    try:
        key_path.chmod(0o600)
    except OSError:
        pass  # May fail on some filesystems

    return cert_path, key_path


def ensure_https_certs(
    cert_path: Path | None = None,
    key_path: Path | None = None,
) -> tuple[Path, Path]:
    """Ensure HTTPS certificates exist, generating if needed.

    Args:
        cert_path: Path to certificate file. Defaults to data/localhost.crt.
        key_path: Path to private key file. Defaults to data/localhost.key.

    Returns:
        Tuple of (cert_path, key_path).
    """
    if cert_path is None:
        cert_path = Path("data/localhost.crt")
    if key_path is None:
        key_path = Path("data/localhost.key")

    if not cert_path.exists() or not key_path.exists():
        generate_self_signed_cert(cert_path, key_path)

    return cert_path, key_path


__all__ = ["generate_self_signed_cert", "ensure_https_certs"]