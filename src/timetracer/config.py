"""
TraceConfig - Central configuration for Timetracer.

This is the main configuration object that controls all behavior.
It can be created programmatically or loaded from environment variables.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

from timetracer.constants import (
    CapturePolicy,
    CompressionType,
    Defaults,
    EnvVars,
    TraceMode,
)
from timetracer.exceptions import ConfigurationError


def _parse_bool(value: str) -> bool:
    """Parse a boolean from environment variable."""
    return value.lower() in ("true", "1", "yes", "on")


def _parse_csv(value: str) -> list[str]:
    """Parse a comma-separated list from environment variable."""
    if not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class TraceConfig:
    """
    Configuration for Timetracer.

    This is the single source of truth for all runtime configuration.
    Create via constructor or use from_env() to load from environment.

    Priority order:
    1. Explicit constructor arguments
    2. Environment variables (via from_env())
    3. Default values

    Example:
        # Explicit configuration
        cfg = TraceConfig(mode=TraceMode.RECORD, cassette_dir="./recordings")

        # Load from environment
        cfg = TraceConfig.from_env()

        # Mixed: defaults + env overrides
        cfg = TraceConfig(service_name="my-api").with_env_overrides()
    """

    # Core settings
    mode: TraceMode = Defaults.MODE
    service_name: str = Defaults.SERVICE_NAME
    env: str = Defaults.ENV

    # Cassette storage
    cassette_dir: str = Defaults.CASSETTE_DIR
    cassette_path: str | None = None  # Specific cassette for replay

    # Capture control
    capture: list[str] = field(default_factory=lambda: ["http"])
    sample_rate: float = Defaults.SAMPLE_RATE
    errors_only: bool = Defaults.ERRORS_ONLY
    exclude_paths: list[str] = field(default_factory=lambda: list(Defaults.EXCLUDE_PATHS))

    # Body capture policies
    max_body_kb: int = Defaults.MAX_BODY_KB
    store_request_body: CapturePolicy = Defaults.STORE_REQUEST_BODY
    store_response_body: CapturePolicy = Defaults.STORE_RESPONSE_BODY

    # Replay settings
    strict_replay: bool = Defaults.STRICT_REPLAY

    # Hybrid replay - selective mocking
    # If mock_plugins is empty, all plugins are mocked (default behavior)
    # If mock_plugins is set, only those plugins are mocked
    # Plugins in live_plugins are never mocked (kept live)
    mock_plugins: list[str] = field(default_factory=list)
    live_plugins: list[str] = field(default_factory=list)

    # Logging
    log_level: str = Defaults.LOG_LEVEL

    # Compression - gzip cassettes for smaller storage
    compression: CompressionType = Defaults.COMPRESSION

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Convert string mode to enum if needed
        if isinstance(self.mode, str):
            try:
                self.mode = TraceMode(self.mode.lower())
            except ValueError:
                raise ConfigurationError(
                    f"Invalid mode: {self.mode}. Must be one of: {[m.value for m in TraceMode]}"
                )

        # Convert string policies to enum if needed
        if isinstance(self.store_request_body, str):
            try:
                self.store_request_body = CapturePolicy(self.store_request_body.lower())
            except ValueError:
                raise ConfigurationError(
                    f"Invalid store_request_body: {self.store_request_body}"
                )

        if isinstance(self.store_response_body, str):
            try:
                self.store_response_body = CapturePolicy(self.store_response_body.lower())
            except ValueError:
                raise ConfigurationError(
                    f"Invalid store_response_body: {self.store_response_body}"
                )

        # Validate sample_rate
        if not 0.0 <= self.sample_rate <= 1.0:
            raise ConfigurationError(
                f"sample_rate must be between 0.0 and 1.0, got {self.sample_rate}"
            )

        # Validate max_body_kb
        if self.max_body_kb < 0:
            raise ConfigurationError(
                f"max_body_kb must be non-negative, got {self.max_body_kb}"
            )

        # Convert string compression to enum if needed
        if isinstance(self.compression, str):
            try:
                self.compression = CompressionType(self.compression.lower())
            except ValueError:
                raise ConfigurationError(
                    f"Invalid compression: {self.compression}. "
                    f"Must be one of: {[c.value for c in CompressionType]}"
                )

    @classmethod
    def from_env(cls) -> TraceConfig:
        """
        Create configuration from environment variables.

        All TIMETRACER_* environment variables are read and used.
        Missing variables use defaults.
        """
        kwargs: dict = {}

        # Mode
        if mode := os.environ.get(EnvVars.MODE):
            kwargs["mode"] = mode

        # Service/env
        if service := os.environ.get(EnvVars.SERVICE):
            kwargs["service_name"] = service
        if env := os.environ.get(EnvVars.ENV):
            kwargs["env"] = env

        # Cassette paths
        if cassette_dir := os.environ.get(EnvVars.DIR):
            kwargs["cassette_dir"] = cassette_dir
        if cassette_path := os.environ.get(EnvVars.CASSETTE):
            kwargs["cassette_path"] = cassette_path

        # Capture settings
        if capture := os.environ.get(EnvVars.CAPTURE):
            kwargs["capture"] = _parse_csv(capture)
        if sample_rate := os.environ.get(EnvVars.SAMPLE_RATE):
            try:
                kwargs["sample_rate"] = float(sample_rate)
            except ValueError:
                raise ConfigurationError(f"Invalid TIMETRACER_SAMPLE_RATE: {sample_rate}")
        if errors_only := os.environ.get(EnvVars.ERRORS_ONLY):
            kwargs["errors_only"] = _parse_bool(errors_only)
        if exclude_paths := os.environ.get(EnvVars.EXCLUDE_PATHS):
            kwargs["exclude_paths"] = _parse_csv(exclude_paths)

        # Body policies
        if max_body := os.environ.get(EnvVars.MAX_BODY_KB):
            try:
                kwargs["max_body_kb"] = int(max_body)
            except ValueError:
                raise ConfigurationError(f"Invalid TIMETRACER_MAX_BODY_KB: {max_body}")
        if store_req := os.environ.get(EnvVars.STORE_REQ_BODY):
            kwargs["store_request_body"] = store_req
        if store_res := os.environ.get(EnvVars.STORE_RES_BODY):
            kwargs["store_response_body"] = store_res

        # Replay
        if strict := os.environ.get(EnvVars.STRICT_REPLAY):
            kwargs["strict_replay"] = _parse_bool(strict)

        # Logging
        if log_level := os.environ.get(EnvVars.LOG_LEVEL):
            kwargs["log_level"] = log_level.lower()

        # Hybrid replay
        if mock_plugins := os.environ.get(EnvVars.MOCK_PLUGINS):
            kwargs["mock_plugins"] = _parse_csv(mock_plugins)
        if live_plugins := os.environ.get(EnvVars.LIVE_PLUGINS):
            kwargs["live_plugins"] = _parse_csv(live_plugins)

        # Compression
        if compression := os.environ.get(EnvVars.COMPRESSION):
            kwargs["compression"] = compression

        return cls(**kwargs)

    def with_env_overrides(self) -> TraceConfig:
        """
        Return a new config with environment variables applied as overrides.

        This allows setting base config in code and overriding via env.
        """
        env_config = TraceConfig.from_env()

        # Create new config, preferring env values over current where set
        return TraceConfig(
            mode=env_config.mode if os.environ.get(EnvVars.MODE) else self.mode,
            service_name=env_config.service_name if os.environ.get(EnvVars.SERVICE) else self.service_name,
            env=env_config.env if os.environ.get(EnvVars.ENV) else self.env,
            cassette_dir=env_config.cassette_dir if os.environ.get(EnvVars.DIR) else self.cassette_dir,
            cassette_path=env_config.cassette_path if os.environ.get(EnvVars.CASSETTE) else self.cassette_path,
            capture=env_config.capture if os.environ.get(EnvVars.CAPTURE) else self.capture,
            sample_rate=env_config.sample_rate if os.environ.get(EnvVars.SAMPLE_RATE) else self.sample_rate,
            errors_only=env_config.errors_only if os.environ.get(EnvVars.ERRORS_ONLY) else self.errors_only,
            exclude_paths=env_config.exclude_paths if os.environ.get(EnvVars.EXCLUDE_PATHS) else self.exclude_paths,
            max_body_kb=env_config.max_body_kb if os.environ.get(EnvVars.MAX_BODY_KB) else self.max_body_kb,
            store_request_body=env_config.store_request_body if os.environ.get(EnvVars.STORE_REQ_BODY) else self.store_request_body,
            store_response_body=env_config.store_response_body if os.environ.get(EnvVars.STORE_RES_BODY) else self.store_response_body,
            strict_replay=env_config.strict_replay if os.environ.get(EnvVars.STRICT_REPLAY) else self.strict_replay,
            log_level=env_config.log_level if os.environ.get(EnvVars.LOG_LEVEL) else self.log_level,
            mock_plugins=env_config.mock_plugins if os.environ.get(EnvVars.MOCK_PLUGINS) else self.mock_plugins,
            live_plugins=env_config.live_plugins if os.environ.get(EnvVars.LIVE_PLUGINS) else self.live_plugins,
            compression=env_config.compression if os.environ.get(EnvVars.COMPRESSION) else self.compression,
        )

    def should_trace(self, path: str) -> bool:
        """
        Determine if a request path should be traced.

        Returns False for excluded paths.
        """
        # Normalize path
        path = path.split("?")[0]  # Remove query string

        # Check exclusions
        for excluded in self.exclude_paths:
            if path == excluded or path.startswith(excluded + "/"):
                return False

        return True

    def should_sample(self) -> bool:
        """
        Determine if this request should be sampled for recording.

        Uses sample_rate for probabilistic sampling.
        """
        if self.sample_rate >= 1.0:
            return True
        if self.sample_rate <= 0.0:
            return False

        import random
        return random.random() < self.sample_rate

    @property
    def is_record_mode(self) -> bool:
        """Check if in record mode."""
        return self.mode == TraceMode.RECORD

    @property
    def is_replay_mode(self) -> bool:
        """Check if in replay mode."""
        return self.mode == TraceMode.REPLAY

    @property
    def is_enabled(self) -> bool:
        """Check if timetrace is enabled (not OFF)."""
        return self.mode != TraceMode.OFF

    def get_python_version(self) -> str:
        """Get current Python version string."""
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def should_mock_plugin(self, plugin_name: str) -> bool:
        """
        Determine if a plugin should be mocked during replay.

        This enables hybrid replay where some dependencies are mocked
        and others are kept live (e.g., mock Stripe but keep DB live).

        Args:
            plugin_name: The name of the plugin (e.g., "http", "db", "redis")

        Returns:
            True if the plugin should be mocked, False if it should stay live.
        """
        # Live plugins are never mocked
        if self.live_plugins and plugin_name in self.live_plugins:
            return False

        # If mock_plugins is specified, only those are mocked
        if self.mock_plugins:
            return plugin_name in self.mock_plugins

        # Default: mock everything
        return True
