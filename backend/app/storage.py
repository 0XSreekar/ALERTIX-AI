"""Upload storage backends with content-hash deduplication."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import boto3
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings


@dataclass(frozen=True, slots=True)
class StoredUpload:
    sha256: str
    path: str
    size_bytes: int
    deduplicated: bool


class UploadStorage:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def store(
        self,
        session: AsyncSession,
        content: bytes,
        filename: str,
        user_id: str | None,
    ) -> StoredUpload:
        digest = hashlib.sha256(content).hexdigest()
        existing = (
            await session.execute(
                text("SELECT sha256, path, size_bytes FROM uploads WHERE sha256 = :sha256"),
                {"sha256": digest},
            )
        ).fetchone()
        if existing:
            return StoredUpload(
                sha256=existing.sha256,
                path=existing.path,
                size_bytes=int(existing.size_bytes),
                deduplicated=True,
            )

        suffix = Path(filename or "upload.bin").suffix.lower() or ".bin"
        object_name = f"{digest[:2]}/{digest}{suffix}"
        path = self._write(content, object_name)
        await session.execute(
            text("""
                INSERT INTO uploads (user_id, sha256, path, status, size_bytes, created_at)
                VALUES (:user_id, :sha256, :path, 'stored', :size_bytes, now())
                ON CONFLICT (sha256) DO NOTHING
            """),
            {"user_id": user_id, "sha256": digest, "path": path, "size_bytes": len(content)},
        )
        return StoredUpload(sha256=digest, path=path, size_bytes=len(content), deduplicated=False)

    def _write(self, content: bytes, object_name: str) -> str:
        backend = self.settings.storage_backend.lower()
        if backend == "local":
            base = Path(self.settings.local_upload_dir)
            target = base / object_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return str(target)
        if backend in {"r2", "s3"}:
            client = boto3.client(
                "s3",
                endpoint_url=self._endpoint_url() if backend == "r2" else None,
                aws_access_key_id=self.settings.r2_access_key_id or None,
                aws_secret_access_key=self.settings.r2_secret_access_key or None,
            )
            client.put_object(Bucket=self.settings.r2_bucket, Key=object_name, Body=content)
            if self.settings.r2_public_url:
                return f"{self.settings.r2_public_url.rstrip('/')}/{object_name}"
            return f"s3://{self.settings.r2_bucket}/{object_name}"
        raise ValueError(f"unsupported storage backend: {backend}")

    def _endpoint_url(self) -> str | None:
        if not self.settings.r2_account_id:
            return None
        return f"https://{self.settings.r2_account_id}.r2.cloudflarestorage.com"
