"""
S3 storage backend for Timetracer cassettes.

Enables storing and retrieving cassettes from AWS S3 or S3-compatible storage.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


@dataclass
class S3Config:
    """Configuration for S3 storage."""
    bucket: str
    prefix: str = "cassettes"
    region: str | None = None
    endpoint_url: str | None = None  # For S3-compatible (MinIO, LocalStack)
    access_key: str | None = None
    secret_key: str | None = None

    @classmethod
    def from_env(cls) -> "S3Config":
        """
        Load S3 configuration from environment variables.

        Environment variables:
            TIMETRACER_S3_BUCKET: S3 bucket name (required)
            TIMETRACER_S3_PREFIX: Key prefix (default: "cassettes")
            TIMETRACER_S3_REGION: AWS region
            TIMETRACER_S3_ENDPOINT: Custom endpoint URL (for MinIO, etc.)
            AWS_ACCESS_KEY_ID: AWS access key
            AWS_SECRET_ACCESS_KEY: AWS secret key
        """
        bucket = os.environ.get("TIMETRACER_S3_BUCKET")
        if not bucket:
            raise ValueError("TIMETRACER_S3_BUCKET environment variable is required")

        return cls(
            bucket=bucket,
            prefix=os.environ.get("TIMETRACER_S3_PREFIX", "cassettes"),
            region=os.environ.get("TIMETRACER_S3_REGION") or os.environ.get("AWS_REGION"),
            endpoint_url=os.environ.get("TIMETRACER_S3_ENDPOINT"),
            access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
            secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )


class S3Store:
    """
    S3 storage backend for cassettes.

    Usage:
        from timetracer.storage.s3 import S3Store, S3Config

        config = S3Config(bucket="my-cassettes", prefix="api-traces")
        store = S3Store(config)

        # Upload a local cassette
        store.upload("./cassettes/2026-01-15/POST__checkout__a91c.json")

        # Download a cassette
        store.download("2026-01-15/POST__checkout__a91c.json", "./local_copy.json")

        # List cassettes
        for key in store.list():
            print(key)
    """

    def __init__(self, config: S3Config) -> None:
        """
        Initialize S3 store.

        Args:
            config: S3 configuration.
        """
        self.config = config
        self._client: "S3Client | None" = None

    @property
    def client(self) -> "S3Client":
        """Get or create S3 client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> "S3Client":
        """Create boto3 S3 client."""
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. "
                "Install with: pip install timetracer[s3]"
            )

        kwargs: dict[str, Any] = {}

        if self.config.region:
            kwargs["region_name"] = self.config.region

        if self.config.endpoint_url:
            kwargs["endpoint_url"] = self.config.endpoint_url

        if self.config.access_key and self.config.secret_key:
            kwargs["aws_access_key_id"] = self.config.access_key
            kwargs["aws_secret_access_key"] = self.config.secret_key

        return boto3.client("s3", **kwargs)

    def _make_key(self, path: str) -> str:
        """Create S3 key from path."""
        # Normalize path
        path = path.replace("\\", "/")

        # Remove leading slashes
        path = path.lstrip("/")

        # Add prefix
        if self.config.prefix:
            return f"{self.config.prefix.rstrip('/')}/{path}"
        return path

    def upload(
        self,
        local_path: str,
        remote_key: str | None = None,
    ) -> str:
        """
        Upload a cassette to S3.

        Args:
            local_path: Path to local cassette file.
            remote_key: Optional S3 key. If None, uses filename.

        Returns:
            S3 key where cassette was uploaded.
        """
        local_path = Path(local_path)

        if not local_path.exists():
            raise FileNotFoundError(f"Cassette not found: {local_path}")

        # Determine key
        if remote_key is None:
            # Use date/filename structure
            remote_key = local_path.name
            if local_path.parent.name and local_path.parent.name != ".":
                remote_key = f"{local_path.parent.name}/{local_path.name}"

        s3_key = self._make_key(remote_key)

        # Upload
        self.client.upload_file(
            str(local_path),
            self.config.bucket,
            s3_key,
            ExtraArgs={"ContentType": "application/json"},
        )

        return s3_key

    def download(
        self,
        remote_key: str,
        local_path: str,
    ) -> str:
        """
        Download a cassette from S3.

        Args:
            remote_key: S3 key (without prefix).
            local_path: Where to save locally.

        Returns:
            Local path where file was saved.
        """
        s3_key = self._make_key(remote_key)
        local_path = Path(local_path)

        # Create parent directory
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download
        self.client.download_file(
            self.config.bucket,
            s3_key,
            str(local_path),
        )

        return str(local_path)

    def read(self, remote_key: str) -> dict[str, Any]:
        """
        Read a cassette directly from S3.

        Args:
            remote_key: S3 key (without prefix).

        Returns:
            Cassette data as dict.
        """
        s3_key = self._make_key(remote_key)

        response = self.client.get_object(
            Bucket=self.config.bucket,
            Key=s3_key,
        )

        body = response["Body"].read()
        return json.loads(body.decode("utf-8"))

    def write(self, remote_key: str, data: dict[str, Any]) -> str:
        """
        Write cassette data directly to S3.

        Args:
            remote_key: S3 key (without prefix).
            data: Cassette data as dict.

        Returns:
            S3 key where cassette was written.
        """
        s3_key = self._make_key(remote_key)

        body = json.dumps(data, indent=2).encode("utf-8")

        self.client.put_object(
            Bucket=self.config.bucket,
            Key=s3_key,
            Body=body,
            ContentType="application/json",
        )

        return s3_key

    def list(
        self,
        prefix: str = "",
        limit: int = 100,
    ) -> Iterator[str]:
        """
        List cassettes in S3.

        Args:
            prefix: Additional prefix filter.
            limit: Maximum number of results.

        Yields:
            S3 keys (relative to store prefix).
        """
        s3_prefix = self._make_key(prefix)

        paginator = self.client.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=self.config.bucket,
            Prefix=s3_prefix,
            PaginationConfig={"MaxItems": limit},
        )

        base_prefix = self.config.prefix.rstrip("/") + "/" if self.config.prefix else ""

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                # Remove base prefix for relative key
                if key.startswith(base_prefix):
                    key = key[len(base_prefix):]
                yield key

    def delete(self, remote_key: str) -> None:
        """
        Delete a cassette from S3.

        Args:
            remote_key: S3 key (without prefix).
        """
        s3_key = self._make_key(remote_key)

        self.client.delete_object(
            Bucket=self.config.bucket,
            Key=s3_key,
        )

    def exists(self, remote_key: str) -> bool:
        """
        Check if a cassette exists in S3.

        Args:
            remote_key: S3 key (without prefix).

        Returns:
            True if cassette exists.
        """
        s3_key = self._make_key(remote_key)

        try:
            self.client.head_object(
                Bucket=self.config.bucket,
                Key=s3_key,
            )
            return True
        except Exception:
            return False

    def sync_upload(
        self,
        local_dir: str,
        remote_prefix: str = "",
    ) -> list[str]:
        """
        Sync local cassettes to S3.

        Args:
            local_dir: Local directory with cassettes.
            remote_prefix: Optional prefix in S3.

        Returns:
            List of uploaded S3 keys.
        """
        local_dir = Path(local_dir)
        uploaded = []

        for json_file in local_dir.rglob("*.json"):
            relative = json_file.relative_to(local_dir)
            remote_key = f"{remote_prefix}/{relative}" if remote_prefix else str(relative)
            remote_key = remote_key.replace("\\", "/")

            key = self.upload(str(json_file), remote_key)
            uploaded.append(key)

        return uploaded

    def sync_download(
        self,
        local_dir: str,
        remote_prefix: str = "",
    ) -> list[str]:
        """
        Sync S3 cassettes to local directory.

        Args:
            local_dir: Local directory to download to.
            remote_prefix: Optional prefix filter in S3.

        Returns:
            List of downloaded local paths.
        """
        local_dir = Path(local_dir)
        downloaded = []

        for remote_key in self.list(prefix=remote_prefix, limit=1000):
            local_path = local_dir / remote_key
            self.download(remote_key, str(local_path))
            downloaded.append(str(local_path))

        return downloaded
