import json
import logging
from typing import Optional

import asyncpg

from tgfs.config import MetadataConfig, PostgresMetadataConfig
from tgfs.core.model import TGFSDirectory, TGFSMetadata
from tgfs.core.repository.interface import IMetaDataRepository
from tgfs.errors import MetadataNotInitialized

logger = logging.getLogger(__name__)


class PostgresMetadataRepository(IMetaDataRepository):
    """
    Speichert den kompletten TGFS-Metadatenbaum als JSON in Postgres.
    Die eigentlichen Datei-Inhalte bleiben in Telegram.
    """

    def __init__(self, meta_cfg: MetadataConfig):
        super().__init__()

        if meta_cfg.postgres is None:
            raise ValueError("Postgres config required for POSTGRES metadata type")

        # 'name' aus MetadataConfig -> Schlüssel in der Tabelle tgfs_metadata
        self._meta_name: str = meta_cfg.name
        self._pg_cfg: PostgresMetadataConfig = meta_cfg.postgres
        self._dsn: str = self._pg_cfg.dsn

    async def _ensure_schema(self, conn: asyncpg.Connection) -> None:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tgfs_metadata (
                name   TEXT PRIMARY KEY,
                data   JSONB NOT NULL,
                mtime  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

    async def push(self) -> None:
        """
        metadata -> JSON serialisieren und in tgfs_metadata upserten.
        Wird von MetaDataApi.push() aufgerufen.
        """
        if not self.metadata:
            raise MetadataNotInitialized()

        data = json.dumps(self.metadata.to_dict())

        conn: Optional[asyncpg.Connection] = None
        try:
            conn = await asyncpg.connect(self._dsn)
            await self._ensure_schema(conn)
            await conn.execute(
                """
                INSERT INTO tgfs_metadata (name, data)
                VALUES ($1, $2::jsonb)
                ON CONFLICT (name) DO UPDATE
                    SET data = EXCLUDED.data,
                        mtime = NOW();
                """,
                self._meta_name,
                data,
            )
        finally:
            if conn:
                await conn.close()

    async def get(self) -> TGFSMetadata:
        """
        Metadaten aus tgfs_metadata lesen.
        Falls nichts da ist, einen leeren Root-Baum zurückgeben.
        """
        conn: Optional[asyncpg.Connection] = None
        try:
            conn = await asyncpg.connect(self._dsn)
            await self._ensure_schema(conn)
            row = await conn.fetchrow(
                "SELECT data FROM tgfs_metadata WHERE name = $1",
                self._meta_name,
            )
            if row is None:
                logger.info("No metadata found in Postgres, creating empty root")
                return TGFSMetadata(dir=TGFSDirectory.root_dir())

            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)

            return TGFSMetadata.from_dict(data)
        finally:
            if conn:
                await conn.close()
