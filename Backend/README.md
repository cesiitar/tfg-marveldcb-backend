Backend API (FastAPI)
======================

Qué hace
--------
- API para recomendaciones de mazos (SVM), importación de cartas desde MarvelCDB y gestión de partidas/mazos.
- Base de datos SQLite por defecto (`marvel_cards.db`). En producción puede apuntar a un volumen persistente con `DB_PATH`.

Requisitos
----------
- Python 3.11+
- Dependencias: `pip install -r requirements.txt`

Config (entorno)
----------------
- `DB_PATH` (opcional): ruta absoluta a la base de datos. Si no se define, usa `marvel_cards.db` en el directorio actual.

Cómo correr en local
--------------------
```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Swagger: http://localhost:8000/docs

Scripts útiles
--------------
- `python init_all.py`            Inicializa/repuebla la base de datos (cartas/sets).
- `python reset_production_data.py` Limpia todas las partidas, mazos y borra el modelo SVM.
- `python update_existing_cards_marvelcdb_code.py` Rellena `marvelcdb_code` en cartas existentes.

Endpoints clave
---------------
- `POST /api/recommendations/deck`  Genera mazos (usa SVM, incluye fallback determinista).
- `POST /api/cards/check-missing`   Identifica cartas faltantes (por código MarvelCDB).
- `POST /api/cards/import-missing`  Importa cartas faltantes desde MarvelCDB o datos completos del frontend.
- `GET  /api/cards/marvelcdb-code/{code}` Busca carta por `marvelcdb_code`.

Despliegue rápido (Render)
--------------------------
- Build: `cd Backend && pip install -r requirements.txt`
- Start: `cd Backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- Volumen persistente: montar `/data` y definir `DB_PATH=/data/marvel_cards.db`
- Tras el primer deploy: `cd Backend && python init_all.py` para crear la BD en el volumen.

Notas
-----
- CORS: añade la URL del frontend en `main.py` (lista `allow_origins`).
- SQLite es válido al inicio; para más concurrencia, migrar a PostgreSQL.

