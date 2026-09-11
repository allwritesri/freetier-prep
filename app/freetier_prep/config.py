"""Environment-driven settings for the freetier-prep control plane."""

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    mode: str = field(default_factory=lambda: os.environ.get("FTP_MODE", "dev"))
    var_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("FTP_VAR_DIR", APP_ROOT / "var"))
    )
    ttl_seconds: int = field(
        default_factory=lambda: int(os.environ.get("FTP_TTL_SECONDS", "3600"))
    )
    ttl_check_interval: float = field(
        default_factory=lambda: float(os.environ.get("FTP_TTL_CHECK_INTERVAL", "5"))
    )
    teardown_max_retries: int = field(
        default_factory=lambda: int(os.environ.get("FTP_TEARDOWN_RETRIES", "3"))
    )
    # own-account (real) mode
    project_id: str = field(
        default_factory=lambda: os.environ.get("FTP_PROJECT", "")
    )
    state_bucket: str = field(
        default_factory=lambda: os.environ.get("FTP_STATE_BUCKET", "")
    )
    terraform_bin: str = field(
        default_factory=lambda: os.environ.get("FTP_TERRAFORM_BIN", "terraform")
    )

    @property
    def tf_dir(self) -> Path:
        return self.var_dir / "tf"

    @property
    def db_path(self) -> Path:
        return self.var_dir / "manifest.db"

    @property
    def keys_dir(self) -> Path:
        return self.var_dir / "keys"

    @property
    def out_dir(self) -> Path:
        return self.var_dir / "out"

    def ensure_dirs(self) -> None:
        self.var_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
