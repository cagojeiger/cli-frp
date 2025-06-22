"""SSL/TLS certificate management for FRP server.

This module provides SSL certificate management including:
- Manual certificate file management
- Let's Encrypt integration for automatic certificate issuance
- Certificate renewal and monitoring
- Automatic renewal setup via cron jobs
"""

import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .config import SSLConfig


class CertificateStatus(str, Enum):
    """SSL certificate status enumeration"""
    DISABLED = "disabled"
    MISSING = "missing"
    EXPIRED = "expired"
    NEEDS_RENEWAL = "needs_renewal"
    VALID = "valid"
    ERROR = "error"


class SSLManager:
    """Manages SSL/TLS certificates for FRP server.

    This class provides comprehensive SSL certificate management including:
    - Manual certificate file validation
    - Let's Encrypt certificate issuance and renewal
    - Certificate status monitoring
    - Automatic renewal setup
    """

    def __init__(self, config: SSLConfig):
        """Initialize SSL manager with configuration.

        Args:
            config: SSL configuration object
        """
        self.config = config

    @property
    def enabled(self) -> bool:
        """Check if SSL is enabled"""
        return self.config.enabled

    @property
    def use_letsencrypt(self) -> bool:
        """Check if using Let's Encrypt"""
        return self.config.use_letsencrypt

    @property
    def cert_file(self) -> str | None:
        """Get certificate file path"""
        return self.config.cert_file

    @property
    def key_file(self) -> str | None:
        """Get private key file path"""
        return self.config.key_file

    @property
    def letsencrypt_email(self) -> str | None:
        """Get Let's Encrypt email"""
        return self.config.letsencrypt_email

    @property
    def letsencrypt_domains(self) -> list[str]:
        """Get Let's Encrypt domains"""
        return self.config.letsencrypt_domains

    def check_certificate_files(self) -> bool:
        """Check if certificate files exist.

        Returns:
            True if both certificate and key files exist, False otherwise
        """
        if not self.enabled or self.use_letsencrypt:
            return True

        if not self.cert_file or not self.key_file:
            return False

        cert_path = Path(self.cert_file)
        key_path = Path(self.key_file)

        return cert_path.exists() and key_path.exists()

    def get_certificate_expiry(self) -> datetime | None:
        """Get certificate expiry date using openssl.

        Returns:
            Certificate expiry datetime, or None if unable to determine
        """
        if not self.enabled or not self.cert_file:
            return None

        try:
            result = subprocess.run([
                'openssl', 'x509', '-in', self.cert_file,
                '-noout', '-dates'
            ], check=False, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return None

            for line in result.stdout.split('\n'):
                if line.startswith('notAfter='):
                    date_str = line.replace('notAfter=', '').strip()
                    try:
                        return datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                    except ValueError:
                        return datetime.strptime(date_str.replace(' GMT', ''), '%b %d %H:%M:%S %Y')

            return None

        except Exception:
            return None

    def needs_renewal(self, expiry_date: datetime) -> bool:
        """Check if certificate needs renewal.

        Args:
            expiry_date: Certificate expiry date

        Returns:
            True if certificate needs renewal, False otherwise
        """
        if not expiry_date:
            return True

        days_until_expiry = (expiry_date - datetime.now()).days
        return days_until_expiry <= self.config.renew_days_before

    def install_certbot(self) -> bool:
        """Install certbot for Let's Encrypt certificates.

        Returns:
            True if installation successful, False otherwise
        """
        try:
            which_result = subprocess.run(['which', 'certbot'], check=False, capture_output=True, text=True)
            if which_result.returncode == 0:
                return True

            result: subprocess.CompletedProcess[str] = subprocess.run([
                'sudo', 'apt', 'update', '&&',
                'sudo', 'apt', 'install', '-y', 'certbot'
            ], check=False, capture_output=True, text=True, timeout=300)

            return result.returncode == 0

        except Exception:
            return False

    def obtain_certificate(self) -> bool:
        """Obtain Let's Encrypt certificate.

        Returns:
            True if certificate obtained successfully, False otherwise
        """
        if not self.use_letsencrypt:
            return False

        if not self.letsencrypt_email or not self.letsencrypt_domains:
            return False

        try:
            cmd = [
                'sudo', 'certbot', 'certonly',
                '--standalone',
                '--non-interactive',
                '--agree-tos',
                '--email', self.letsencrypt_email
            ]

            for domain in self.letsencrypt_domains:
                cmd.extend(['-d', domain])

            if self.config.letsencrypt_challenge_type == 'dns':
                cmd.append('--manual')
                cmd.append('--preferred-challenges=dns')

            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=300)

            return result.returncode == 0

        except Exception:
            return False

    def renew_certificate(self) -> bool:
        """Renew Let's Encrypt certificate.

        Returns:
            True if renewal successful, False otherwise
        """
        if not self.use_letsencrypt:
            return False

        try:
            result = subprocess.run([
                'sudo', 'certbot', 'renew',
                '--non-interactive',
                '--quiet'
            ], check=False, capture_output=True, text=True, timeout=300)

            return result.returncode == 0

        except Exception:
            return False

    def setup_auto_renewal(self) -> bool:
        """Setup automatic certificate renewal via cron.

        Returns:
            True if auto-renewal setup successful, False otherwise
        """
        if not self.config.auto_renew or not self.use_letsencrypt:
            return False

        try:
            cron_content = """# FRP SSL Certificate Auto-Renewal
0 */12 * * * root certbot renew --quiet --post-hook "systemctl reload frps" 2>/dev/null
"""

            cron_file = Path('/etc/cron.d/frp-ssl-renewal')
            cron_file.write_text(cron_content)

            subprocess.run(['sudo', 'chmod', '644', str(cron_file)], check=True)

            return True

        except Exception:
            return False

    def get_certificate_status(self) -> CertificateStatus:
        """Get current certificate status.

        Returns:
            Current certificate status
        """
        if not self.enabled:
            return CertificateStatus.DISABLED

        if self.use_letsencrypt:
            return self._get_letsencrypt_status()
        else:
            return self._get_manual_cert_status()

    def _get_letsencrypt_status(self) -> CertificateStatus:
        """Get Let's Encrypt certificate status."""
        primary_domain = self.letsencrypt_domains[0] if self.letsencrypt_domains else None
        if not primary_domain:
            return CertificateStatus.ERROR

        cert_path = Path(f'/etc/letsencrypt/live/{primary_domain}/fullchain.pem')
        if not cert_path.exists():
            return CertificateStatus.MISSING

        return self._check_expiry_status()

    def _get_manual_cert_status(self) -> CertificateStatus:
        """Get manual certificate status."""
        if not self.check_certificate_files():
            return CertificateStatus.MISSING

        return self._check_expiry_status()

    def _check_expiry_status(self) -> CertificateStatus:
        """Check certificate expiry status."""
        expiry = self.get_certificate_expiry()
        if not expiry:
            return CertificateStatus.ERROR

        if expiry < datetime.now():
            return CertificateStatus.EXPIRED
        elif self.needs_renewal(expiry):
            return CertificateStatus.NEEDS_RENEWAL
        else:
            return CertificateStatus.VALID

    def get_certificate_info(self) -> dict[str, Any]:
        """Get comprehensive certificate information.

        Returns:
            Dictionary containing certificate status and details
        """
        status = self.get_certificate_status()
        info: dict[str, Any] = {
            'status': status.value,
            'enabled': self.enabled,
            'use_letsencrypt': self.use_letsencrypt,
        }

        if self.enabled:
            if self.use_letsencrypt:
                info.update({
                    'email': self.letsencrypt_email,
                    'domains': self.letsencrypt_domains,
                    'challenge_type': self.config.letsencrypt_challenge_type,
                    'auto_renew': self.config.auto_renew,
                })
            else:
                info.update({
                    'cert_file': self.cert_file,
                    'key_file': self.key_file,
                })

            expiry = self.get_certificate_expiry()
            if expiry:
                info.update({
                    'expiry_date': expiry.isoformat(),
                    'days_until_expiry': (expiry - datetime.now()).days,
                    'needs_renewal': self.needs_renewal(expiry),
                })

        return info
