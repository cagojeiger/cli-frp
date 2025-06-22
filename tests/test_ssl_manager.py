"""Tests for SSL/TLS certificate management.

Following TDD approach - tests written first to define expected behavior.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from frp_wrapper.server.config import SSLConfig
from frp_wrapper.server.ssl import CertificateStatus, SSLManager


class TestSSLManager:
    """Test SSL certificate management"""

    def test_ssl_manager_init_with_manual_certs(self):
        """Test SSLManager initialization with manual certificates"""
        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )

        manager = SSLManager(ssl_config)

        assert manager.config == ssl_config
        assert manager.cert_file == "/path/to/cert.pem"
        assert manager.key_file == "/path/to/key.pem"
        assert not manager.use_letsencrypt

    def test_ssl_manager_init_with_letsencrypt(self):
        """Test SSLManager initialization with Let's Encrypt"""
        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com", "www.example.com"]
        )

        manager = SSLManager(ssl_config)

        assert manager.config == ssl_config
        assert manager.use_letsencrypt
        assert manager.letsencrypt_email == "test@example.com"
        assert manager.letsencrypt_domains == ["example.com", "www.example.com"]

    def test_ssl_manager_disabled_ssl(self):
        """Test SSLManager with disabled SSL"""
        ssl_config = SSLConfig(enabled=False)

        manager = SSLManager(ssl_config)

        assert not manager.enabled
        assert manager.get_certificate_status() == CertificateStatus.DISABLED

    @patch('pathlib.Path.exists')
    def test_check_certificate_files_exist(self, mock_exists):
        """Test checking if certificate files exist"""
        mock_exists.return_value = True

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        assert manager.check_certificate_files()
        mock_exists.assert_called()

    @patch('pathlib.Path.exists')
    def test_check_certificate_files_missing(self, mock_exists):
        """Test checking missing certificate files"""
        mock_exists.return_value = False

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        assert not manager.check_certificate_files()

    @patch('subprocess.run')
    def test_get_certificate_expiry(self, mock_run):
        """Test getting certificate expiry date"""
        mock_run.return_value.stdout = "notAfter=Dec 31 23:59:59 2024 GMT"
        mock_run.return_value.returncode = 0

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        expiry = manager.get_certificate_expiry()

        assert expiry is not None
        assert expiry.year == 2024
        assert expiry.month == 12
        assert expiry.day == 31

    @patch('subprocess.run')
    def test_get_certificate_expiry_invalid_cert(self, mock_run):
        """Test getting expiry date for invalid certificate"""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "unable to load certificate"

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/invalid.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        expiry = manager.get_certificate_expiry()

        assert expiry is None

    def test_needs_renewal_soon(self):
        """Test checking if certificate needs renewal soon"""
        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem",
            renew_days_before=30
        )
        manager = SSLManager(ssl_config)

        future_date = datetime.now() + timedelta(days=20)
        assert manager.needs_renewal(future_date)

        future_date = datetime.now() + timedelta(days=40)
        assert not manager.needs_renewal(future_date)

    @patch('subprocess.run')
    def test_install_certbot(self, mock_run):
        """Test installing certbot"""
        mock_run.return_value.returncode = 0

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.install_certbot()

        assert result is True
        mock_run.assert_called()

    @patch('subprocess.run')
    def test_obtain_letsencrypt_certificate(self, mock_run):
        """Test obtaining Let's Encrypt certificate"""
        mock_run.return_value.returncode = 0

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com", "www.example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.obtain_certificate()

        assert result is True
        mock_run.assert_called()

    @patch('subprocess.run')
    def test_obtain_letsencrypt_certificate_failure(self, mock_run):
        """Test Let's Encrypt certificate obtainment failure"""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Challenge failed"

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.obtain_certificate()

        assert result is False

    @patch('subprocess.run')
    def test_renew_certificate(self, mock_run):
        """Test certificate renewal"""
        mock_run.return_value.returncode = 0

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.renew_certificate()

        assert result is True
        mock_run.assert_called()

    @patch('subprocess.run')
    @patch('pathlib.Path.write_text')
    def test_setup_auto_renewal_cron(self, mock_write, mock_subprocess):
        """Test setting up automatic renewal cron job"""
        mock_subprocess.return_value.returncode = 0

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"],
            auto_renew=True
        )
        manager = SSLManager(ssl_config)

        result = manager.setup_auto_renewal()

        assert result is True
        mock_write.assert_called()
        mock_subprocess.assert_called()

    def test_get_certificate_status_disabled(self):
        """Test getting certificate status when SSL is disabled"""
        ssl_config = SSLConfig(enabled=False)
        manager = SSLManager(ssl_config)

        status = manager.get_certificate_status()

        assert status == CertificateStatus.DISABLED

    @patch.object(SSLManager, 'check_certificate_files')
    def test_get_certificate_status_missing(self, mock_check):
        """Test getting certificate status when files are missing"""
        mock_check.return_value = False

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        status = manager.get_certificate_status()

        assert status == CertificateStatus.MISSING

    @patch.object(SSLManager, 'check_certificate_files')
    @patch.object(SSLManager, 'get_certificate_expiry')
    def test_get_certificate_status_expired(self, mock_expiry, mock_check):
        """Test getting certificate status when certificate is expired"""
        mock_check.return_value = True
        mock_expiry.return_value = datetime.now() - timedelta(days=1)  # Expired yesterday

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        status = manager.get_certificate_status()

        assert status == CertificateStatus.EXPIRED

    @patch.object(SSLManager, 'check_certificate_files')
    @patch.object(SSLManager, 'get_certificate_expiry')
    @patch.object(SSLManager, 'needs_renewal')
    def test_get_certificate_status_needs_renewal(self, mock_needs_renewal, mock_expiry, mock_check):
        """Test getting certificate status when renewal is needed"""
        mock_check.return_value = True
        mock_expiry.return_value = datetime.now() + timedelta(days=20)
        mock_needs_renewal.return_value = True

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        status = manager.get_certificate_status()

        assert status == CertificateStatus.NEEDS_RENEWAL

    @patch.object(SSLManager, 'check_certificate_files')
    @patch.object(SSLManager, 'get_certificate_expiry')
    @patch.object(SSLManager, 'needs_renewal')
    def test_get_certificate_status_valid(self, mock_needs_renewal, mock_expiry, mock_check):
        """Test getting certificate status when certificate is valid"""
        mock_check.return_value = True
        mock_expiry.return_value = datetime.now() + timedelta(days=60)
        mock_needs_renewal.return_value = False

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        status = manager.get_certificate_status()

        assert status == CertificateStatus.VALID


class TestSSLManagerIntegration:
    """Integration tests for SSL management"""

    def test_complete_letsencrypt_workflow(self):
        """Test complete Let's Encrypt certificate workflow"""
        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["test.example.com"],
            auto_renew=True
        )

        manager = SSLManager(ssl_config)

        assert manager.enabled
        assert manager.use_letsencrypt
        assert manager.letsencrypt_email == "test@example.com"
        assert manager.letsencrypt_domains == ["test.example.com"]

    def test_manual_certificate_workflow(self):
        """Test manual certificate management workflow"""
        with tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as cert_file, \
             tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as key_file:

            cert_path = Path(cert_file.name)
            key_path = Path(key_file.name)

        try:
            ssl_config = SSLConfig(
                enabled=True,
                cert_file=str(cert_path),
                key_file=str(key_path)
            )

            manager = SSLManager(ssl_config)

            assert manager.enabled
            assert not manager.use_letsencrypt
            assert manager.cert_file == str(cert_path)
            assert manager.key_file == str(key_path)

        finally:
            cert_path.unlink(missing_ok=True)
            key_path.unlink(missing_ok=True)


class TestSSLManagerEdgeCases:
    """Test edge cases and error conditions for SSL manager"""

    @patch('subprocess.run')
    def test_install_certbot_already_installed(self, mock_run):
        """Test certbot installation when already installed"""
        mock_run.return_value.returncode = 0

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.install_certbot()
        assert result is True

    @patch('subprocess.run')
    def test_install_certbot_failure(self, mock_run):
        """Test certbot installation failure"""
        mock_run.side_effect = [
            Mock(returncode=1),  # which certbot fails
            Mock(returncode=1)   # apt install fails
        ]

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.install_certbot()
        assert result is False

    @patch('subprocess.run')
    def test_install_certbot_exception(self, mock_run):
        """Test certbot installation with exception"""
        mock_run.side_effect = Exception("Network error")

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.install_certbot()
        assert result is False

    @patch('subprocess.run')
    def test_renew_certificate_failure(self, mock_run):
        """Test certificate renewal failure"""
        mock_run.return_value.returncode = 1

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.renew_certificate()
        assert result is False

    @patch('subprocess.run')
    def test_renew_certificate_exception(self, mock_run):
        """Test certificate renewal with exception"""
        mock_run.side_effect = Exception("Renewal failed")

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"]
        )
        manager = SSLManager(ssl_config)

        result = manager.renew_certificate()
        assert result is False

    @patch('subprocess.run')
    @patch('pathlib.Path.write_text')
    def test_setup_auto_renewal_failure(self, mock_write, mock_subprocess):
        """Test auto renewal setup failure"""
        mock_write.side_effect = Exception("Permission denied")

        ssl_config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="test@example.com",
            letsencrypt_domains=["example.com"],
            auto_renew=True
        )
        manager = SSLManager(ssl_config)

        result = manager.setup_auto_renewal()
        assert result is False

    def test_get_certificate_info_disabled(self):
        """Test getting certificate info when SSL is disabled"""
        ssl_config = SSLConfig(enabled=False)
        manager = SSLManager(ssl_config)

        info = manager.get_certificate_info()

        assert info['status'] == 'disabled'
        assert info['enabled'] is False
        assert info['use_letsencrypt'] is False

    @patch.object(SSLManager, 'get_certificate_status')
    @patch.object(SSLManager, 'get_certificate_expiry')
    def test_get_certificate_info_with_expiry(self, mock_expiry, mock_status):
        """Test getting certificate info with expiry date"""
        mock_status.return_value = CertificateStatus.VALID
        mock_expiry.return_value = datetime(2024, 12, 31, 23, 59, 59)

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        info = manager.get_certificate_info()

        assert info['status'] == 'valid'
        assert info['enabled'] is True
        assert info['expiry_date'] == '2024-12-31T23:59:59'

    @patch.object(SSLManager, 'get_certificate_status')
    @patch.object(SSLManager, 'get_certificate_expiry')
    @patch.object(SSLManager, 'needs_renewal')
    def test_get_certificate_info_needs_renewal(self, mock_needs_renewal, mock_expiry, mock_status):
        """Test getting certificate info when renewal is needed"""
        mock_status.return_value = CertificateStatus.NEEDS_RENEWAL
        mock_expiry.return_value = datetime(2024, 12, 31, 23, 59, 59)
        mock_needs_renewal.return_value = True

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        info = manager.get_certificate_info()

        assert info['status'] == 'needs_renewal'
        assert info['needs_renewal'] is True

    @patch('subprocess.run')
    def test_get_certificate_expiry_parse_error(self, mock_run):
        """Test certificate expiry parsing error"""
        mock_run.return_value.stdout = "invalid date format"
        mock_run.return_value.returncode = 0

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        expiry = manager.get_certificate_expiry()
        assert expiry is None

    @patch('subprocess.run')
    def test_get_certificate_expiry_exception(self, mock_run):
        """Test certificate expiry with subprocess exception"""
        mock_run.side_effect = Exception("Command failed")

        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        manager = SSLManager(ssl_config)

        expiry = manager.get_certificate_expiry()
        assert expiry is None
