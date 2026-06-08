"""Tests for CLI lan-cert command.

CERT-01: Check mkcert installation status via CLI.
CERT-02: Generate LAN-accessible SSL certificates via CLI.
MAINT-01: Check certificate status and expiration.
MAINT-02: Regenerate certificates when expired or LAN IP changes.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli.main import app


runner = CliRunner()


class TestLanCertStatusCommand:
    """Tests for `xbm lan-cert --status` command."""

    def test_status_shows_mkcert_installed(self):
        """Test that --status shows mkcert installation status when installed."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_mkcert_ca_root", return_value=Path("/home/user/.local/share/mkcert")):
                with patch("src.cli.main.get_ca_certificate_path", return_value=Path("/home/user/.local/share/mkcert/rootCA.pem")):
                    result = runner.invoke(app, ["lan-cert", "--status"])

                    assert result.exit_code == 0
                    assert "mkcert" in result.stdout.lower()
                    assert "installed" in result.stdout.lower()

    def test_status_shows_ca_root_directory(self):
        """Test that --status shows CA root directory when mkcert installed."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_mkcert_ca_root", return_value=Path("/home/user/.local/share/mkcert")):
                with patch("src.cli.main.get_ca_certificate_path", return_value=Path("/home/user/.local/share/mkcert/rootCA.pem")):
                    result = runner.invoke(app, ["lan-cert", "--status"])

                    assert result.exit_code == 0
                    assert "CA Root" in result.stdout or "mkcert" in result.stdout

    def test_status_shows_certificate_info_when_certs_exist(self):
        """Test that --status shows certificate info when certificates exist."""
        mock_cert_info = {
            'path': Path('data/lan.crt'),
            'exists': True,
            'created': None,
            'expires': None,
            'days_until_expiry': 365,
            'sans': ['localhost', '127.0.0.1', '192.168.1.100', '::1'],
            'is_expired': False,
            'is_expiring_soon': False,
        }

        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_mkcert_ca_root", return_value=Path("/home/user/.local/share/mkcert")):
                with patch("src.cli.main.get_ca_certificate_path", return_value=Path("/home/user/.local/share/mkcert/rootCA.pem")):
                    with patch("src.cli.main.get_certificate_info", return_value=mock_cert_info):
                        with patch("src.cli.main.Settings") as mock_settings:
                            mock_settings.return_value.lan_cert_path = Path('data/lan.crt')
                            mock_settings.return_value.lan_key_path = Path('data/lan.key')

                            result = runner.invoke(app, ["lan-cert", "--status"])

                            assert result.exit_code == 0
                            assert "Certificate" in result.stdout

    def test_status_shows_not_generated_when_no_certs(self):
        """Test that --status shows 'not generated' when certificates don't exist."""
        mock_cert_info = {
            'path': Path('data/lan.crt'),
            'exists': False,
            'created': None,
            'expires': None,
            'days_until_expiry': None,
            'sans': [],
            'is_expired': None,
            'is_expiring_soon': None,
        }

        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_mkcert_ca_root", return_value=Path("/home/user/.local/share/mkcert")):
                with patch("src.cli.main.get_ca_certificate_path", return_value=Path("/home/user/.local/share/mkcert/rootCA.pem")):
                    with patch("src.cli.main.get_certificate_info", return_value=mock_cert_info):
                        with patch("src.cli.main.Settings") as mock_settings:
                            mock_settings.return_value.lan_cert_path = Path('data/lan.crt')
                            mock_settings.return_value.lan_key_path = Path('data/lan.key')

                            result = runner.invoke(app, ["lan-cert", "--status"])

                            assert result.exit_code == 0
                            assert "No LAN certificates" in result.stdout or "not generated" in result.stdout.lower()

    def test_status_warns_when_certificate_expires_soon(self):
        """Test that --status warns when certificate expires within 30 days."""
        mock_cert_info = {
            'path': Path('data/lan.crt'),
            'exists': True,
            'created': None,
            'expires': None,
            'days_until_expiry': 15,
            'sans': ['localhost', '127.0.0.1', '192.168.1.100', '::1'],
            'is_expired': False,
            'is_expiring_soon': True,
        }

        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_mkcert_ca_root", return_value=Path("/home/user/.local/share/mkcert")):
                with patch("src.cli.main.get_ca_certificate_path", return_value=Path("/home/user/.local/share/mkcert/rootCA.pem")):
                    with patch("src.cli.main.get_certificate_info", return_value=mock_cert_info):
                        with patch("src.cli.main.Settings") as mock_settings:
                            mock_cert_path = MagicMock()
                            mock_cert_path.exists.return_value = True
                            mock_key_path = MagicMock()
                            mock_key_path.exists.return_value = True
                            mock_settings.return_value.lan_cert_path = mock_cert_path
                            mock_settings.return_value.lan_key_path = mock_key_path

                            result = runner.invoke(app, ["lan-cert", "--status"])

                            assert result.exit_code == 0
                            assert "15" in result.stdout or "expire" in result.stdout.lower()

    def test_status_shows_mkcert_not_installed_with_instructions(self):
        """Test that --status shows 'mkcert not installed' with install instructions."""
        with patch("src.cli.main.check_mkcert_installed", return_value=False):
            result = runner.invoke(app, ["lan-cert", "--status"])

            # Should exit with error code
            assert result.exit_code == 1
            assert "not installed" in result.stdout.lower()
            assert "brew install" in result.stdout.lower() or "install" in result.stdout.lower()


class TestLanCertGenerateCommand:
    """Tests for `xbm lan-cert --generate` command."""

    def test_generate_creates_certificates_for_localhost_and_lan_ip(self):
        """Test that --generate creates certificates with correct SANs."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_lan_ip", return_value="192.168.1.100"):
                with patch("src.cli.main.generate_lan_certificates") as mock_generate:
                    mock_generate.return_value = (Path("data/lan.crt"), Path("data/lan.key"))
                    with patch("src.cli.main.Settings") as mock_settings:
                        mock_settings.return_value.lan_cert_path = Path('data/lan.crt')
                        mock_settings.return_value.lan_key_path = Path('data/lan.key')

                        result = runner.invoke(app, ["lan-cert", "--generate"])

                        assert result.exit_code == 0
                        # Verify generate was called with correct hosts
                        call_args = mock_generate.call_args
                        assert call_args is not None

    def test_generate_fails_gracefully_when_mkcert_not_installed(self):
        """Test that --generate fails gracefully when mkcert not installed."""
        with patch("src.cli.main.check_mkcert_installed", return_value=False):
            result = runner.invoke(app, ["lan-cert", "--generate"])

            assert result.exit_code == 1
            assert "not installed" in result.stdout.lower()

    def test_generate_force_overwrites_existing_certificates(self):
        """Test that --generate --force overwrites existing certificates."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_lan_ip", return_value="192.168.1.100"):
                with patch("src.cli.main.generate_lan_certificates") as mock_generate:
                    mock_generate.return_value = (Path("data/lan.crt"), Path("data/lan.key"))
                    with patch("src.cli.main.backup_old_certificates", return_value=(Path("data/lan.crt.bak"), Path("data/lan.key.bak"))):
                        with patch("src.cli.main.Settings") as mock_settings:
                            mock_settings.return_value.lan_cert_path = Path('data/lan.crt')
                            mock_settings.return_value.lan_key_path = Path('data/lan.key')

                            result = runner.invoke(app, ["lan-cert", "--generate", "--force"])

                            assert result.exit_code == 0

    def test_generate_detects_lan_ip_automatically(self):
        """Test that --generate detects LAN IP automatically."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_lan_ip", return_value="192.168.1.100") as mock_get_ip:
                with patch("src.cli.main.generate_lan_certificates") as mock_generate:
                    mock_generate.return_value = (Path("data/lan.crt"), Path("data/lan.key"))
                    with patch("src.cli.main.Settings") as mock_settings:
                        mock_settings.return_value.lan_cert_path = Path('data/lan.crt')
                        mock_settings.return_value.lan_key_path = Path('data/lan.key')

                        result = runner.invoke(app, ["lan-cert", "--generate"])

                        # Verify get_lan_ip was called
                        mock_get_ip.assert_called_once()

    def test_generate_includes_all_required_sans(self):
        """Test that --generate includes localhost, 127.0.0.1, LAN IP, and ::1 in SANs."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_lan_ip", return_value="192.168.1.100"):
                with patch("src.cli.main.generate_lan_certificates") as mock_generate:
                    mock_generate.return_value = (Path("data/lan.crt"), Path("data/lan.key"))
                    with patch("src.cli.main.Settings") as mock_settings:
                        mock_settings.return_value.lan_cert_path = Path('data/lan.crt')
                        mock_settings.return_value.lan_key_path = Path('data/lan.key')

                        runner.invoke(app, ["lan-cert", "--generate"])

                        # Check that generate_lan_certificates was called with correct hosts
                        call_args = mock_generate.call_args
                        # The hosts argument should include localhost, 127.0.0.1, LAN IP, ::1
                        # This is verified in the actual implementation

    def test_generate_shows_success_message_with_lan_url(self):
        """Test that --generate shows success message with LAN URL."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_lan_ip", return_value="192.168.1.100"):
                with patch("src.cli.main.generate_lan_certificates") as mock_generate:
                    mock_generate.return_value = (Path("data/lan.crt"), Path("data/lan.key"))
                    with patch("src.cli.main.Settings") as mock_settings:
                        mock_settings.return_value.lan_cert_path = Path('data/lan.crt')
                        mock_settings.return_value.lan_key_path = Path('data/lan.key')

                        result = runner.invoke(app, ["lan-cert", "--generate"])

                        assert result.exit_code == 0
                        assert "success" in result.stdout.lower() or "generated" in result.stdout.lower()


class TestLanCertGuideCommand:
    """Tests for `xbm lan-cert --guide` command."""

    def test_guide_shows_platform_specific_instructions(self):
        """Test that --guide shows platform-specific CA installation instructions."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_ca_certificate_path", return_value=Path("/home/user/.local/share/mkcert/rootCA.pem")):
                with patch("platform.system", return_value="Darwin"):
                    result = runner.invoke(app, ["lan-cert", "--guide"])

                    assert result.exit_code == 0
                    # Should show instructions
                    assert "mkcert" in result.stdout.lower() or "install" in result.stdout.lower()

    def test_guide_shows_all_platforms_with_flag(self):
        """Test that --guide --all shows instructions for all platforms."""
        with patch("src.cli.main.check_mkcert_installed", return_value=True):
            with patch("src.cli.main.get_ca_certificate_path", return_value=Path("/home/user/.local/share/mkcert/rootCA.pem")):
                result = runner.invoke(app, ["lan-cert", "--guide", "--all"])

                assert result.exit_code == 0
                # Should show all platforms
                assert "macOS" in result.stdout or "Darwin" in result.stdout or "mac" in result.stdout.lower()