import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import asyncpg

from tgfs.config import MetadataConfig, PostgresMetadataConfig
from tgfs.core.model import TGFSDirectory, TGFSMetadata
from tgfs.core.repository.interface import IMetaDataRepository
from tgfs.errors import MetadataNotInitialized

logger = logging.getLogger(__name__)


@dataclass
class _FlatNode:
    """
    Interne Repräsentation eines Knotens (Datei oder Ordner),
    wie er in tgfs_node gespeichert wird.
    """

    id: Optional[int]
    parent_id: Optional[int]
    name: str
    is_dir: bool
    deleted: bool
    payload: Dict[str, Any]


class PostgresMetadataRepository(IMetaDataRepository):
    """
    Relationale Speicherung des TGFS-Metadatenbaums in Postgres.

    - Ein Eintrag in tgfs_namespace pro `metadata_cfg.name`
    - Eine Zeile in tgfs_node pro Datei/Ordner
    - Der eigentliche Baum wird beim get()/push() rekonstruiert
    """

    def __init__(self, meta_cfg: MetadataConfig):
        super().__init__()

        if meta_cfg.postgres is None:
            raise ValueError("Postgres config required for POSTGRES metadata type")

        self._meta_name: str = meta_cfg.name
        self._pg_cfg: PostgresMetadataConfig = meta_cfg.postgres
        self._dsn: str = self._pg_cfg.dsn

    # -------------------------------------------------------------------------
    # Low-level DB Helpers
    # -------------------------------------------------------------------------

    async def _get_conn(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._dsn)

    async def _ensure_schema(self, conn: asyncpg.Connection) -> None:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tgfs_namespace (
                id   SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
            """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tgfs_node (
                id            BIGSERIAL PRIMARY KEY,
                namespace_id  INTEGER NOT NULL REFERENCES tgfs_namespace(id) ON DELETE CASCADE,
                parent_id     BIGINT REFERENCES tgfs_node(id) ON DELETE CASCADE,
                name          TEXT NOT NULL,
                is_dir        BOOLEAN NOT NULL,
                deleted       BOOLEAN NOT NULL DEFAULT FALSE,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                payload       JSONB
            );
            """
        )

        await conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS tgfs_node_uq_path
            ON tgfs_node (namespace_id, parent_id, name);
            """
        )

    async def _get_or_create_namespace_id(
        self, conn: asyncpg.Connection
    ) -> int:
        row = await conn.fetchrow(
            "SELECT id FROM tgfs_namespace WHERE name = $1",
            self._meta_name,
        )
        if row:
            return int(row["id"])

        row = await conn.fetchrow(
            """
            INSERT INTO tgfs_namespace (name)
            VALUES ($1)
            RETURNING id
            """,
            self._meta_name,
        )
        return int(row["id"])

    # -------------------------------------------------------------------------
    # IMetaDataRepository API
    # -------------------------------------------------------------------------

    async def push(self) -> None:
        """
        Aktuelle self.metadata -> Tabellen tgfs_node schreiben.

        Vereinfachte Strategie:
          - alles für diesen Namespace löschen
          - kompletten Baum neu einfügen
        (immer noch viel effizienter als ein riesiger JSON-BLOB, und
         Postgres kann auf einzelnen Knoten indizieren)
        """
        if not self.metadata:
            raise MetadataNotInitialized()

        # Metadaten in ein python-dict abbilden
        root_dict = self.metadata.to_dict()

        conn: Optional[asyncpg.Connection] = None
        tx = None
        try:
            conn = await self._get_conn()
            await self._ensure_schema(conn)
            ns_id = await self._get_or_create_namespace_id(conn)

            tx = conn.transaction()
            await tx.start()

            # alle existierenden Knoten dieses Namespace löschen
            await conn.execute(
                "DELETE FROM tgfs_node WHERE namespace_id = $1",
                ns_id,
            )

            # Baum flatten & einfügen
            flat_nodes = self._flatten_metadata(root_dict)

            # erst root(s) ohne parent_id, dann Kinder
            # wir merken uns mapping: temp_id -> wirkliche DB-id
            id_map: Dict[int, int] = {}

            # 1. Nodes ohne parent_id (root)
            for temp_id, node in flat_nodes.items():
                if node.parent_id is None:
                    db_id = await self._insert_node(conn, ns_id, node, None)
                    id_map[temp_id] = db_id

            # 2. Nodes mit parent
            changed = True
            # simpler Algorithmus: so lange iterieren, bis alle parent_ids aufgelöst sind
            while changed:
                changed = False
                for temp_id, node in flat_nodes.items():
                    if temp_id in id_map:
                        continue
                    if node.parent_id is None:
                        continue
                    if node.parent_id in id_map:
                        parent_db_id = id_map[node.parent_id]
                        db_id = await self._insert_node(
                            conn, ns_id, node, parent_db_id
                        )
                        id_map[temp_id] = db_id
                        changed = True

            await tx.commit()
            tx = None
            logger.info(
                "PostgresMetadataRepository.push(): wrote %d nodes for namespace '%s'",
                len(flat_nodes),
                self._meta_name,
            )
        except Exception:
            if tx is not None:
                await tx.rollback()
            raise
        finally:
            if conn:
                await conn.close()

    async def get(self) -> TGFSMetadata:
        """
        Knoten aus tgfs_node laden und zu TGFSMetadata zusammenbauen.
        Wenn keine Daten existieren -> leeren Root-Baum zurückgeben.
        """
        conn: Optional[asyncpg.Connection] = None
        try:
            conn = await self._get_conn()
            await self._ensure_schema(conn)

            row = await conn.fetchrow(
                "SELECT id FROM tgfs_namespace WHERE name = $1",
                self._meta_name,
            )
            if not row:
                logger.info(
                    "No namespace '%s' found in Postgres, creating empty root",
                    self._meta_name,
                )
                return TGFSMetadata(dir=TGFSDirectory.root_dir())

            ns_id = int(row["id"])

            rows = await conn.fetch(
                """
                SELECT id, parent_id, name, is_dir, deleted, payload
                FROM tgfs_node
                WHERE namespace_id = $1
                ORDER BY id
                """,
                ns_id,
            )

            if not rows:
                logger.info(
                    "No nodes found in Postgres for namespace '%s', creating empty root",
                    self._meta_name,
                )
                return TGFSMetadata(dir=TGFSDirectory.root_dir())

            # zu flachem Knoten-Mapping konvertieren
            flat_nodes: Dict[int, _FlatNode] = {}
            for r in rows:
                node_id = int(r["id"])
                parent_id = int(r["parent_id"]) if r["parent_id"] is not None else None
                payload = r["payload"] or {}
                flat_nodes[node_id] = _FlatNode(
                    id=node_id,
                    parent_id=parent_id,
                    name=r["name"],
                    is_dir=bool(r["is_dir"]),
                    deleted=bool(r["deleted"]),
                    payload=dict(payload),
                )

            # Baum-Dict aus den flachen Nodes bauen
            root_dict = self._build_metadata_dict(flat_nodes)

            return TGFSMetadata.from_dict(root_dict)
        finally:
            if conn:
                await conn.close()

    # -------------------------------------------------------------------------
    # Flatten & Rebuild helpers
    # -------------------------------------------------------------------------

    def _flatten_metadata(self, root_dict: Dict[str, Any]) -> Dict[int, _FlatNode]:
        """
        Wandelt das TGFSMetadata-Dict in ein Mapping temp_id -> _FlatNode um.
        Da TGFSMetadata/TGFSDirectory-Struktur sich ändern kann, bauen wir das
        generisch – orientiert an der tatsächlichen Baumstruktur:

        Erwartet:
          root_dict = {
            "dir": { ... Directory-Struktur ... }
          }
        """

        flat: Dict[int, _FlatNode] = {}
        next_id = 1

        def alloc_id() -> int:
            nonlocal next_id
            i = next_id
            next_id += 1
            return i

        def visit_dir(node: Dict[str, Any], parent_temp_id: Optional[int]) -> int:
            """
            Einen Directory-Knoten verarbeiten und rekursiv seine Kinder.
            Rückgabe: temp_id dieses Verzeichnisses.
            """
            temp_id = alloc_id()

            name = node.get("name", "/")
            deleted = bool(node.get("deleted", False))

            # alles, was wir nicht direkt als Spalte ablegen, wandert in payload
            # => clean_dict = node ohne 'children', 'name', 'deleted'
            payload = {
                k: v
                for k, v in node.items()
                if k not in ("children", "name", "deleted")
            }

            flat[temp_id] = _FlatNode(
                id=None,
                parent_id=parent_temp_id,
                name=name,
                is_dir=True,
                deleted=deleted,
                payload=payload,
            )

            for child in node.get("children", []):
                # child kann Datei oder Unterverzeichnis sein
                if child.get("is_dir", False):
                    visit_dir(child, temp_id)
                else:
                    visit_file(child, temp_id)

            return temp_id

        def visit_file(node: Dict[str, Any], parent_temp_id: int) -> int:
            temp_id = alloc_id()

            name = node.get("name", "")
            deleted = bool(node.get("deleted", False))

            payload = {
                k: v
                for k, v in node.items()
                if k not in ("name", "deleted", "is_dir")
            }

            flat[temp_id] = _FlatNode(
                id=None,
                parent_id=parent_temp_id,
                name=name,
                is_dir=False,
                deleted=deleted,
                payload=payload,
            )
            return temp_id

        # root: TGFSMetadata hat root_dict["dir"] als Verzeichnisbaum
        dir_root = root_dict.get("dir")
        if not isinstance(dir_root, dict):
            raise ValueError("metadata root_dict['dir'] is not a dict")

        visit_dir(dir_root, parent_temp_id=None)
        return flat

    def _build_metadata_dict(
        self, nodes: Dict[int, _FlatNode]
    ) -> Dict[str, Any]:
        """
        Baut aus flachen Nodes wieder das Dict im Format von TGFSMetadata.to_dict().
        Das bedeutet: wir bauen eine Directory-Struktur unter key "dir".
        """

        # parent_id -> list of child_ids
        children_by_parent: Dict[Optional[int], List[int]] = {}
        for node_id, node in nodes.items():
            children_by_parent.setdefault(node.parent_id, []).append(node_id)

        # root-Knoten: diejenigen, deren parent_id None ist
        root_ids = children_by_parent.get(None, [])
        if len(root_ids) != 1:
            # zur Sicherheit: falls mehrere Roots, nehmen wir den mit dem kleinsten id
            logger.warning(
                "Expected exactly one root node, found %d; picking smallest id",
                len(root_ids),
            )
        root_id = sorted(root_ids)[0]

        def build_dir_dict(node_id: int) -> Dict[str, Any]:
            node = nodes[node_id]
            if not node.is_dir:
                raise ValueError("Root node must be a directory")

            # Basisdict aus payload zurückbauen
            d: Dict[str, Any] = dict(node.payload)
            d["name"] = node.name
            if node.deleted:
                d["deleted"] = True

            # Kinder
            child_ids = children_by_parent.get(node_id, [])
            children: List[Dict[str, Any]] = []
            for cid in child_ids:
                cnode = nodes[cid]
                if cnode.is_dir:
                    children.append(build_dir_dict(cid))
                else:
                    children.append(build_file_dict(cid))
            d["children"] = children
            d["is_dir"] = True
            return d

        def build_file_dict(node_id: int) -> Dict[str, Any]:
            node = nodes[node_id]
            if node.is_dir:
                raise ValueError("build_file_dict called on dir node")

            d: Dict[str, Any] = dict(node.payload)
            d["name"] = node.name
            d["is_dir"] = False
            if node.deleted:
                d["deleted"] = True
            return d

        dir_root_dict = build_dir_dict(root_id)
        return {"dir": dir_root_dict}

    async def _insert_node(
        self,
        conn: asyncpg.Connection,
        namespace_id: int,
        node: _FlatNode,
        parent_db_id: Optional[int],
    ) -> int:
        row = await conn.fetchrow(
            """
            INSERT INTO tgfs_node (
                namespace_id, parent_id, name,
                is_dir, deleted, payload, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW(), NOW())
            RETURNING id
            """,
            namespace_id,
            parent_db_id,
            node.name,
            node.is_dir,
            node.deleted,
            json.dumps(node.payload),
        )
        return int(row["id"])
