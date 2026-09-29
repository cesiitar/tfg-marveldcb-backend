"""
Sincronización incremental del catálogo con MarvelCDB.

Añade los sets (packs) y las cartas que falten en la base de datos, con el mismo
formato que usa init_all.py. Es segura para producción:
  - Solo hace INSERT OR IGNORE: nunca borra ni modifica filas existentes.
  - No toca usuarios, mazos, partidas, favoritos ni comentarios.
  - Si MarvelCDB no responde, no cambia nada.

Se lanza en segundo plano al arrancar la API (como mucho una vez cada 24 h) y
también se puede ejecutar a mano:  python catalog_sync.py [--force]
"""
import sys
import threading
import time
import zlib
from collections import Counter
from datetime import datetime, timezone

import requests

from db_utils import get_db_connection

MARVELCDB_API = "https://marvelcdb.com/api/public"
SYNC_INTERVAL_SECONDS = 24 * 60 * 60
# Tipos de carta de encuentro que se importan aunque compartan código con cartas de jugador
ENCOUNTER_TYPES = ['villain', 'main_scheme', 'side_scheme', 'minion', 'attachment', 'treachery', 'environment']

_lock = threading.Lock()


def _new_card_id(code: str, taken: set) -> int:
    """Id para una carta nueva: su código numérico si está libre; si no, un id estable
    (crc32) por encima de 2.000.000, fuera de los rangos que ya usa la BD."""
    if code.isdigit() and int(code) not in taken:
        return int(code)
    candidate = 2_000_000 + zlib.crc32(code.encode()) % 1_000_000
    while candidate in taken:
        candidate += 1
    return candidate


def _key(name, pack_name) -> tuple:
    return ((name or '').strip().lower(), (pack_name or '').strip().lower())


def _deck_limit(value):
    return int(value) if str(value if value is not None else '').isdigit() else None


def _ensure_meta_table(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')


def _last_sync(cursor):
    cursor.execute("SELECT value FROM app_meta WHERE key = 'catalog_last_sync'")
    row = cursor.fetchone()
    if not row:
        return None
    try:
        return datetime.fromisoformat(row[0])
    except ValueError:
        return None


def _insert_missing(cursor, table: str, columns: set, row: dict):
    """INSERT OR IGNORE solo con las columnas que existen en esta BD (las BD antiguas tienen menos)."""
    data = {k: v for k, v in row.items() if k in columns}
    names = ', '.join(data)
    marks = ', '.join('?' for _ in data)
    cursor.execute(f"INSERT OR IGNORE INTO {table} ({names}) VALUES ({marks})", tuple(data.values()))


def _fetch(path: str):
    response = requests.get(f"{MARVELCDB_API}{path}", timeout=60)
    response.raise_for_status()
    return response.json()


def sync_catalog(force: bool = False) -> dict:
    """Inserta los sets y cartas que falten. Devuelve un resumen de lo añadido."""
    if not _lock.acquire(blocking=False):
        return {"status": "running"}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        _ensure_meta_table(cursor)
        conn.commit()

        last = _last_sync(cursor)
        if not force and last and (datetime.now(timezone.utc) - last).total_seconds() < SYNC_INTERVAL_SECONDS:
            conn.close()
            return {"status": "skipped", "last_sync": last.isoformat()}

        # Descargar todo antes de escribir: si algo falla, la BD queda intacta.
        packs = _fetch("/packs/")
        player_cards = _fetch("/cards/")
        encounter_cards = _fetch("/cards/?encounter=true")

        set_columns = {r[1] for r in cursor.execute("PRAGMA table_info(card_sets)").fetchall()}
        card_columns = {r[1] for r in cursor.execute("PRAGMA table_info(cards)").fetchall()}

        cursor.execute("SELECT COUNT(*) FROM card_sets")
        sets_before = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cards")
        cards_before = cursor.fetchone()[0]

        # 1) Sets que falten (mismo formato que init_all.import_sets)
        existing_set_codes = {r[0] for r in cursor.execute("SELECT code FROM card_sets").fetchall()}
        for pack in packs:
            if pack.get('code', '') in existing_set_codes:
                continue
            set_id = pack.get('id') or 2_000_000 + zlib.crc32(pack.get('code', '').encode()) % 1_000_000
            _insert_missing(cursor, 'card_sets', set_columns, {
                'id': set_id,
                'name': pack.get('name', ''),
                'code': pack.get('code', ''),
                'card_count': pack.get('total', 0),
            })

        # Qué cartas hay ya. No se puede confiar en el id: las BD existentes mezclan
        # esquemas (init_all usaba hash(), que cambia en cada ejecución). Una carta se
        # da por existente si coincide su código de MarvelCDB o su nombre + pack
        # (contando repeticiones, p. ej. las fases de un villano con el mismo nombre).
        taken_ids = {r[0] for r in cursor.execute("SELECT id FROM cards").fetchall()}
        existing_codes = set()
        if 'marvelcdb_code' in card_columns:
            existing_codes = {r[0] for r in cursor.execute(
                "SELECT marvelcdb_code FROM cards WHERE marvelcdb_code IS NOT NULL AND marvelcdb_code != ''").fetchall()}
        remaining = Counter(_key(r[0], r[1]) for r in cursor.execute("SELECT name, pack_name FROM cards").fetchall())
        seen_codes = set()

        def add_card(code: str, row: dict):
            if not code or code in seen_codes:
                return
            seen_codes.add(code)
            key = _key(row.get('name'), row.get('pack_name'))
            if code in existing_codes or remaining[key] > 0:
                if remaining[key] > 0:
                    remaining[key] -= 1
                return
            row['id'] = _new_card_id(code, taken_ids)
            taken_ids.add(row['id'])
            _insert_missing(cursor, 'cards', card_columns, row)

        # 2) Cartas de jugador (mismo formato que init_all.import_cards)
        for card in player_cards:
            code = str(card.get('code', ''))
            add_card(code, {
                'name': card.get('name', ''),
                'aspect': card.get('faction_code', ''),
                'type': card.get('type_code', ''),
                'cost': int(card.get('cost') or 0),
                'set_name': card.get('pack_name', ''),
                'set_code': card.get('pack_code', ''),
                'pack_code': card.get('pack_code', ''),
                'pack_name': card.get('pack_name', ''),
                'faction_code': card.get('faction_code', ''),
                'type_code': card.get('type_code', ''),
                'card_set': card.get('card_set_name'),
                'quantity': card.get('quantity', 1),
                'deck_limit': _deck_limit(card.get('deck_limit')),
                'marvelcdb_code': code,
            })

        # 3) Villanos y cartas de encuentro (mismo formato que
        #    init_all.import_villains_and_encounters, pero sin reemplazar nada)
        player_codes = {str(c.get('code', '')) for c in player_cards}
        for card in encounter_cards:
            code = str(card.get('code', ''))
            if code in player_codes and card.get('type_code', '') not in ENCOUNTER_TYPES:
                continue
            pack_name = card.get('pack_name', '')
            add_card(code, {
                'name': card.get('name', ''),
                'cost': card.get('cost', 0),
                'type': card.get('type_name', '').lower(),
                'aspect': card.get('faction_name', '').lower(),
                'pack_name': pack_name,
                'quantity': card.get('quantity', 1),
                'deck_limit': card.get('deck_limit', None),
                'card_set': card.get('card_set_name', pack_name),
                'set_code': {'Core Set': 'core', 'The Green Goblin': 'gg', 'Wrecking Crew': 'wc'}.get(pack_name),
                'marvelcdb_code': code,
            })

        cursor.execute('''
            INSERT OR REPLACE INTO app_meta (key, value) VALUES ('catalog_last_sync', ?)
        ''', (datetime.now(timezone.utc).isoformat(),))
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM card_sets")
        sets_after = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cards")
        cards_after = cursor.fetchone()[0]
        conn.close()

        result = {
            "status": "ok",
            "sets_added": sets_after - sets_before,
            "cards_added": cards_after - cards_before,
        }
        print(f"[catalog-sync] Catalogo sincronizado con MarvelCDB: {result}", flush=True)
        return result
    except Exception as e:  # nunca debe tumbar la API
        print(f"[catalog-sync] No se pudo sincronizar el catalogo: {e}", flush=True)
        return {"status": "error", "error": str(e)}
    finally:
        _lock.release()


def start_background_sync(delay_seconds: int = 20):
    """Lanza la sincronización en un hilo aparte, sin retrasar el arranque de la API."""
    def run():
        time.sleep(delay_seconds)
        sync_catalog()

    threading.Thread(target=run, name="catalog-sync", daemon=True).start()


if __name__ == "__main__":
    print(sync_catalog(force="--force" in sys.argv))
