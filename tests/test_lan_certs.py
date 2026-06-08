"""Tests for LAN certificate management utilities.

CERT-04: System detects LAN IP automatically for certificate generation.
CERT-02: User can generate LAN-accessible SSL certificates via CLI.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGetLanIp:
    """Tests for get_lan_ip() function."""

    def test_returns_valid_ipv4_address(self):
        """Test that get_lan_ip returns a valid IPv4 address string or None."""
        from src.web.lan_certs import get_lan_ip

        result = get_lan_ip()
        if result is not None:
            # Should be a valid IPv4 address format
            parts = result.split(".")
            assert len(parts) == 4
            for part in parts:
                assert 0 <= int(part) <= 255

    def test_returns_none_on_socket_error(self):
        """Test that get_lan_ip returns None when socket fails."""
        from src.web.lan_certs import get_lan_ip

        with patch("socket.socket") as mock_socket:
            mock_socket.side_effect = OSError("Network error")
            result = get_lan_ip()
            assert result is None


class TestCheckMkcertInstalled:
    """Tests for check_mkcert_installed() function."""

    def test_returns_true_when_mkcert_available(self):
        """Test that check_mkcert_installed returns True when mkcert is in PATH."""
        from src.web.lan_certs import check_mkcert_installed

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = check_mkcert_installed()
            assert result is True

    def test_returns_false_when_mkcert_not_found(self):
        """Test that check_mkcert_installed returns False when mkcert not installed."""
        from src.web.lan_certs import check_mkcert_installed

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = check_mkcert_installed()
            assert result is False

    def test_returns_false_on_timeout(self):
        """Test that check_mkcert_installed returns False on timeout."""
        from src.web.lan_certs import check_mkcert_installed

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = __import__("subprocess").TimeoutExpired("cmd", 5)
            result = check_mkcert_installed()
            assert result is False


class TestGetMkcertCaRoot:
    """Tests for get_mkcert_ca_root() function."""

    def test_returns_path_when_mkcert_installed(self):
        """Test that get_mkcert_ca_root returns Path when mkcert installed."""
        from src.web.lan_certs import get_mkcert_ca_root

        with patch("src.web.lan_certs.check_mkcert_installed", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="/home/user/.local/share/mkcert\n"
                )
                result = get_mkcert_ca_root()
                assert isinstance(result, Path)
                assert str(result) == "/home/user/.local/share/mkcert"

    def test_raises_file_not_found_when_mkcert_not_installed(self):
        """Test that get_mkcert_ca_root raises FileNotFoundError when mkcert not installed."""
        from src.web.lan_certs import get_mkcert_ca_root

        with patch("src.web.lan_certs.check_mkcert_installed", return_value=False):
            with pytest.raises(FileNotFoundError):
                get_mkcert_ca_root()

    def test_raises_runtime_error_on_mkcert_failure(self):
        """Test that get_mkcert_ca_root raises RuntimeError on mkcert -CAROOT failure."""
        from src.web.lan_certs import get_mkcert_ca_root

        with patch("src.web.lan_certs.check_mkcert_installed", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stderr="mkcert error"
                )
                with pytest.raises(RuntimeError):
                    get_mkcert_ca_root()


class TestGetCaCertificatePath:
    """Tests for get_ca_certificate_path() function."""

    def test_returns_root_ca_pem_path(self):
        """Test that get_ca_certificate_path returns Path to rootCA.pem."""
        from src.web.lan_certs import get_ca_certificate_path

        with patch("src.web.lan_certs.get_mkcert_ca_root", return_value=Path("/home/user/.local/share/mkcert")):
            result = get_ca_certificate_path()
            assert isinstance(result, Path)
            assert result.name == "rootCA.pem"


class TestGenerateLanCertificates:
    """Tests for generate_lan_certificates() function."""

    def test_creates_cert_files_with_correct_sans(self):
        """Test that generate_lan_certificates creates PEM files with correct SANs."""
        from src.web.lan_certs import generate_lan_certificates

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "lan.crt"
            key_path = Path(tmpdir) / "lan.key"
            lan_ip = "192.168.1.100"

            with patch("src.web.lan_certs.check_mkcert_installed", return_value=True):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)

                    result = generate_lan_certificates(lan_ip, cert_path, key_path)

                    assert result == (cert_path, key_path)
                    # Verify mkcert was called with correct arguments
                    call_args = mock_run.call_args[0][0]
                    assert "localhost" in call_args
                    assert "127.0.0.1" in call_args
                    assert lan_ip in call_args
                    assert "::1" in call_args

    def test_includes_ipv6_localhost(self):
        """Test that ::1 (IPv6 localhost) is included in SANs."""
        from src.web.lan_certs import generate_lan_certificates

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "lan.crt"
            key_path = Path(tmpdir) / "lan.key"

            with patch("src.web.lan_certs.check_mkcert_installed", return_value=True):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)

                    generate_lan_certificates("192.168.1.100", cert_path, key_path)

                    call_args = mock_run.call_args[0][0]
                    assert "::1" in call_args

    def test_raises_file_not_found_when_mkcert_not_installed(self):
        """Test that generate_lan_certificates raises FileNotFoundError when mkcert not installed."""
        from src.web.lan_certs import generate_lan_certificates

        with patch("src.web.lan_certs.check_mkcert_installed", return_value=False):
            with pytest.raises(FileNotFoundError):
                generate_lan_certificates("192.168.1.100", Path("cert.pem"), Path("key.pem"))

    def test_raises_runtime_error_on_mkcert_failure(self):
        """Test that generate_lan_certificates raises RuntimeError on mkcert failure."""
        from src.web.lan_certs import generate_lan_certificates

        with patch("src.web.lan_certs.check_mkcert_installed", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="mkcert error")

                with pytest.raises(RuntimeError):
                    generate_lan_certificates("192.168.1.100", Path("cert.pem"), Path("key.pem"))


class TestBackupOldCertificates:
    """Tests for backup_old_certificates() function."""

    def test_creates_bak_files(self):
        """Test that backup_old_certificates creates .bak files."""
        from src.web.lan_certs import backup_old_certificates

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "lan.crt"
            key_path = Path(tmpdir) / "lan.key"

            # Create existing files
            cert_path.write_text("cert content")
            key_path.write_text("key content")

            result = backup_old_certificates(cert_path, key_path)

            assert result is not None
            backup_cert, backup_key = result
            assert backup_cert.exists()
            assert backup_key.exists()
            assert backup_cert.read_text() == "cert content"
            assert backup_key.read_text() == "key content"

    def test_returns_none_when_no_files_exist(self):
        """Test that backup_old_certificates returns None when no files exist."""
        from src.web.lan_certs import backup_old_certificates

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "lan.crt"
            key_path = Path(tmpdir) / "lan.key"

            result = backup_old_certificates(cert_path, key_path)

            assert result is None


class TestGetCertificateInfo:
    """Tests for get_certificate_info() function."""

    def test_returns_dict_with_paths_and_dates(self):
        """Test that get_certificate_info returns dict with paths, creation date, expiration, SANs."""
        from src.web.lan_certs import get_certificate_info
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        from datetime import datetime, timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "test.crt"

            # Create a test certificate
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "test"),
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
                datetime.utcnow() + timedelta(days=30)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
                ]),
                critical=False,
            ).sign(key, hashes.SHA256(), default_backend())

            cert_path.write_bytes(cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM))

            result = get_certificate_info(cert_path)

            assert result["exists"] is True
            assert result["path"] == cert_path
            assert "expires" in result
            assert "sans" in result
            assert len(result["sans"]) == 2

    def test_returns_exists_false_when_file_missing(self):
        """Test that get_certificate_info returns exists=False for missing file."""
        from src.web.lan_certs import get_certificate_info

        result = get_certificate_info(Path("/nonexistent/path.crt"))

        assert result["exists"] is False
        assert result["sans"] == []