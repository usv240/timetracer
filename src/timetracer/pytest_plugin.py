"""
pytest plugin for Timetracer.

Provides fixtures and markers for cassette-based testing.

Usage:
    # In your test file
    @pytest.mark.cassette("my_cassette.json")
    def test_my_endpoint(client):
        response = client.get("/api/users")
        assert response.status_code == 200

    # Or use fixtures directly
    def test_with_fixture(timetracer_replay):
        with timetracer_replay("my_cassette.json"):
            # Code runs with mocked dependencies
            pass
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

import pytest

from timetracer.cassette import read_cassette, write_cassette
from timetracer.config import TraceConfig
from timetracer.context import reset_session, set_session
from timetracer.session import ReplaySession, TraceSession

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.nodes import Item


def pytest_configure(config: "Config") -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "cassette(path, mode='replay'): Load cassette for replay during test. "
        "mode can be 'replay', 'record', or 'new_episodes' (record if missing).",
    )


def pytest_collection_modifyitems(config: "Config", items: list["Item"]) -> None:
    """Process cassette markers on collected tests."""
    # This hook can be used for additional processing if needed
    pass


@pytest.fixture
def timetracer_cassette_dir(request: pytest.FixtureRequest) -> Path:
    """
    Fixture providing the cassette directory for tests.

    By default, uses ./cassettes relative to the test file.
    Can be overridden via pytest.ini or conftest.py.
    """
    # Try to get from pytest config
    cassette_dir = request.config.getini("timetracer_cassette_dir")
    if cassette_dir:
        return Path(cassette_dir)

    # Default: cassettes directory relative to test file
    test_path = Path(request.fspath)
    return test_path.parent / "cassettes"


@pytest.fixture
def timetracer_replay(
    timetracer_cassette_dir: Path,
) -> Generator[Any, None, None]:
    """
    Fixture providing a context manager for replay mode.

    Usage:
        def test_my_endpoint(timetracer_replay, client):
            with timetracer_replay("my_cassette.json"):
                response = client.get("/api/users")
                assert response.status_code == 200
    """
    @contextmanager
    def _replay_context(
        cassette_path: str | Path,
        strict: bool = False,
        plugins: list[str] | None = None,
    ) -> Generator[ReplaySession, None, None]:
        """
        Context manager for replay mode.

        Args:
            cassette_path: Path to cassette file (relative to cassette_dir or absolute).
            strict: If True, raises error on unmatched events.
            plugins: List of plugins to enable (e.g., ["httpx", "requests"]).

        Yields:
            The replay session for inspection.
        """
        # Resolve cassette path
        if not os.path.isabs(cassette_path):
            full_path = timetracer_cassette_dir / cassette_path
        else:
            full_path = Path(cassette_path)

        if not full_path.exists():
            raise FileNotFoundError(f"Cassette not found: {full_path}")

        # Enable plugins
        enabled_plugins = _enable_plugins(plugins or ["httpx", "requests"])

        try:
            # Load cassette
            cassette = read_cassette(str(full_path))

            # Create replay session
            config = TraceConfig(mode="replay", cassette_path=str(full_path))
            session = ReplaySession(
                cassette=cassette,
                cassette_path=str(full_path),
                strict=strict,
                config=config,
            )
            token = set_session(session)

            try:
                yield session
            finally:
                reset_session(token)

        finally:
            # Disable plugins
            _disable_plugins(enabled_plugins)

    yield _replay_context


@pytest.fixture
def timetracer_record(
    timetracer_cassette_dir: Path,
    tmp_path: Path,
) -> Generator[Any, None, None]:
    """
    Fixture providing a context manager for record mode.

    Usage:
        def test_record_new(timetracer_record, client):
            with timetracer_record("new_cassette.json") as session:
                response = client.get("/api/users")
            # Cassette is saved after context exits
    """
    @contextmanager
    def _record_context(
        cassette_name: str | None = None,
        plugins: list[str] | None = None,
        use_tmp: bool = False,
    ) -> Generator[TraceSession, None, None]:
        """
        Context manager for record mode.

        Args:
            cassette_name: Name for the cassette file.
            plugins: List of plugins to enable.
            use_tmp: If True, save to tmp directory (for testing).

        Yields:
            The trace session for inspection.
        """
        # Enable plugins
        enabled_plugins = _enable_plugins(plugins or ["httpx", "requests"])

        try:
            # Determine output directory
            if use_tmp:
                output_dir = tmp_path
            else:
                output_dir = timetracer_cassette_dir
                output_dir.mkdir(parents=True, exist_ok=True)

            # Create config
            config = TraceConfig(
                mode="record",
                cassette_dir=str(output_dir),
            )

            # Create session
            session = TraceSession(config=config)
            token = set_session(session)

            try:
                yield session
            finally:
                reset_session(token)

                # Write cassette
                session.finalize()
                cassette_path = write_cassette(session, config)
                session._cassette_path = cassette_path

        finally:
            _disable_plugins(enabled_plugins)

    yield _record_context


@pytest.fixture
def timetracer_auto(
    timetracer_cassette_dir: Path,
    request: pytest.FixtureRequest,
) -> Generator[Any, None, None]:
    """
    Fixture that automatically records or replays based on cassette existence.

    If cassette exists: replay mode
    If cassette doesn't exist: record mode

    Usage:
        def test_endpoint(timetracer_auto, client):
            with timetracer_auto("my_test.json"):
                response = client.get("/api/users")
    """
    @contextmanager
    def _auto_context(
        cassette_name: str,
        plugins: list[str] | None = None,
    ) -> Generator[TraceSession | ReplaySession, None, None]:
        """
        Auto-select record or replay based on cassette existence.
        """
        cassette_path = timetracer_cassette_dir / cassette_name

        # Enable plugins
        enabled_plugins = _enable_plugins(plugins or ["httpx", "requests"])

        try:
            if cassette_path.exists():
                # Replay mode
                cassette = read_cassette(str(cassette_path))
                config = TraceConfig(mode="replay", cassette_path=str(cassette_path))
                session = ReplaySession(
                    cassette=cassette,
                    cassette_path=str(cassette_path),
                    strict=False,
                    config=config,
                )
            else:
                # Record mode
                timetracer_cassette_dir.mkdir(parents=True, exist_ok=True)
                config = TraceConfig(
                    mode="record",
                    cassette_dir=str(timetracer_cassette_dir),
                )
                session = TraceSession(config=config)

            token = set_session(session)

            try:
                yield session
            finally:
                reset_session(token)

                # If recording, write cassette
                if isinstance(session, TraceSession):
                    session.finalize()
                    write_cassette(session, config)

        finally:
            _disable_plugins(enabled_plugins)

    yield _auto_context


def _enable_plugins(plugins: list[str]) -> list[str]:
    """Enable specified plugins and return list of enabled ones."""
    enabled = []
    for plugin in plugins:
        try:
            if plugin == "httpx":
                from timetracer.plugins import enable_httpx
                enable_httpx()
                enabled.append("httpx")
            elif plugin == "requests":
                from timetracer.plugins import enable_requests
                enable_requests()
                enabled.append("requests")
            elif plugin == "aiohttp":
                from timetracer.plugins import enable_aiohttp
                enable_aiohttp()
                enabled.append("aiohttp")
            elif plugin == "sqlalchemy":
                from timetracer.plugins import enable_sqlalchemy
                enable_sqlalchemy()
                enabled.append("sqlalchemy")
            elif plugin == "redis":
                from timetracer.plugins import enable_redis
                enable_redis()
                enabled.append("redis")
            elif plugin == "motor":
                from timetracer.plugins import enable_motor
                enable_motor()
                enabled.append("motor")
        except ImportError:
            pass  # Plugin not available
    return enabled


def _disable_plugins(plugins: list[str]) -> None:
    """Disable specified plugins."""
    for plugin in plugins:
        try:
            if plugin == "httpx":
                from timetracer.plugins import disable_httpx
                disable_httpx()
            elif plugin == "requests":
                from timetracer.plugins import disable_requests
                disable_requests()
            elif plugin == "aiohttp":
                from timetracer.plugins import disable_aiohttp
                disable_aiohttp()
            elif plugin == "sqlalchemy":
                from timetracer.plugins import disable_sqlalchemy
                disable_sqlalchemy()
            elif plugin == "redis":
                from timetracer.plugins import disable_redis
                disable_redis()
            elif plugin == "motor":
                from timetracer.plugins import disable_motor
                disable_motor()
        except (ImportError, Exception):
            pass


# Entry point for pytest plugin discovery
def pytest_addoption(parser: pytest.Parser) -> None:
    """Add pytest command-line options."""
    parser.addini(
        "timetracer_cassette_dir",
        "Default directory for Timetracer cassettes",
        default="cassettes",
    )
