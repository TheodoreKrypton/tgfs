import asyncio
import json
import logging
import os
from typing import Any, Dict

import asyncpg

from tgfs.config import get_config, MetadataType

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _clean_node(node: Any) -> Any:
    """
    Entfernt rekursiv alle Knoten mit {"deleted": true} aus dem
    TGFS-Metadatenbaum (Dictionary-Struktur).
    """
    if isinstance(node, dict):
        # Wenn dieser Knoten selbst als gelöscht markiert ist -> komplett entfernen
        if node.get("deleted") is True:
            return None

        # Wenn der Knoten Kinder hat, diese rekursiv säubern
        if "children" in node and isinstance(node["children"], list):
            new_children = []
            for child in node["children"]:
                cleaned = _clean_node(child)
                if cleaned is not None:
                    new_children.append(cleaned)
            node["children"] = new_children

        # Evtl. verschachtelte Strukturen weiter säubern
        for k, v in list(node.items()):
            if isinstance(v, (dict, list)):
                cleaned = _clean_node(v)
                node[k] = cleaned

        return node

    if isinstance(node, list):
        new_list = []
        for item in node:
            cleaned = _clean_node(item)
            if cleaned is not None:
                new_list.append(cleaned)
        return new_list

    # primitive Typen (str/int/...) unverändert lassen
    return node


async def cleanup_one_meta(dsn: str, name: str) -> None:
    logger.info("Cleaning metadata for name=%s", name)

    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            "SELECT data FROM tgfs_metadata WHERE name = $1",
            name,
        )
        if row is None:
            logger.info("No row found for name=%s, skipping", name)
            return

        data = row["data"]
        # asyncpg kann JSONB als dict oder str liefern
        if isinstance(data, str):
            data = json.loads(data)

        if not isinstance(data, dict):
            logger.warning("Unexpected data type for name=%s: %r", name, type(data))
            return

        # Wir erwarten, dass der Root-Baum unter "dir" hängt
        if "dir" not in data:
            logger.warning('No "dir" key in metadata for name=%s, skipping', name)
            return

        cleaned_dir = _clean_node(data["dir"])
        data["dir"] = cleaned_dir

        cleaned_json = json.dumps(data)
        await conn.execute(
            """
            UPDATE tgfs_metadata
            SET data = $2::jsonb,
                mtime = NOW()
            WHERE name = $1
            """,
            name,
            cleaned_json,
        )

        logger.info("Finished cleaning metadata for name=%s", name)
    finally:
        await conn.close()


async def main() -> None:
    # TGFS-Konfiguration laden (nutzt TGFS_CONFIG_FILE / TGFS_DATA_DIR)
    cfg = get_config()

    # Für alle Channels, die postgres als Metadaten-Backend nutzen
    tasks = []
    for _, meta_cfg in cfg.tgfs.metadata.items():
        if meta_cfg.type != MetadataType.POSTGRES:
            continue
        if meta_cfg.postgres is None:
            continue

        dsn = meta_cfg.postgres.dsn
        name = meta_cfg.name or "default"
        tasks.append(cleanup_one_meta(dsn, name))

    if not tasks:
        logger.info("No postgres metadata configurations found. Nothing to do.")
        return

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
