class AutomatorError(Exception):
    """Base exception for all application errors."""


class ConfigurationError(AutomatorError):
    """Raised when required configuration is missing or invalid."""


class DatabaseError(AutomatorError):
    """Raised when database operations fail."""


class EncryptionError(AutomatorError):
    """Raised when token encryption or decryption fails."""


class DriveSyncError(AutomatorError):
    """Raised when Google Drive sync operations fail."""


class DriveNotConfiguredError(DriveSyncError):
    """Raised when Drive credentials or folder IDs are not configured."""


class MediaPairIncompleteError(DriveSyncError):
    """Raised when video/caption pair is not yet complete."""


class FileNotStableError(DriveSyncError):
    """Raised when a Drive file has not passed settle-time validation."""


class TikTokAuthError(AutomatorError):
    """Raised when TikTok OAuth or token operations fail."""


class ProxyError(AutomatorError):
    """Raised when proxy operations fail."""


class AdminAuthError(AutomatorError):
    """Raised when admin authentication fails."""
