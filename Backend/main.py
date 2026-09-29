from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import json
import re
from typing import List, Dict, Optional
import sys
import os
import requests

# Añadir path para importar módulos ML
sys.path.append(os.path.dirname(__file__))
from ml.api.recommendations import router as recommendations_router
from ml.models.train_model import train_villain_recommender

app = FastAPI(title="MarvelCDB API", version="1.0.0")

# Registrar rutas de recomendaciones
app.include_router(recommendations_router, prefix="/api", tags=["recommendations"])

# Inicializar tablas al arrancar la aplicación
@app.on_event("startup")
async def startup_event():
    """Inicializar tablas necesarias al arrancar la aplicación"""
    init_users_table()
    ensure_decks_columns()
    ensure_game_configurations_table()
    ensure_user_favorites_table()
    ensure_deck_comments_table()
    # Añade en segundo plano los sets y cartas nuevos de MarvelCDB (solo inserta, nunca borra)
    start_background_sync()

def get_user_by_auth0_id(auth0_id: str):
    """Helper function to get user by Auth0 ID"""
    if not auth0_id:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, auth0_id, email, name, picture_url, created_at
        FROM users 
        WHERE auth0_id = ?
    ''', (auth0_id,))
    
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row:
        return None
    
    return {
        "id": user_row["id"],
        "auth0_id": user_row["auth0_id"],
        "email": user_row["email"],
        "name": user_row["name"],
        "picture_url": user_row["picture_url"],
        "created_at": user_row["created_at"]
    }

# Configurar CORS para permitir requests desde el frontend separado
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend local
        "http://localhost:5173",  # Vite dev server
        "https://www.aiforgedecks.com",  # Dominio propio (principal)
        "https://aiforgedecks.com",  # Dominio propio sin www (redirige a www)
        "https://aiforge-decks.vercel.app",  # Dominio anterior en Vercel
        "https://frontend-sigma-dusky-21.vercel.app",  # Frontend en producción (Vercel)
        "https://cesiitar.github.io",  # GitHub Pages (si planeas usar GitHub Pages)
        "https://tfg-marveldcb-frontend.vercel.app",  # Vercel (ejemplo)
        "https://tfg-marveldcb-frontend.netlify.app"   # Netlify (ejemplo)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar utilidades centralizadas de base de datos
from db_utils import get_db_connection, get_db_path, verify_tables_exist
from catalog_sync import start_background_sync

def init_users_table():
    """Inicializar tabla de usuarios si no existe"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auth0_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            picture_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# =============================================================================
# UTILIDADES DE ESQUEMA (decks)
# =============================================================================
def ensure_decks_columns():
    """Garantiza que la tabla decks tenga las columnas requeridas por los endpoints."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(decks)")
    columns = [column[1] for column in cursor.fetchall()]

    altered = False

    # hero_name para el héroe del mazo
    if 'hero_name' not in columns:
        cursor.execute('ALTER TABLE decks ADD COLUMN hero_name TEXT')
        altered = True

    # aspect para el aspecto del mazo
    if 'aspect' not in columns:
        cursor.execute('ALTER TABLE decks ADD COLUMN aspect TEXT')
        altered = True

    # is_public para visibilidad (por compatibilidad)
    if 'is_public' not in columns:
        cursor.execute('ALTER TABLE decks ADD COLUMN is_public INTEGER DEFAULT 1')
        altered = True

    # description para descripción del mazo (opcional)
    if 'description' not in columns:
        cursor.execute('ALTER TABLE decks ADD COLUMN description TEXT')
        altered = True

    # hero_id para vincular con la tabla de héroes por ID (más seguro que hero_name)
    if 'hero_id' not in columns:
        cursor.execute('ALTER TABLE decks ADD COLUMN hero_id INTEGER')
        altered = True

    if altered:
        conn.commit()
    conn.close()

# =============================================================================
# UTILIDADES DE ESQUEMA (game_configurations)
# =============================================================================
def ensure_game_configurations_table():
    """Crear la tabla game_configurations si no existe."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Crear la tabla game_configurations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_configurations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,        -- ID numérico del usuario (de la tabla users)
            deck_id INTEGER NOT NULL,        -- ID del mazo
            difficulty TEXT NOT NULL,        -- "normal" o "expert"
            villain_id INTEGER NOT NULL,      -- ID del villano (referencia a cards.id)
            result TEXT NOT NULL,            -- "win" o "loss"
            played_at TEXT NOT NULL,         -- Timestamp ISO de cuándo se jugó
            
            FOREIGN KEY (villain_id) REFERENCES cards(id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,  -- Si se elimina un usuario, se eliminan sus partidas
            FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE  -- Si se elimina un mazo, se eliminan sus partidas
        )
    ''')
    
    # Verificar columnas existentes para migraciones
    cursor.execute("PRAGMA table_info(game_configurations)")
    columns_info = cursor.fetchall()
    columns = [col[1] for col in columns_info]
    column_types = {col[1]: col[2] for col in columns_info}  # nombre: tipo
    
    # Migrar villain (nombre) a villain_id (ID) si es necesario
    if 'villain' in columns and 'villain_id' not in columns:
        # Migrar datos de villain (nombre) a villain_id (ID)
        print("🔄 Migrando datos de villain (nombre) a villain_id (ID)...")
        
        # Añadir columna villain_id
        cursor.execute('ALTER TABLE game_configurations ADD COLUMN villain_id INTEGER')
        
        # Migrar datos existentes
        cursor.execute('SELECT id, villain FROM game_configurations WHERE villain IS NOT NULL')
        existing_configs = cursor.fetchall()
        
        migrated_count = 0
        for config_id, villain_name in existing_configs:
            # Buscar el ID del villano por nombre
            cursor.execute('''
                SELECT id FROM cards 
                WHERE type = 'villain' AND LOWER(card_set) = LOWER(?)
                LIMIT 1
            ''', (villain_name,))
            
            villain_row = cursor.fetchone()
            if villain_row:
                villain_id = villain_row[0]
                cursor.execute('''
                    UPDATE game_configurations 
                    SET villain_id = ? 
                    WHERE id = ?
                ''', (villain_id, config_id))
                migrated_count += 1
            else:
                print(f"⚠️ No se encontró villano: {villain_name}")
        
        # Eliminar columna villain (nombre)
        cursor.execute('ALTER TABLE game_configurations DROP COLUMN villain')
        
        print(f"✅ Migrados {migrated_count} registros de game_configurations")
    
    # Migrar user_id de TEXT a INTEGER si es necesario
    if 'user_id' in columns and column_types.get('user_id', '').upper() == 'TEXT':
        print("🔄 Migrando user_id de TEXT a INTEGER...")
        
        # Crear tabla temporal con estructura correcta
        cursor.execute('''
            CREATE TABLE game_configurations_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                deck_id INTEGER NOT NULL,
                difficulty TEXT NOT NULL,
                villain_id INTEGER NOT NULL,
                result TEXT NOT NULL,
                played_at TEXT NOT NULL,
                FOREIGN KEY (villain_id) REFERENCES cards(id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
            )
        ''')
        
        # Migrar datos: convertir user_id TEXT a INTEGER
        # Si user_id es un número como texto, lo convertimos
        # Si es auth0_id, necesitamos buscar el ID numérico del usuario
        cursor.execute('SELECT id, user_id, deck_id, difficulty, villain_id, result, played_at FROM game_configurations')
        existing_configs = cursor.fetchall()
        
        migrated_count = 0
        for config in existing_configs:
            config_id, old_user_id, deck_id, difficulty, villain_id, result, played_at = config
            
            # Intentar convertir directamente si es un número
            try:
                new_user_id = int(old_user_id)
            except (ValueError, TypeError):
                # Si no es un número, buscar por auth0_id
                cursor.execute('SELECT id FROM users WHERE auth0_id = ? LIMIT 1', (old_user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    new_user_id = user_row[0]
                else:
                    print(f"⚠️ No se encontró usuario con auth0_id: {old_user_id}, saltando registro {config_id}")
                    continue
            
            cursor.execute('''
                INSERT INTO game_configurations_new 
                (id, user_id, deck_id, difficulty, villain_id, result, played_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (config_id, new_user_id, deck_id, difficulty, villain_id, result, played_at))
            migrated_count += 1
        
        # Reemplazar tabla antigua por la nueva
        cursor.execute('DROP TABLE game_configurations')
        cursor.execute('ALTER TABLE game_configurations_new RENAME TO game_configurations')
        
        print(f"✅ Migrados {migrated_count} registros de game_configurations (user_id TEXT -> INTEGER)")
    
    conn.commit()
    conn.close()

# =============================================================================
# UTILIDADES DE ESQUEMA (user_favorites)
# =============================================================================
def ensure_user_favorites_table():
    """Crear la tabla user_favorites si no existe."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Crear la tabla user_favorites
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,        -- ID numérico del usuario (de la tabla users)
            deck_id INTEGER NOT NULL,         -- ID del mazo favorito
            created_at TEXT DEFAULT (datetime('now', 'localtime')),  -- Cuándo se marcó como favorito
            
            -- Restricciones importantes:
            UNIQUE(user_id, deck_id),         -- Evitar duplicados
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,  -- Si se elimina un usuario, se eliminan sus favoritos
            FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE  -- Si se elimina un mazo, se eliminan sus favoritos
        )
    ''')
    
    # Verificar si user_id es TEXT y migrar a INTEGER si es necesario
    cursor.execute("PRAGMA table_info(user_favorites)")
    columns_info = cursor.fetchall()
    column_types = {col[1]: col[2] for col in columns_info}  # nombre: tipo
    
    if 'user_id' in column_types and column_types.get('user_id', '').upper() == 'TEXT':
        print("🔄 Migrando user_favorites.user_id de TEXT a INTEGER...")
        
        # Crear tabla temporal con estructura correcta
        cursor.execute('''
            CREATE TABLE user_favorites_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                deck_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(user_id, deck_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
            )
        ''')
        
        # Migrar datos
        cursor.execute('SELECT id, user_id, deck_id, created_at FROM user_favorites')
        existing_favorites = cursor.fetchall()
        
        migrated_count = 0
        for fav in existing_favorites:
            fav_id, old_user_id, deck_id, created_at = fav
            
            # Intentar convertir directamente si es un número
            try:
                new_user_id = int(old_user_id)
            except (ValueError, TypeError):
                # Si no es un número, buscar por auth0_id
                cursor.execute('SELECT id FROM users WHERE auth0_id = ? LIMIT 1', (old_user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    new_user_id = user_row[0]
                else:
                    print(f"⚠️ No se encontró usuario con auth0_id: {old_user_id}, saltando favorito {fav_id}")
                    continue
            
            cursor.execute('''
                INSERT INTO user_favorites_new (id, user_id, deck_id, created_at)
                VALUES (?, ?, ?, ?)
            ''', (fav_id, new_user_id, deck_id, created_at))
            migrated_count += 1
        
        # Reemplazar tabla antigua por la nueva
        cursor.execute('DROP TABLE user_favorites')
        cursor.execute('ALTER TABLE user_favorites_new RENAME TO user_favorites')
        
        print(f"✅ Migrados {migrated_count} registros de user_favorites (user_id TEXT -> INTEGER)")
    
    conn.commit()
    conn.close()

# =============================================================================
# UTILIDADES DE ESQUEMA (deck_comments)
# =============================================================================
def ensure_deck_comments_table():
    """Crear la tabla deck_comments si no existe."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Crear la tabla deck_comments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deck_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            auth0_id TEXT NOT NULL,
            comment_text TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT,
            
            FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
        )
    ''')
    
    # Crear índices para búsquedas rápidas
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_deck_comments_deck_id ON deck_comments(deck_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_deck_comments_auth0_id ON deck_comments(auth0_id)
    ''')
    
    conn.commit()
    conn.close()

# =============================================================================
# UTILIDADES DE ESQUEMA (cards)
# =============================================================================
def ensure_cards_columns():
    """Garantiza que la tabla cards tenga todas las columnas requeridas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(cards)")
    columns = [column[1] for column in cursor.fetchall()]

    altered = False
    required_columns = {
        'deck_limit': 'INTEGER',
        'health': 'INTEGER',
        'attack': 'INTEGER',
        'threat': 'INTEGER',
        'traits': 'TEXT',
        'text': 'TEXT',
        'is_unique': 'BOOLEAN DEFAULT 0',
        'marvelcdb_code': 'VARCHAR(20)'  # Código de MarvelCDB (ej: "01001", "01002")
    }
    
    for col_name, col_type in required_columns.items():
        if col_name not in columns:
            cursor.execute(f'ALTER TABLE cards ADD COLUMN {col_name} {col_type}')
            altered = True
            print(f"✅ Añadida columna {col_name} a la tabla cards")
    
    # Crear índice único en marvelcdb_code si no existe
    if 'marvelcdb_code' in columns or altered:
        try:
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_marvelcdb_code ON cards(marvelcdb_code)')
            conn.commit()
        except:
            pass  # El índice ya existe o hay duplicados, no es crítico

    if altered:
        conn.commit()
    conn.close()

@app.get("/")
async def root():
    return {"message": "MarvelCDB API está funcionando!"}

# =============================================================================
# ENDPOINTS DE SINCRONIZACIÓN DE USUARIOS
# =============================================================================

@app.post("/api/sync-user")
async def sync_user(user_data: dict):
    """Sincronizar usuario de Auth0 con la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        auth0_id = user_data.get("auth0_id")
        email = user_data.get("email")
        name = user_data.get("name")
        picture = user_data.get("picture")
        
        if not auth0_id or not email:
            raise HTTPException(
                status_code=400, 
                detail="auth0_id y email son requeridos"
            )
        
        # Verificar si el usuario ya existe
        cursor.execute('''
            SELECT id FROM users 
            WHERE auth0_id = ? OR email = ?
        ''', (auth0_id, email))
        
        existing_user = cursor.fetchone()
        
        if existing_user:
            return {
                "message": "Usuario ya existe",
                "user": {
                    "id": existing_user["id"],
                    "auth0_id": auth0_id,
                    "email": email
                }
            }
        
        # Crear usuario en la base de datos
        cursor.execute('''
            INSERT INTO users (auth0_id, email, name, picture_url)
            VALUES (?, ?, ?, ?)
        ''', (auth0_id, email, name, picture))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        return {
            "message": "Usuario creado exitosamente",
            "user": {
                "id": user_id,
                "auth0_id": auth0_id,
                "email": email,
                "name": name,
                "picture_url": picture
            }
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error sincronizando usuario: {str(e)}")
    
    finally:
        conn.close()

@app.get("/api/sets")
async def get_sets():
    """Obtener todos los sets de cartas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, code, card_count 
        FROM card_sets 
        ORDER BY id
    ''')
    
    sets = []
    for row in cursor.fetchall():
        set_name = row["name"]
        
        # Contar cartas reales usando el código del set
        cursor.execute('SELECT COUNT(*) FROM cards WHERE set_code = ?', (row["code"],))
        real_card_count = cursor.fetchone()[0]
        
        # Solo incluir sets que tengan cartas
        if real_card_count > 0:
            sets.append({
                "id": row["id"],
                "name": row["name"],
                "cardCount": real_card_count
            })
    
    conn.close()
    return {"sets": sets}

@app.get("/api/sets/{set_id}/cards")
async def get_cards_by_set(
    set_id: int,
    search: Optional[str] = None,
    sort_by: Optional[str] = None
):
    """Obtener todas las cartas de un set específico"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Primero obtener el nombre del set
    cursor.execute('SELECT name FROM card_sets WHERE id = ?', (set_id,))
    set_row = cursor.fetchone()
    
    if not set_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Set no encontrado")
    
    set_name = set_row["name"]
    
    # Obtener el código del set
    cursor.execute('SELECT code FROM card_sets WHERE id = ?', (set_id,))
    set_code_row = cursor.fetchone()
    
    if not set_code_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Código del set no encontrado")
    
    set_code = set_code_row["code"]
    
    # Construir query con filtros y ordenamiento
    query = '''
        SELECT id, name, aspect, type, cost, set_name
        FROM cards 
        WHERE set_code = ?
    '''
    params = [set_code]
    
    # Añadir filtro de búsqueda si se proporciona (startsWith en lugar de includes)
    if search:
        query += ' AND name LIKE ?'
        params.append(f'{search}%')
    
    # Añadir ordenamiento
    if sort_by == 'clase':
        query += ' ORDER BY aspect, type, cost, name'
    elif sort_by == 'nombre':
        # Ordenar por nombre pero manteniendo agrupación por clase
        query += ' ORDER BY aspect, name'
    elif sort_by == 'fuerza':
        query += ' ORDER BY cost DESC, name'
    elif sort_by == 'tipo':
        # Ordenamiento especial para héroes: primero héroes, luego por cost
        query += ' ORDER BY CASE WHEN type = "hero" THEN 0 ELSE 1 END, type, cost, name'
    else:
        # Ordenamiento por defecto: héroes primero, luego por tipo
        query += ' ORDER BY CASE WHEN type = "hero" THEN 0 ELSE 1 END, type, cost, name'
    
    cursor.execute(query, params)
    
    cards = []
    for row in cursor.fetchall():
        card = {
            "id": row["id"],  # ← CAMPO ID AÑADIDO
            "name": row["name"],
            "clase": row["aspect"],
            "type": row["type"],
            "cost": row["cost"],
            "set": row["set_name"]  # Usar el nombre completo del set
        }
        cards.append(card)
    
    conn.close()
    return {"set": set_name, "cards": cards}

@app.get("/api/heroes")
async def get_heroes():
    """Obtener todos los héroes disponibles para crear mazos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener todos los héroes con su información completa
    cursor.execute('''
        SELECT id, name, pack_name, cost, card_set
        FROM cards 
        WHERE type = 'hero'
        ORDER BY name, CASE WHEN pack_name = 'Core Set' THEN 0 ELSE 1 END, pack_name
    ''')
    
    heroes = []
    hero_names = {}  # Para detectar duplicados
    
    for row in cursor.fetchall():
        hero_name = row["name"]
        pack_name = row["pack_name"]
        card_set = row["card_set"]
        
        # Detectar héroes duplicados por nombre
        if hero_name in hero_names:
            hero_names[hero_name] += 1
            # Si hay duplicados, usar formato "Nombre (Alter Ego)" del card_set
            if card_set and card_set != hero_name and "(" in card_set and ")" in card_set:
                # Extraer el alter ego del card_set (ej: "Black Panther (Shuri)" -> "Shuri")
                alter_ego = card_set.split("(")[1].split(")")[0]
                display_name = f"{hero_name} ({alter_ego})"
            else:
                display_name = f"{hero_name} ({pack_name})"
        else:
            hero_names[hero_name] = 1
            # Si es único, usar solo el nombre
            display_name = hero_name
        
        heroes.append({
            "id": row["id"],
            "name": display_name,
            "hero_name": hero_name,
            "pack_name": pack_name,
            "cost": row["cost"]
        })
    
    conn.close()
    return heroes  # Devolver array directo como espera el frontend

@app.get("/api/villains")
async def get_villains():
    """Obtener todos los nombres únicos de villanos por nombre de carta (sin duplicados)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener nombres únicos de villanos usando el nombre de la carta ('name').
    # Se hace TRIM para evitar duplicados por espacios.
    cursor.execute('''
        SELECT DISTINCT
               TRIM(name) AS name
        FROM cards
        WHERE type = 'villain'
        ORDER BY name
    ''')
    
    villains = []
    for row in cursor.fetchall():
        villains.append(row["name"])
    
    conn.close()
    return villains

@app.get("/api/villains/with-ids")
async def get_villains_with_ids():
    """Obtener todos los villanos únicos con sus IDs para el frontend (un nombre por villano)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener villanos únicos con ID y nombre usando el nombre de la carta ('name').
    # Se agrupa por una versión normalizada del nombre (lower + trim) para evitar duplicados
    # cuando solo cambian mayúsculas/minúsculas o espacios, y se toma el MIN(id) como
    # identificador representativo.
    cursor.execute('''
        SELECT
            MIN(id) AS id,
            TRIM(name) AS name
        FROM cards
        WHERE type = 'villain'
        GROUP BY LOWER(TRIM(name))
        ORDER BY name
    ''')
    
    villains = []
    for row in cursor.fetchall():
        villains.append({
            "id": row["id"],
            "name": row["name"]
        })
    
    conn.close()
    return villains

@app.get("/api/villains/{villain_name}/id")
async def get_villain_id(villain_name: str):
    """Obtener el ID de un villano por su nombre"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar el villano por nombre (case-insensitive) y tomar el primer ID
    cursor.execute('''
        SELECT MIN(id) FROM cards 
        WHERE type = 'villain' AND LOWER(card_set) = LOWER(?)
    ''', (villain_name,))
    
    villain_row = cursor.fetchone()
    conn.close()
    
    if not villain_row or villain_row[0] is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villain not found"
        )
    
    return {"villain_id": villain_row[0]}

@app.get("/api/heroes/{hero_id}/cards")
async def get_hero_cards(hero_id: int):
    """Obtener las cartas específicas del héroe usando su ID"""
    ensure_cards_columns()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar el héroe por ID para obtener su card_set y pack_name
    cursor.execute('''
        SELECT card_set, pack_name FROM cards 
        WHERE id = ? AND type = 'hero'
    ''', (hero_id,))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Hero not found")
    
    hero_card_set = result[0]
    hero_pack_name = result[1]
    
    # Buscar las cartas que pertenecen al héroe específico dentro del pack correcto
    # EXCLUIR la carta del héroe (type = 'hero') y solo incluir cartas del aspecto 'hero'
    cursor.execute('''
        SELECT id, name, cost, type, aspect, card_set, quantity, deck_limit
        FROM cards 
        WHERE card_set = ? 
        AND pack_name = ?
        AND type != 'hero' 
        AND LOWER(type) != 'alter_ego' 
        AND LOWER(type) != 'alter-ego'
        AND aspect = 'hero'
        ORDER BY type, cost, name
    ''', (hero_card_set, hero_pack_name))
    
    cards = []
    for row in cursor.fetchall():
        cards.append({
            "id": row["id"],  # ← ID único de la carta
            "name": row["name"],
            "cost": row["cost"],
            "type": row["type"],
            "clase": row["aspect"],
            "set": row["card_set"],
            "quantity": row["quantity"],  # ← IMPORTANTE: cantidad de la carta
            "max_quantity": (row["deck_limit"] if row["deck_limit"] is not None else 3)
        })
    
    conn.close()
    return cards  # Devolver array directo como espera el frontend

@app.get("/api/cards/marvelcdb-code/{code}")
async def get_card_by_marvelcdb_code(code: str):
    """
    Busca una carta por su código de MarvelCDB (code, no id).
    El frontend usa el campo 'code' de MarvelCDB como identificador único.
    
    Estrategia de búsqueda:
    1. Buscar por marvelcdb_code (si existe la columna)
    2. Si no encuentra, buscar por id (convertir code a int, ej: "01001" -> 1001)
    3. Si aún no encuentra, buscar por id como string (para códigos con letras como "50035a")
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si la columna marvelcdb_code existe
    cursor.execute("PRAGMA table_info(cards)")
    columns = [column[1] for column in cursor.fetchall()]
    
    row = None
    
    if 'marvelcdb_code' in columns:
        # 1. Buscar por marvelcdb_code (método preferido)
        cursor.execute('''
            SELECT id, name, aspect, type, cost, set_name, deck_limit, marvelcdb_code
            FROM cards 
            WHERE marvelcdb_code = ?
        ''', (code,))
        row = cursor.fetchone()
    
    # 2. Si no se encontró, intentar buscar por id (convertir code a int)
    if not row:
        try:
            # Intentar convertir el code a int (ej: "01001" -> 1001, "12013" -> 12013)
            # Esto funciona porque en init_all.py convertimos code a int para el id
            if code.isdigit():
                card_id = int(code)
            else:
                # Si tiene letras (ej: "50035a"), intentar extraer el número
                import re
                numbers = re.findall(r'\d+', code)
                if numbers:
                    card_id = int(numbers[0])
                else:
                    card_id = abs(hash(code)) % 1000000
        except:
            card_id = abs(hash(code)) % 1000000
        
        cursor.execute('''
            SELECT id, name, aspect, type, cost, set_name, deck_limit
            FROM cards 
            WHERE id = ?
        ''', (card_id,))
        row = cursor.fetchone()
    
    # 3. Si aún no se encontró y el code tiene letras, buscar por id como string
    if not row and not code.isdigit():
        cursor.execute('''
            SELECT id, name, aspect, type, cost, set_name, deck_limit
            FROM cards 
            WHERE CAST(id AS TEXT) = ?
        ''', (code,))
        row = cursor.fetchone()
    
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Carta no encontrada con código: {code}"
        )
    
    # Construir respuesta según si tiene marvelcdb_code o no
    if 'marvelcdb_code' in columns and len(row) > 7:
        card = {
            "id": row[0],
            "name": row[1],
            "clase": row[2],  # aspect = clase
            "type": row[3],
            "cost": row[4],
            "set": row[5],
            "max_quantity": (row[6] if row[6] is not None else 3),
            "marvelcdb_code": row[7] if row[7] else code  # Si es NULL, usar el code buscado
        }
    else:
        card = {
            "id": row[0],
            "name": row[1],
            "clase": row[2],  # aspect = clase
            "type": row[3],
            "cost": row[4],
            "set": row[5],
            "max_quantity": (row[6] if row[6] is not None else 3),
            "marvelcdb_code": code  # Añadir el code buscado para que el frontend lo tenga
        }
    
    # Devolver en el formato esperado por el frontend
    return {"card": card}

@app.get("/api/cards/aspect/{aspect}")
async def get_cards_by_aspect(aspect: str):
    """Obtener todas las cartas de un aspecto específico"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar cartas del aspecto especificado
    cursor.execute('''
        SELECT id, name, cost, type, aspect, pack_name, quantity, deck_limit
        FROM cards 
        WHERE aspect = ?
        ORDER BY type, cost, name
    ''', (aspect,))
    
    cards = []
    for row in cursor.fetchall():
        cards.append({
            "id": row["id"],  # ← CAMPO ID AÑADIDO
            "name": row["name"],
            "cost": row["cost"],
            "type": row["type"],
            "clase": row["aspect"],
            "set": row["pack_name"],
            "quantity": row["quantity"],
            "max_quantity": (row["deck_limit"] if row["deck_limit"] is not None else 3)
        })
    
    conn.close()
    return cards  # Devolver array directo como espera el frontend

@app.get("/api/cards")
async def get_all_cards():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, aspect, type, cost, set_name, deck_limit
        FROM cards 
        ORDER BY set_name, type, cost, name
    ''')
    
    cards = []
    for row in cursor.fetchall():
        card = {
            "id": row["id"],
            "name": row["name"],
            "clase": row["aspect"],
            "type": row["type"],
            "cost": row["cost"],
            "set": row["set_name"],  # Ahora contiene el nombre completo
            "max_quantity": (row["deck_limit"] if row["deck_limit"] is not None else 3)
        }
        cards.append(card)
    
    conn.close()
    return {"cards": cards}

@app.get("/api/cards/search")
async def search_cards(
    name: Optional[str] = None,
    aspect: Optional[str] = None,
    type: Optional[str] = None,
    cost: Optional[int] = None,
    set_name: Optional[str] = None
):
    """Buscar cartas con filtros"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Construir query dinámicamente
    query = '''
        SELECT id, name, aspect, type, cost, set_name
        FROM cards 
        WHERE 1=1
    '''
    params = []
    
    if name:
        query += ' AND name LIKE ?'
        params.append(f'{name}%')
    
    if aspect:
        query += ' AND aspect = ?'
        params.append(aspect)
    
    if type:
        query += ' AND type = ?'
        params.append(type)
    
    if cost is not None:
        query += ' AND cost = ?'
        params.append(cost)
    
    if set_name:
        query += ' AND set_name = ?'
        params.append(set_name)
    
    query += ' ORDER BY set_name, type, cost, name'
    
    cursor.execute(query, params)
    
    cards = []
    for row in cursor.fetchall():
        card = {
            "id": row["id"],
            "name": row["name"],
            "clase": row["aspect"],
            "type": row["type"],
            "cost": row["cost"],
            "set": row["set_name"]  # Ahora contiene el nombre completo
        }
        cards.append(card)
    
    conn.close()
    return {"cards": cards}


@app.get("/api/decks")
async def get_public_decks():
    """Obtener todos los mazos públicos"""
    ensure_decks_columns()
    ensure_user_favorites_table()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si existe la columna user_id
    cursor.execute("PRAGMA table_info(decks)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Incluir mazos legacy donde is_public pueda ser NULL y también mazos de usuario
    # Mostrar todo lo que sea público (1) o legacy (NULL). Todos los mazos creados por usuarios se guardan como públicos.
    # Incluir conteo de favoritos usando LEFT JOIN con user_favorites
    if 'user_id' in columns:
        cursor.execute('''
            SELECT d.id, d.name, d.description, d.hero_name, d.hero_id, d.aspect, d.cards, d.created_at, d.user_id,
                   COALESCE(COUNT(uf.id), 0) as favorite_count
            FROM decks d
            LEFT JOIN user_favorites uf ON d.id = uf.deck_id
            WHERE d.is_public = 1 OR d.is_public IS NULL
            GROUP BY d.id, d.name, d.description, d.hero_name, d.hero_id, d.aspect, d.cards, d.created_at, d.user_id
            ORDER BY d.created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT d.id, d.name, d.description, d.hero_name, d.aspect, d.cards, d.created_at,
                   COALESCE(COUNT(uf.id), 0) as favorite_count
            FROM decks d
            LEFT JOIN user_favorites uf ON d.id = uf.deck_id
            WHERE d.is_public = 1 OR d.is_public IS NULL
            GROUP BY d.id, d.name, d.description, d.hero_name, d.aspect, d.cards, d.created_at
            ORDER BY d.created_at DESC
        ''')
    
    decks = []
    for row in cursor.fetchall():
        try:
            raw_cards = json.loads(row["cards"]) if row["cards"] else []
        except json.JSONDecodeError:
            raw_cards = []
        # Normalizar a formato { card_id, card_name, card_set, quantity, type, clase }
        cards_data = []
        for c in raw_cards:
            card_id = c.get("card_id")
            card_name = c.get("card_name") or c.get("name") or c.get("code")
            card_set = c.get("card_set", "")
            
            # Si tenemos card_id, buscar por ID (más preciso)
            if card_id:
                cursor.execute('SELECT type, aspect, pack_name, card_set FROM cards WHERE id = ?', (card_id,))
                card_info = cursor.fetchone()
                
                if card_info:
                    card_data = {
                        "card_id": card_id,
                        "card_name": card_name,
                        "card_set": card_info[3] or card_set,
                        "quantity": c.get("quantity", 1),
                        "type": card_info[0],
                        "clase": card_info[1],
                        "set": card_info[2] or "Unknown"
                    }
                else:
                    # Fallback si no encuentra por ID
                    card_data = {
                        "card_id": card_id,
                        "card_name": card_name,
                        "card_set": card_set,
                        "quantity": c.get("quantity", 1)
                    }
            else:
                # Fallback: buscar por nombre y set
                cursor.execute('SELECT id, type, aspect, pack_name, card_set FROM cards WHERE name = ? AND (card_set = ? OR pack_name = ?)', (card_name, card_set, card_set))
                card_info = cursor.fetchone()
                
                if card_info:
                    card_data = {
                        "card_id": card_info[0],  # ID de la BD
                        "card_name": card_name,
                        "card_set": card_info[4] or card_set,
                        "quantity": c.get("quantity", 1),
                        "type": card_info[1],
                        "clase": card_info[2],
                        "set": card_info[3] or "Unknown"
                    }
                else:
                    # Último fallback
                    card_data = {
                        "card_name": card_name,
                        "card_set": card_set,
                        "quantity": c.get("quantity", 1)
                    }
            
            cards_data.append(card_data)
        
        # Obtener nombre del creador si existe user_id
        creator_name = None
        if 'user_id' in columns:
            try:
                uid = row["user_id"]
                if uid:
                    # Ahora user_id es el ID numérico, no el auth0_id
                    cursor.execute('SELECT name FROM users WHERE id = ?', (uid,))
                    user_row = cursor.fetchone()
                    if user_row and user_row[0]:
                        creator_name = user_row[0]
            except Exception:
                creator_name = None

        deck = {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "hero_name": row["hero_name"],
            "hero_id": row["hero_id"],  # Campo opcional
            "aspect": row["aspect"],
            "cards": cards_data,
            "created_at": row["created_at"],
            "creator_name": creator_name,
            "favorite_count": row["favorite_count"]
        }
        
        # Añadir información del usuario si existe
        if 'user_id' in columns:
            try:
                if row["user_id"] is not None:
                    deck["userId"] = row["user_id"]
            except KeyError:
                pass
        
        decks.append(deck)
    
    conn.close()
    return {"decks": decks}

@app.post("/api/decks", status_code=201)
async def create_deck(deck_data: dict, request: Request):
    """Crear un nuevo mazo. La autenticación es opcional: sin login se crea un mazo público sin dueño (importación)."""
    try:
        ensure_decks_columns()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Debug log
        print(f"🔍 POST /api/decks - Auth0_ID recibido: {auth0_id or '(sin autenticación)'}")
        print(f"📦 Datos recibidos: {deck_data}")
        
        user = None
        if auth0_id:
            user = get_user_by_auth0_id(auth0_id)
            if user:
                print(f"✅ Usuario encontrado: ID={user['id']}, Name={user['name']}")
            else:
                print(f"⚠️ Auth0_ID presente pero usuario no encontrado en BD; se crea mazo sin dueño")
        
        # Validar datos requeridos
        if not deck_data.get('name') or not deck_data.get('hero_name') or not deck_data.get('cards') or not deck_data.get('aspect'):
            print(f"❌ Campos faltantes - name: {deck_data.get('name')}, hero_name: {deck_data.get('hero_name')}, cards: {deck_data.get('cards')}, aspect: {deck_data.get('aspect')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: name, hero_name, aspect, cards"
            )
        # Validar aspect permitido
        aspect = deck_data.get('aspect')
        allowed_aspects = {"aggression", "justice", "leadership", "protection", "pool"}
        if aspect not in allowed_aspects:
            print(f"❌ Aspect inválido: {aspect}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid aspect. Allowed: aggression, justice, leadership, protection, pool"
            )
        
        print(f"✅ Aspect válido: {aspect}")
        
        # Validar nombre duplicado (GLOBAL - case-insensitive, trim)
        conn = get_db_connection()
        cursor = conn.cursor()
        deck_name = deck_data.get('name', '').strip()
        cursor.execute('''
            SELECT COUNT(*) 
            FROM decks 
            WHERE LOWER(TRIM(name)) = LOWER(?)
        ''', (deck_name,))
        duplicate_count = cursor.fetchone()[0]
        
        if duplicate_count > 0:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un mazo con el nombre '{deck_name}'. Por favor, elige otro nombre."
            )
        
        print(f"✅ Nombre del mazo único: '{deck_name}'")
        
        # Validar que el mazo tenga entre 40 y 50 cartas (sin contar el héroe)
        cards = deck_data.get('cards', [])
        print(f"🔢 Validando {len(cards)} cartas...")
        
        # Validar quantity > 0 y entero
        for i, card in enumerate(cards):
            quantity = card.get('quantity', 0)
            if not isinstance(quantity, int) or quantity <= 0:
                print(f"❌ Carta {i+1} cantidad inválida: {quantity}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each card quantity must be a positive integer"
                )
        
        total_cards = sum(card.get('quantity', 1) for card in cards)
        print(f"🔢 Total de cartas: {total_cards}")
        
        if total_cards < 40 or total_cards > 50:
            print(f"❌ Mazo debe tener entre 40 y 50 cartas, tiene {total_cards}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deck must have between 40 and 50 cards (excluding hero). Current: {total_cards} cards"
            )
        
        print(f"✅ Mazo tiene {total_cards} cartas (válido)")
        
        # Validar que todas las cartas existan en la base de datos
        # (conn y cursor ya están abiertos desde la validación de nombre duplicado)
        
        print(f"🔍 Validando existencia de cartas y asignando clases...")
        for i, card in enumerate(cards):
            card_id = card.get('card_id')
            card_name = card.get('card_name', card.get('name', ''))
            card_set = card.get('card_set', '')
            quantity = card.get('quantity', 1)
            
            # Si se proporciona card_id, buscar por ID (más preciso)
            if card_id:
                cursor.execute('SELECT name, deck_limit, pack_name, aspect FROM cards WHERE id = ?', (card_id,))
                row = cursor.fetchone()
                if not row:
                    print(f"❌ Carta {i+1} no existe: ID {card_id}")
                    conn.close()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card with ID {card_id} does not exist in database"
                    )
                # Asignar la clase correcta automáticamente
                card['clase'] = row[3]  # aspect de la base de datos
                print(f"✅ Carta {i+1} existe: {row[0]} (ID: {card_id}) - Clase asignada: {row[3]}")
            else:
                # Fallback: buscar por nombre y set (método anterior)
                cursor.execute('SELECT name, deck_limit, pack_name, aspect FROM cards WHERE name = ? AND pack_name = ?', (card_name, card_set))
                row = cursor.fetchone()
                
                if not row:
                    print(f"❌ Carta {i+1} no existe: {card_name} del set {card_set}")
                    conn.close()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card '{card_name}' from set '{card_set}' does not exist in database"
                    )
                # Asignar la clase correcta automáticamente
                card['clase'] = row[3]  # aspect de la base de datos
                print(f"✅ Carta {i+1} existe: {row[0]} del set {card_set} - Clase asignada: {row[3]}")
            
            # Enforce deck_limit si existe
            deck_limit = None
            try:
                deck_limit = row["deck_limit"]
            except Exception:
                deck_limit = None
                
            if deck_limit is not None and isinstance(deck_limit, int):
                if quantity > deck_limit:
                    print(f"❌ Carta {i+1} excede límite: {card_name} del set {card_set} ({quantity} > {deck_limit})")
                    conn.close()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card '{card_name}' from set '{card_set}' exceeds deck limit ({deck_limit})"
                    )
                else:
                    print(f"✅ Carta {i+1} dentro del límite: {card_name} del set {card_set} ({quantity} <= {deck_limit})")
        
        print(f"✅ Todas las cartas validadas correctamente")
        
        # Primero verificar si la tabla decks tiene la columna user_id
        cursor.execute("PRAGMA table_info(decks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            # Añadir la columna user_id como INTEGER (no TEXT)
            cursor.execute('ALTER TABLE decks ADD COLUMN user_id INTEGER')
        
        # Procesar cartas para el formato correcto (incluyendo card_id y card_set)
        processed_cards = []
        for card in deck_data.get('cards', []):
            processed_cards.append({
                "card_id": card.get('card_id'),  # Incluir card_id si está disponible
                "card_name": card.get('card_name', card.get('name', '')),
                "card_set": card.get('card_set', ''),
                "quantity": card.get('quantity', 1)
            })
        
        print(f"💾 Insertando mazo en la base de datos...")
        print(f"📝 Descripción recibida: '{deck_data.get('description', '')}'") 
        print(f"🦸 Hero ID recibido: {deck_data.get('hero_id')}")
        user_id_value = user["id"] if user else None
        cursor.execute('''
            INSERT INTO decks (name, description, hero_name, hero_id, aspect, cards, is_public, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            deck_data.get("name", ""),
            deck_data.get("description", ""),
            deck_data.get("hero_name", ""),
            deck_data.get("hero_id"),  # Campo opcional
            deck_data.get("aspect"),
            json.dumps(processed_cards),
            1,  # Siempre público por ahora
            user_id_value  # NULL si no hay usuario (importación sin login)
        ))
        
        print(f"✅ Mazo insertado correctamente")
        
        deck_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        from datetime import datetime
        current_time = datetime.now().isoformat() + "Z"
        
        return {
            "deck": {
                "id": deck_id,
                "name": deck_data.get("name"),
                "hero_name": deck_data.get("hero_name"),
                "aspect": deck_data.get("aspect"),
                "cards": processed_cards,
                "created_at": current_time,
                "creator_name": user.get("name") if user else None,
                "hero_unresolved": deck_data.get("hero_id") is None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating deck: {str(e)}"
        )

def train_model_in_background():
    """
    Función que se ejecuta en segundo plano para entrenar el modelo después de subir una partida.
    
    NOTA: Las tablas se verifican automáticamente en get_game_data_from_db() usando
    verify_tables_exist(), que es más robusto que llamar ensure_* manualmente.
    """
    try:
        # Asegurar que las tablas necesarias existan antes de entrenar
        # (esto es redundante pero defensivo - get_game_data_from_db también verifica)
        ensure_game_configurations_table()
        ensure_decks_columns()
        
        # Entrenar modelo en segundo plano (silenciosamente si no hay suficientes datos)
        model = train_villain_recommender()
        if model:
            print("✅ Modelo entrenado exitosamente en segundo plano")
        # Si no hay suficientes datos, es comportamiento esperado - no mostrar mensaje
    except Exception as e:
        print(f"❌ Error entrenando modelo en segundo plano: {str(e)}")
        import traceback
        print(f"📋 Traceback completo:\n{traceback.format_exc()}")
        # No lanzamos excepción para no afectar la respuesta al usuario

@app.post("/api/game-configurations", status_code=201)
async def create_game_configuration(config_data: dict, request: Request, background_tasks: BackgroundTasks):
    """Crear una nueva configuración de partida"""
    try:
        ensure_game_configurations_table()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Debug log
        print(f"🎮 POST /api/game-configurations - Auth0_ID recibido: {auth0_id}")
        print(f"📦 Datos recibidos: {config_data}")
        
        # Validar autenticación
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        # Validar datos requeridos
        required_fields = ['deck_id', 'difficulty', 'villain_id', 'result', 'played_at']
        for field in required_fields:
            if not config_data.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Validar difficulty
        difficulty = config_data.get('difficulty')
        if difficulty not in ['normal', 'expert']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid difficulty. Allowed: normal, expert"
            )
        
        # Validar result
        result = config_data.get('result')
        if result not in ['win', 'loss']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid result. Allowed: win, loss"
            )
        
        # Validar que el deck existe y que el usuario puede usarlo (es suyo o es público)
        deck_id = config_data.get('deck_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, is_public FROM decks WHERE id = ?
        ''', (deck_id,))
        deck_row = cursor.fetchone()
        if not deck_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        deck_user_id = deck_row['user_id'] if deck_row['user_id'] is not None else None
        is_public = deck_row['is_public'] if deck_row['is_public'] is not None else 1
        # Permitir: es mazo del usuario, o es mazo público (de base de datos / importado)
        if deck_user_id is not None and deck_user_id != user['id'] and not is_public:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Deck not found or does not belong to user"
            )
        
        # Validar que el villano existe por ID
        villain_id = config_data.get('villain_id')
        cursor.execute('''
            SELECT COUNT(*) FROM cards WHERE type = 'villain' AND id = ?
        ''', (villain_id,))
        
        villain_count = cursor.fetchone()[0]
        if villain_count == 0:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Villain not found"
            )
        
        # Insertar la configuración de partida
        cursor.execute('''
            INSERT INTO game_configurations (
                user_id, deck_id, difficulty, villain_id, result, played_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user['id'],
            deck_id,
            difficulty,
            villain_id,
            result,
            config_data.get('played_at')
        ))
        
        game_config_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Configuración de partida creada: ID={game_config_id}")
        
        # Entrenar el modelo en segundo plano después de guardar la partida
        background_tasks.add_task(train_model_in_background)
        
        return {
            "message": "Configuración de partida guardada correctamente",
            "game_configuration_id": game_config_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creando configuración de partida: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating game configuration: {str(e)}"
        )


@app.delete("/api/game-configurations/{game_id}", status_code=200)
async def delete_game_configuration(game_id: int, request: Request):
    """Eliminar una partida del usuario. Solo se puede borrar una partida propia."""
    try:
        ensure_game_configurations_table()
        auth0_id = request.headers.get('X-Auth0-ID')
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        user = get_user_by_auth0_id(auth0_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM game_configurations WHERE id = ? AND user_id = ?',
            (game_id, user['id'])
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found or does not belong to user"
            )
        cursor.execute('DELETE FROM game_configurations WHERE id = ? AND user_id = ?', (game_id, user['id']))
        conn.commit()
        conn.close()
        return {"message": "Partida eliminada correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error eliminando partida: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting game configuration: {str(e)}"
        )


@app.get("/api/game-configurations")
async def get_game_configurations(request: Request):
    """Obtener todas las partidas del usuario autenticado"""
    try:
        ensure_game_configurations_table()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Validar autenticación
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si hay partidas antes de hacer JOINs
        cursor.execute('SELECT COUNT(*) FROM game_configurations WHERE user_id = ?', (user['id'],))
        count = cursor.fetchone()[0]
        
        if count == 0:
            conn.close()
            return {"games": []}
        
        # Obtener partidas del usuario con información del mazo, villano y creador
        # Filtrar partidas cuyo mazo aún existe (evitar partidas huérfanas)
        cursor.execute('''
            SELECT 
                gc.id,
                gc.deck_id,
                gc.difficulty,
                gc.villain_id,
                gc.result,
                gc.played_at,
                d.name as deck_name,
                d.hero_name,
                d.aspect,
                COALESCE(c.name, c.card_set, 'Unknown') as villain_name,
                u.name as creator_name
            FROM game_configurations gc
            INNER JOIN decks d ON gc.deck_id = d.id
            LEFT JOIN cards c ON gc.villain_id = c.id
            LEFT JOIN users u ON d.user_id = u.id
            WHERE gc.user_id = ?
            ORDER BY gc.played_at DESC
        ''', (user['id'],))
        
        games = []
        for row in cursor.fetchall():
            game = {
                "id": row["id"],
                "deck_id": row["deck_id"],
                "deck_name": row["deck_name"] if row["deck_name"] else "Unknown",
                "hero_name": row["hero_name"] if row["hero_name"] else "Unknown",
                "aspect": row["aspect"] if row["aspect"] else "Unknown",
                "villain_id": row["villain_id"],
                "villain_name": row["villain_name"] if row["villain_name"] else "Unknown",
                "difficulty": row["difficulty"],
                "result": row["result"],
                "played_at": row["played_at"],
                "creator_name": row["creator_name"] if row["creator_name"] else None
            }
            games.append(game)
        
        conn.close()
        
        return {"games": games}
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error retrieving game configurations: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log para debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving game configurations: {str(e)}"
        )

@app.get("/api/game-configurations/all")
async def get_all_game_configurations():
    """Obtener TODAS las partidas públicas de todos los usuarios. Endpoint público."""
    try:
        ensure_game_configurations_table()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si hay partidas antes de hacer JOINs
        cursor.execute('SELECT COUNT(*) FROM game_configurations')
        count = cursor.fetchone()[0]
        
        if count == 0:
            conn.close()
            return {"games": []}
        
        # Obtener todas las partidas con información del mazo, villano y creador
        # Filtrar partidas cuyo mazo aún existe (evitar partidas huérfanas)
        cursor.execute('''
            SELECT 
                gc.id,
                gc.deck_id,
                gc.difficulty,
                gc.villain_id,
                gc.result,
                gc.played_at,
                d.name as deck_name,
                d.hero_name,
                d.aspect,
                d.user_id,
                COALESCE(c.name, c.card_set, 'Unknown') as villain_name,
                u.name as creator_name
            FROM game_configurations gc
            INNER JOIN decks d ON gc.deck_id = d.id
            LEFT JOIN cards c ON gc.villain_id = c.id
            LEFT JOIN users u ON d.user_id = u.id
            ORDER BY gc.played_at DESC
        ''')
        
        games = []
        for row in cursor.fetchall():
            game = {
                "id": row["id"],
                "deck_id": row["deck_id"],
                "deck_name": row["deck_name"] if row["deck_name"] else "Unknown",
                "hero_name": row["hero_name"] if row["hero_name"] else "Unknown",
                "aspect": row["aspect"] if row["aspect"] else "Unknown",
                "villain_id": row["villain_id"],
                "villain_name": row["villain_name"] if row["villain_name"] else "Unknown",
                "difficulty": row["difficulty"],
                "result": row["result"],
                "played_at": row["played_at"],
                "creator_name": row["creator_name"] if row["creator_name"] else None
            }
            games.append(game)
        
        conn.close()
        
        return {"games": games}
        
    except Exception as e:
        import traceback
        error_detail = f"Error retrieving all game configurations: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log para debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving all game configurations: {str(e)}"
        )

@app.get("/api/game-configurations/stats")
async def get_game_stats(request: Request):
    """Obtener estadísticas de partidas del usuario"""
    try:
        ensure_game_configurations_table()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Validar autenticación
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Estadísticas generales
        cursor.execute('''
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN difficulty = 'normal' THEN 1 ELSE 0 END) as normal_games,
                SUM(CASE WHEN difficulty = 'expert' THEN 1 ELSE 0 END) as expert_games
            FROM game_configurations 
            WHERE user_id = ?
        ''', (user['id'],))
        
        stats_row = cursor.fetchone()
        
        # Villanos más jugados
        cursor.execute('''
            SELECT 
                c.card_set as villain_name,
                COUNT(*) as games_played,
                SUM(CASE WHEN gc.result = 'win' THEN 1 ELSE 0 END) as wins
            FROM game_configurations gc
            JOIN cards c ON gc.villain_id = c.id
            WHERE gc.user_id = ?
            GROUP BY c.card_set
            ORDER BY games_played DESC
            LIMIT 5
        ''', (user['id'],))
        
        top_villains = []
        for row in cursor.fetchall():
            top_villains.append({
                "villain_name": row["villain_name"],
                "games_played": row["games_played"],
                "wins": row["wins"],
                "win_rate": round((row["wins"] / row["games_played"]) * 100, 1) if row["games_played"] > 0 else 0
            })
        
        # Mazos más usados
        cursor.execute('''
            SELECT 
                d.name as deck_name,
                d.hero_name,
                d.aspect,
                COUNT(*) as games_played,
                SUM(CASE WHEN gc.result = 'win' THEN 1 ELSE 0 END) as wins
            FROM game_configurations gc
            JOIN decks d ON gc.deck_id = d.id
            WHERE gc.user_id = ?
            GROUP BY d.id, d.name, d.hero_name, d.aspect
            ORDER BY games_played DESC
            LIMIT 5
        ''', (user['id'],))
        
        top_decks = []
        for row in cursor.fetchall():
            top_decks.append({
                "deck_name": row["deck_name"],
                "hero_name": row["hero_name"],
                "aspect": row["aspect"],
                "games_played": row["games_played"],
                "wins": row["wins"],
                "win_rate": round((row["wins"] / row["games_played"]) * 100, 1) if row["games_played"] > 0 else 0
            })
        
        conn.close()
        
        total_games = stats_row["total_games"] or 0
        wins = stats_row["wins"] or 0
        losses = stats_row["losses"] or 0
        
        stats = {
            "total_games": total_games,
            "wins": wins,
            "losses": losses,
            "win_rate": round((wins / total_games) * 100, 1) if total_games > 0 else 0,
            "normal_games": stats_row["normal_games"] or 0,
            "expert_games": stats_row["expert_games"] or 0,
            "top_villains": top_villains,
            "top_decks": top_decks
        }
        
        return {"stats": stats}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving game stats: {str(e)}"
        )

@app.get("/api/decks/{deck_id}")
async def get_deck(deck_id: int):
    """Obtener un mazo específico por ID"""
    ensure_decks_columns()
    ensure_user_favorites_table()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Incluir conteo de favoritos usando LEFT JOIN con user_favorites
    cursor.execute('''
        SELECT d.id, d.name, d.description, d.hero_name, d.hero_id, d.aspect, d.cards, d.created_at,
               COALESCE(COUNT(uf.id), 0) as favorite_count
        FROM decks d
        LEFT JOIN user_favorites uf ON d.id = uf.deck_id
        WHERE d.id = ? AND d.is_public = 1
        GROUP BY d.id, d.name, d.description, d.hero_name, d.hero_id, d.aspect, d.cards, d.created_at
    ''', (deck_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Mazo no encontrado")
    
    try:
        raw_cards = json.loads(row["cards"]) if row["cards"] else []
    except json.JSONDecodeError:
        raw_cards = []
    
    # Normalizar a formato { card_id, card_name, card_set, quantity, type, clase }
    cards_data = []
    for c in raw_cards:
        card_id = c.get("card_id")
        card_name = c.get("card_name") or c.get("name") or c.get("code")
        card_set = c.get("card_set", "")
        
        # Si tenemos card_id, buscar por ID (más preciso)
        if card_id:
            cursor.execute('SELECT type, aspect, pack_name, card_set FROM cards WHERE id = ?', (card_id,))
            card_info = cursor.fetchone()
            
            if card_info:
                card_data = {
                    "card_id": card_id,
                    "card_name": card_name,
                    "card_set": card_info[3] or card_set,  # Usar card_set de la BD
                    "quantity": c.get("quantity", 1),
                    "type": card_info[0],
                    "clase": card_info[1],
                    "set": card_info[2] or "Unknown"
                }
            else:
                # Fallback si no encuentra por ID
                card_data = {
                    "card_id": card_id,
                    "card_name": card_name,
                    "card_set": card_set,
                    "quantity": c.get("quantity", 1)
                }
        else:
            # Fallback: buscar por nombre y set
            cursor.execute('SELECT id, type, aspect, pack_name, card_set FROM cards WHERE name = ? AND (card_set = ? OR pack_name = ?)', (card_name, card_set, card_set))
            card_info = cursor.fetchone()
            
            if card_info:
                card_data = {
                    "card_id": card_info[0],  # ID de la BD
                    "card_name": card_name,
                    "card_set": card_info[4] or card_set,
                    "quantity": c.get("quantity", 1),
                    "type": card_info[1],
                    "clase": card_info[2],
                    "set": card_info[3] or "Unknown"
                }
            else:
                # Último fallback
                card_data = {
                    "card_name": card_name,
                    "card_set": card_set,
                    "quantity": c.get("quantity", 1)
                }
        
        cards_data.append(card_data)
    
    # Obtener nombre del creador si existe user_id
    creator_name = None
    try:
        cursor.execute("PRAGMA table_info(decks)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'user_id' in columns:
            cursor.execute('SELECT user_id FROM decks WHERE id = ?', (deck_id,))
            uid_row = cursor.fetchone()
            if uid_row and uid_row[0]:
                # Ahora user_id es el ID numérico, no el auth0_id
                cursor.execute('SELECT name FROM users WHERE id = ?', (uid_row[0],))
                user_row = cursor.fetchone()
                if user_row and user_row[0]:
                    creator_name = user_row[0]
    except Exception:
        creator_name = None

    deck = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "hero_name": row["hero_name"],
        "hero_id": row["hero_id"],  # Campo opcional
        "aspect": row["aspect"],
        "cards": cards_data,
        "created_at": row["created_at"],
        "creator_name": creator_name,
        "favorite_count": row["favorite_count"]
    }
    
    print(f"📤 Devolviendo mazo con descripción: '{row['description']}'")
    
    conn.close()
    return deck

@app.get("/api/decks/{deck_id}/is-favorite")
async def check_deck_favorite(deck_id: int, request: Request):
    """Verificar si un mazo es favorito del usuario autenticado"""
    try:
        ensure_user_favorites_table()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el mazo existe
        cursor.execute('SELECT id FROM decks WHERE id = ?', (deck_id,))
        deck_row = cursor.fetchone()
        if not deck_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        # Verificar si es favorito
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM user_favorites 
            WHERE user_id = ? AND deck_id = ?
        ''', (user["id"], deck_id))
        
        count = cursor.fetchone()[0]
        is_favorite = count > 0
        
        conn.close()
        
        return {"is_favorite": is_favorite}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/favorites")
async def toggle_favorite(favorite_data: dict, request: Request):
    """Añadir o quitar un mazo de favoritos"""
    try:
        ensure_user_favorites_table()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        # Validar datos requeridos
        deck_id = favorite_data.get('deck_id')
        action = favorite_data.get('action')
        
        if not deck_id or not action:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: deck_id, action"
            )
        
        if action not in ['add', 'remove']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Allowed: add, remove"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el mazo existe
        cursor.execute('SELECT id FROM decks WHERE id = ?', (deck_id,))
        deck_row = cursor.fetchone()
        if not deck_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        # Verificar si ya es favorito
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM user_favorites 
            WHERE user_id = ? AND deck_id = ?
        ''', (user["id"], deck_id))
        
        count = cursor.fetchone()[0]
        is_favorite = count > 0
        
        if action == 'add':
            if is_favorite:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Deck is already in favorites"
                )
            
            # Añadir a favoritos
            cursor.execute('''
                INSERT INTO user_favorites (user_id, deck_id)
                VALUES (?, ?)
            ''', (user["id"], deck_id))
            
            conn.commit()
            conn.close()
            
            return {
                "message": "Favorito añadido correctamente",
                "is_favorite": True
            }
        
        else:  # action == 'remove'
            if not is_favorite:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Deck is not in favorites"
                )
            
            # Quitar de favoritos
            cursor.execute('''
                DELETE FROM user_favorites 
                WHERE user_id = ? AND deck_id = ?
            ''', (user["id"], deck_id))
            
            conn.commit()
            conn.close()
            
            return {
                "message": "Favorito eliminado correctamente",
                "is_favorite": False
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# =============================================================================
# ENDPOINTS DE COMENTARIOS
# =============================================================================

@app.get("/api/decks/{deck_id}/comments")
async def get_deck_comments(deck_id: int):
    """Obtener todos los comentarios de un mazo específico. Endpoint público."""
    try:
        ensure_deck_comments_table()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el mazo existe
        cursor.execute('SELECT id FROM decks WHERE id = ?', (deck_id,))
        deck = cursor.fetchone()
        
        if not deck:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        # Obtener todos los comentarios del mazo con nombre del autor
        cursor.execute('''
            SELECT 
                dc.id,
                dc.deck_id,
                dc.auth0_id,
                dc.comment_text,
                dc.created_at,
                dc.updated_at,
                u.name as author_name
            FROM deck_comments dc
            LEFT JOIN users u ON dc.auth0_id = u.auth0_id
            WHERE dc.deck_id = ?
            ORDER BY dc.created_at DESC
        ''', (deck_id,))
        
        comments = []
        for row in cursor.fetchall():
            comment = {
                "id": row["id"],
                "deck_id": row["deck_id"],
                "auth0_id": row["auth0_id"],
                "author_name": row["author_name"],
                "comment_text": row["comment_text"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            comments.append(comment)
        
        conn.close()
        
        return {"comments": comments}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving comments: {str(e)}"
        )

@app.post("/api/decks/{deck_id}/comments", status_code=201)
async def create_deck_comment(deck_id: int, comment_data: dict, request: Request):
    """Crear un nuevo comentario en un mazo. REQUIERE AUTENTICACIÓN."""
    try:
        ensure_deck_comments_table()
        
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Validar autenticación
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        # Validar datos requeridos
        comment_text = comment_data.get('comment_text')
        
        if not comment_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="comment_text is required"
            )
        
        # Validar que el comentario no esté vacío (trimmed)
        comment_text = comment_text.strip()
        if not comment_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="comment_text cannot be empty"
            )
        
        # Validar límite de caracteres (1000 caracteres)
        MAX_COMMENT_LENGTH = 1000
        if len(comment_text) > MAX_COMMENT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"comment_text cannot exceed {MAX_COMMENT_LENGTH} characters"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el mazo existe
        cursor.execute('SELECT id FROM decks WHERE id = ?', (deck_id,))
        deck = cursor.fetchone()
        
        if not deck:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found"
            )
        
        # Crear el comentario
        cursor.execute('''
            INSERT INTO deck_comments (deck_id, auth0_id, comment_text)
            VALUES (?, ?, ?)
        ''', (deck_id, auth0_id, comment_text))
        
        comment_id = cursor.lastrowid
        
        conn.commit()
        
        # Obtener el comentario creado con nombre del autor
        cursor.execute('''
            SELECT 
                dc.id,
                dc.deck_id,
                dc.auth0_id,
                dc.comment_text,
                dc.created_at,
                dc.updated_at,
                u.name as author_name
            FROM deck_comments dc
            LEFT JOIN users u ON dc.auth0_id = u.auth0_id
            WHERE dc.id = ?
        ''', (comment_id,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving created comment"
            )
        
        comment = {
            "id": row["id"],
            "deck_id": row["deck_id"],
            "auth0_id": row["auth0_id"],
            "author_name": row["author_name"],
            "comment_text": row["comment_text"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
        
        conn.close()
        
        return {
            "comment": comment,
            "message": "Comentario creado correctamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating comment: {str(e)}"
        )

@app.put("/api/comments/{comment_id}")
async def update_deck_comment(comment_id: int, comment_data: dict, request: Request):
    """Actualizar un comentario existente. Solo el autor puede editarlo. REQUIERE AUTENTICACIÓN."""
    try:
        ensure_deck_comments_table()
        
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Validar autenticación
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        # Validar datos requeridos
        comment_text = comment_data.get('comment_text')
        
        if not comment_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="comment_text is required"
            )
        
        # Validar que el comentario no esté vacío (trimmed)
        comment_text = comment_text.strip()
        if not comment_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="comment_text cannot be empty"
            )
        
        # Validar límite de caracteres (1000 caracteres)
        MAX_COMMENT_LENGTH = 1000
        if len(comment_text) > MAX_COMMENT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"comment_text cannot exceed {MAX_COMMENT_LENGTH} characters"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el comentario existe y obtener su auth0_id
        cursor.execute('''
            SELECT id, auth0_id, deck_id
            FROM deck_comments
            WHERE id = ?
        ''', (comment_id,))
        
        comment = cursor.fetchone()
        
        if not comment:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        # Verificar que el usuario es el autor del comentario
        if comment["auth0_id"] != auth0_id:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own comments"
            )
        
        # Actualizar el comentario
        cursor.execute('''
            UPDATE deck_comments
            SET comment_text = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (comment_text, comment_id))
        
        conn.commit()
        
        # Obtener el comentario actualizado con nombre del autor
        cursor.execute('''
            SELECT 
                dc.id,
                dc.deck_id,
                dc.auth0_id,
                dc.comment_text,
                dc.created_at,
                dc.updated_at,
                u.name as author_name
            FROM deck_comments dc
            LEFT JOIN users u ON dc.auth0_id = u.auth0_id
            WHERE dc.id = ?
        ''', (comment_id,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving updated comment"
            )
        
        updated_comment = {
            "id": row["id"],
            "deck_id": row["deck_id"],
            "auth0_id": row["auth0_id"],
            "author_name": row["author_name"],
            "comment_text": row["comment_text"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
        
        conn.close()
        
        return {
            "comment": updated_comment,
            "message": "Comentario actualizado correctamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating comment: {str(e)}"
        )

@app.delete("/api/comments/{comment_id}")
async def delete_deck_comment(comment_id: int, request: Request):
    """Eliminar un comentario. Solo el autor puede eliminarlo. REQUIERE AUTENTICACIÓN."""
    try:
        ensure_deck_comments_table()
        
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Validar autenticación
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el comentario existe y obtener su auth0_id
        cursor.execute('''
            SELECT id, auth0_id
            FROM deck_comments
            WHERE id = ?
        ''', (comment_id,))
        
        comment = cursor.fetchone()
        
        if not comment:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        # Verificar que el usuario es el autor del comentario
        if comment["auth0_id"] != auth0_id:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own comments"
            )
        
        # Eliminar el comentario
        cursor.execute('''
            DELETE FROM deck_comments
            WHERE id = ?
        ''', (comment_id,))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Comentario eliminado correctamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting comment: {str(e)}"
        )

# =============================================================================
# ENDPOINTS PROTEGIDOS (requieren autenticación)
# =============================================================================

@app.get("/api/user/profile")
async def get_user_profile(request: Request):
    """Obtener perfil del usuario autenticado"""
    try:
        auth0_id = request.headers.get('X-Auth0-ID')
        
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "auth0_id": user["auth0_id"],
            "created_at": user["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/user/stats")
async def get_user_stats(request: Request):
    """Obtener estadísticas del usuario autenticado"""
    try:
        ensure_decks_columns()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Contar mazos del usuario usando el ID numérico del usuario
        cursor.execute('SELECT COUNT(*) FROM decks WHERE user_id = ?', (user["id"],))
        deck_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "deckCount": deck_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/user/decks")
async def get_user_decks(request: Request):
    """Obtener mazos del usuario autenticado"""
    try:
        ensure_decks_columns()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si existe la columna user_id
        cursor.execute("PRAGMA table_info(decks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            conn.close()
            return {"decks": []}
        
        # Obtener mazos del usuario con conteo de favoritos
        ensure_user_favorites_table()
        cursor.execute('''
            SELECT d.id, d.name, d.description, d.hero_name, d.hero_id, d.aspect, d.cards, d.created_at, d.is_public,
                   COALESCE(COUNT(uf.id), 0) as favorite_count
            FROM decks d
            LEFT JOIN user_favorites uf ON d.id = uf.deck_id
            WHERE d.user_id = ?
            GROUP BY d.id, d.name, d.description, d.hero_name, d.hero_id, d.aspect, d.cards, d.created_at, d.is_public
            ORDER BY d.created_at DESC
        ''', (user["id"],))
        
        decks = []
        for row in cursor.fetchall():
            try:
                raw_cards = json.loads(row["cards"]) if row["cards"] else []
            except json.JSONDecodeError:
                raw_cards = []
            # Normalizar a formato { card_id, card_name, card_set, quantity, type, clase }
            cards_data = []
            for c in raw_cards:
                card_id = c.get("card_id")
                card_name = c.get("card_name") or c.get("name") or c.get("code")
                card_set = c.get("card_set", "")
                
                # Si tenemos card_id, buscar por ID (más preciso)
                if card_id:
                    cursor.execute('SELECT type, aspect, pack_name, card_set FROM cards WHERE id = ?', (card_id,))
                    card_info = cursor.fetchone()
                    
                    if card_info:
                        card_data = {
                            "card_id": card_id,
                            "card_name": card_name,
                            "card_set": card_info[3] or card_set,
                            "quantity": c.get("quantity", 1),
                            "type": card_info[0],
                            "clase": card_info[1],
                            "set": card_info[2] or "Unknown"
                        }
                    else:
                        # Fallback si no encuentra por ID
                        card_data = {
                            "card_id": card_id,
                            "card_name": card_name,
                            "card_set": card_set,
                            "quantity": c.get("quantity", 1)
                        }
                else:
                    # Fallback: buscar por nombre y set
                    cursor.execute('SELECT id, type, aspect, pack_name, card_set FROM cards WHERE name = ? AND (card_set = ? OR pack_name = ?)', (card_name, card_set, card_set))
                    card_info = cursor.fetchone()
                    
                    if card_info:
                        card_data = {
                            "card_id": card_info[0],  # ID de la BD
                            "card_name": card_name,
                            "card_set": card_info[4] or card_set,
                            "quantity": c.get("quantity", 1),
                            "type": card_info[1],
                            "clase": card_info[2],
                            "set": card_info[3] or "Unknown"
                        }
                    else:
                        # Último fallback
                        card_data = {
                            "card_name": card_name,
                            "card_set": card_set,
                            "quantity": c.get("quantity", 1)
                        }
                
                cards_data.append(card_data)
            
            # Obtener nombre del creador (el propio usuario)
            creator_name = user.get("name")

            deck = {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "hero_name": row["hero_name"],
                "hero_id": row["hero_id"],  # Campo opcional
                "aspect": row["aspect"],
                "cards": cards_data,
                "created_at": row["created_at"],
                "isPublic": bool(row["is_public"]),
                "creator_name": creator_name,
                "favorite_count": row["favorite_count"]
            }
            decks.append(deck)
        
        conn.close()
        
        return {
            "decks": decks,
            "user_id": user["id"],
            "total_decks": len(decks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error in get_user_decks: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log para debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/user/favorites")
async def get_user_favorites(request: Request):
    """Obtener mazos favoritos del usuario autenticado"""
    try:
        ensure_user_favorites_table()
        ensure_decks_columns()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el usuario tiene favoritos antes de hacer JOINs
        cursor.execute('SELECT COUNT(*) FROM user_favorites WHERE user_id = ?', (user["id"],))
        favorites_count = cursor.fetchone()[0]
        
        if favorites_count == 0:
            conn.close()
            return {"favorites": []}
        
        # Obtener mazos favoritos del usuario con conteo de favoritos
        cursor.execute('''
            SELECT d.id, d.name, d.description, d.hero_name, d.hero_id, d.aspect, d.cards, d.created_at, uf.created_at as favorited_at,
                   COALESCE(COUNT(DISTINCT uf2.id), 0) as favorite_count
            FROM user_favorites uf
            LEFT JOIN decks d ON uf.deck_id = d.id
            LEFT JOIN user_favorites uf2 ON d.id = uf2.deck_id
            WHERE uf.user_id = ?
            GROUP BY d.id, d.name, d.description, d.hero_name, d.hero_id, d.aspect, d.cards, d.created_at, uf.created_at
            ORDER BY uf.created_at DESC
        ''', (user["id"],))
        
        favorites = []
        for row in cursor.fetchall():
            try:
                raw_cards = json.loads(row["cards"]) if row["cards"] else []
            except json.JSONDecodeError:
                raw_cards = []
            
            # Procesar cartas del mazo
            cards_data = []
            for c in raw_cards:
                card_id = c.get("card_id")
                card_name = c.get("card_name") or c.get("name") or c.get("code")
                card_set = c.get("card_set", "")
                
                if card_id:
                    cursor.execute('SELECT type, aspect, pack_name, card_set FROM cards WHERE id = ?', (card_id,))
                    card_info = cursor.fetchone()
                    
                    if card_info:
                        card_data = {
                            "card_id": card_id,
                            "card_name": card_name,
                            "card_set": card_info[3] or card_set,
                            "quantity": c.get("quantity", 1),
                            "type": card_info[0],
                            "clase": card_info[1],
                            "set": card_info[2] or "Unknown"
                        }
                    else:
                        card_data = {
                            "card_id": card_id,
                            "card_name": card_name,
                            "card_set": card_set,
                            "quantity": c.get("quantity", 1)
                        }
                else:
                    card_data = {
                        "card_name": card_name,
                        "card_set": card_set,
                        "quantity": c.get("quantity", 1)
                    }
                
                cards_data.append(card_data)
            
            favorite = {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "hero_name": row["hero_name"],
                "hero_id": row["hero_id"],
                "aspect": row["aspect"],
                "cards": cards_data,
                "created_at": row["created_at"],
                "favorited_at": row["favorited_at"],
                "favorite_count": row["favorite_count"]
            }
            favorites.append(favorite)
        
        conn.close()
        
        return {"favorites": favorites}
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error in get_user_favorites: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log para debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.put("/api/decks/{deck_id}")
async def update_deck(deck_id: int, deck_data: dict, request: Request):
    """Actualizar un mazo existente"""
    try:
        ensure_decks_columns()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Debug log
        print(f"🔍 PUT /api/decks/{deck_id} - Auth0_ID recibido: {auth0_id}")
        print(f"📦 Datos recibidos: {deck_data}")
        print(f"🎯 Cartas en el mazo: {len(deck_data.get('cards', []))}")
        
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        
        if not user:
            print(f"❌ Usuario no encontrado para Auth0_ID: {auth0_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        print(f"✅ Usuario encontrado: ID={user['id']}, Name={user['name']}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el mazo existe y pertenece al usuario
        cursor.execute('''
            SELECT id, user_id FROM decks 
            WHERE id = ? AND user_id = ?
        ''', (deck_id, user["id"]))
        
        deck = cursor.fetchone()
        
        if not deck:
            print(f"❌ Mazo {deck_id} no encontrado o no pertenece al usuario {user['id']}")
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found or does not belong to user"
            )
        
        print(f"✅ Mazo encontrado: ID={deck[0]}, User_ID={deck[1]}")
        
        # Validar nombre duplicado (GLOBAL - case-insensitive, trim, excluyendo mazo actual)
        deck_name = deck_data.get('name', '').strip()
        cursor.execute('''
            SELECT COUNT(*) 
            FROM decks 
            WHERE LOWER(TRIM(name)) = LOWER(?)
              AND id != ?
        ''', (deck_name, deck_id))
        duplicate_count = cursor.fetchone()[0]
        
        if duplicate_count > 0:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un mazo con el nombre '{deck_name}'. Por favor, elige otro nombre."
            )
        
        print(f"✅ Nombre del mazo único: '{deck_name}'")
        
        # Validar datos del mazo
        required_fields = ['name', 'hero_name', 'cards']
        for field in required_fields:
            if field not in deck_data:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Validar que el mazo tenga entre 40 y 50 cartas (excluyendo el héroe)
        total_cards = sum(card.get('quantity', 0) for card in deck_data['cards'])
        print(f"🔢 Total de cartas calculado: {total_cards}")
        if total_cards < 40 or total_cards > 50:
            print(f"❌ Mazo debe tener entre 40 y 50 cartas, tiene {total_cards}")
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deck must have between 40 and 50 cards, has {total_cards}"
            )
        print(f"✅ Mazo tiene {total_cards} cartas (válido)")
        
        # Validar que todas las cartas existan y respeten los límites
        for i, card in enumerate(deck_data['cards']):
            print(f"🔍 Validando carta {i+1}: {card}")
            card_id = card.get('card_id')
            card_name = card.get('card_name')
            card_set = card.get('card_set', '')
            quantity = card.get('quantity', 0)
            
            print(f"   - card_id: {card_id}")
            print(f"   - card_name: {card_name}")
            print(f"   - card_set: {card_set}")
            print(f"   - quantity: {quantity}")
            
            if not card_name and not card_id:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Card name or card_id is required"
                )
            
            # Si se proporciona card_id, buscar por ID (más preciso)
            if card_id:
                print(f"   🔍 Buscando por card_id: {card_id}")
                cursor.execute('SELECT deck_limit, aspect FROM cards WHERE id = ?', (card_id,))
                card_info = cursor.fetchone()
                if not card_info:
                    print(f"   ❌ Carta con ID {card_id} no encontrada")
                    conn.close()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card with ID {card_id} does not exist"
                    )
                print(f"   ✅ Carta encontrada por ID: deck_limit={card_info[0]}, aspect={card_info[1]}")
                # Asignar la clase correcta automáticamente
                card['clase'] = card_info[1]  # aspect de la base de datos
            else:
                # Fallback: buscar por nombre y set (card_set O pack_name)
                print(f"   🔍 Buscando por nombre '{card_name}' y set '{card_set}'")
                cursor.execute('SELECT deck_limit, aspect FROM cards WHERE name = ? AND (card_set = ? OR pack_name = ?)', (card_name, card_set, card_set))
                card_info = cursor.fetchone()
                
                if not card_info:
                    print(f"   ❌ Carta '{card_name}' del set '{card_set}' no encontrada")
                    conn.close()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card '{card_name}' from set '{card_set}' does not exist"
                    )
                print(f"   ✅ Carta encontrada por nombre: deck_limit={card_info[0]}, aspect={card_info[1]}")
                # Asignar la clase correcta automáticamente
                card['clase'] = card_info[1]  # aspect de la base de datos
            
            # Verificar límite de cartas
            deck_limit = card_info[0] if card_info[0] is not None else 3
            if quantity > deck_limit:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Card '{card_name}' from set '{card_set}' quantity ({quantity}) exceeds deck limit ({deck_limit})"
                )
        
        # Actualizar el mazo
        cursor.execute('''
            UPDATE decks 
            SET name = ?, description = ?, hero_name = ?, hero_id = ?, cards = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (
            deck_data['name'],
            deck_data.get('description', ''),  # Campo opcional
            deck_data['hero_name'],
            deck_data.get('hero_id'),  # Campo opcional
            json.dumps(deck_data['cards']),
            deck_id,
            user["id"]
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Deck updated successfully",
            "deck_id": deck_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.delete("/api/decks/{deck_id}")
async def delete_deck(deck_id: int, request: Request):
    """Eliminar un mazo existente"""
    try:
        ensure_decks_columns()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        if not auth0_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auth0 ID header is required"
            )
        
        user = get_user_by_auth0_id(auth0_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el mazo existe y pertenece al usuario
        cursor.execute('''
            SELECT id FROM decks 
            WHERE id = ? AND user_id = ?
        ''', (deck_id, user["id"]))
        
        deck = cursor.fetchone()
        
        if not deck:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deck not found or does not belong to user"
            )
        
        # Contar partidas asociadas antes de eliminar
        cursor.execute('SELECT COUNT(*) FROM game_configurations WHERE deck_id = ?', (deck_id,))
        games_count = cursor.fetchone()[0]
        
        # Eliminar partidas asociadas al mazo
        cursor.execute('DELETE FROM game_configurations WHERE deck_id = ?', (deck_id,))
        games_deleted = cursor.rowcount
        
        # Eliminar comentarios asociados al mazo (si existen)
        cursor.execute('DELETE FROM deck_comments WHERE deck_id = ?', (deck_id,))
        comments_deleted = cursor.rowcount
        
        # Eliminar el mazo (esto también eliminará los favoritos por ON DELETE CASCADE)
        cursor.execute('DELETE FROM decks WHERE id = ? AND user_id = ?', (deck_id, user["id"]))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Deck deleted successfully",
            "deck_id": deck_id,
            "games_deleted": games_deleted,
            "comments_deleted": comments_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# =============================================================================
# IMPORTACIÓN DE CARTAS DESDE MARVELCDB
# =============================================================================

# URL base de la API de MarvelCDB
MARVELCDB_API_BASE = "https://marvelcdb.com/api/public"

# Modelos Pydantic para los endpoints
class CheckMissingRequest(BaseModel):
    card_codes: List[str]

class CardData(BaseModel):
    """Datos completos de una carta que el frontend puede pasar"""
    code: str  # Código de MarvelCDB (ej: "01001")
    name: Optional[str] = None
    type_code: Optional[str] = None
    faction_code: Optional[str] = None
    pack_code: Optional[str] = None
    pack_name: Optional[str] = None
    cost: Optional[int] = None
    deck_limit: Optional[int] = None
    health: Optional[int] = None
    attack: Optional[int] = None
    threat: Optional[int] = None
    scheme: Optional[int] = None
    traits: Optional[str] = None
    text: Optional[str] = None
    is_unique: Optional[bool] = None
    quantity: Optional[int] = 1
    card_set_name: Optional[str] = None

class ImportMissingRequest(BaseModel):
    card_codes: Optional[List[str]] = None  # Códigos para buscar desde MarvelCDB
    cards: Optional[List[CardData]] = None  # Datos completos de cartas (si el frontend ya los tiene)
    
    class Config:
        # Permitir que se pase card_codes o cards (o ambos)
        pass

def map_marvelcdb_card_to_db(card_data: dict) -> dict:
    """
    Mapea una carta de MarvelCDB a nuestra estructura de base de datos.
    Incluye TODOS los campos necesarios para que la carta sea igual a las que ya tenemos.
    
    IMPORTANTE: Usa .get() con valores por defecto para TODOS los campos,
    así nunca falla aunque la API no devuelva algún campo.
    """
    # Validar que tenemos al menos code y name (campos críticos)
    if not card_data.get('code'):
        raise ValueError("La carta debe tener un campo 'code'")
    
    if not card_data.get('name'):
        print(f"⚠️  Advertencia: Carta {card_data.get('code')} no tiene nombre, usando 'Unknown'")
    
    # Convertir code a entero para id (siempre seguro porque validamos arriba)
    card_id = card_data.get('code', '')
    if card_id and str(card_id).isdigit():
        card_id = int(card_id)
    else:
        card_id = abs(hash(str(card_id))) % 1000000
    
    # Función auxiliar para convertir a int de forma segura
    def safe_int(value, default=0):
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    # Función auxiliar para obtener string de forma segura
    def safe_str(value, default=''):
        if value is None:
            return default
        try:
            return str(value)
        except:
            return default
    
    # Mapear campos principales con valores por defecto seguros
    # TODOS los campos usan .get() con valores por defecto para que nunca falle
    
    # Obtener faction_code y type_code
    faction_code = safe_str(card_data.get('faction_code'), '').lower()
    type_code = safe_str(card_data.get('type_code'), '').lower()
    
    # Mapear aspect (clase) correctamente
    # Si es un héroe, el aspect debe ser 'hero'
    # Si es una carta de aspecto, usar el faction_code directamente
    if type_code == 'hero':
        aspect = 'hero'
    elif faction_code in ['aggression', 'justice', 'leadership', 'protection', 'pool', 'basic', 'hero', 'encounter', 'campaign']:
        aspect = faction_code
    else:
        # Si no reconocemos el faction_code, usar 'basic' como fallback
        aspect = 'basic'
        print(f"⚠️  Carta {card_data.get('code')} tiene faction_code desconocido: '{faction_code}', usando 'basic'")
    
    # Obtener el code original de MarvelCDB (CRÍTICO: guardar el code, no el id)
    marvelcdb_code = safe_str(card_data.get('code'), '')
    
    mapped = {
        'id': card_id,
        'name': safe_str(card_data.get('name'), 'Unknown Card'),
        'aspect': aspect,  # aspect = clase (mapeado correctamente)
        'type': type_code,
        'cost': safe_int(card_data.get('cost'), 0),
        'set_name': safe_str(card_data.get('card_set_name') or card_data.get('pack_name') or card_data.get('pack_code'), ''),  # Set: card_set_name -> pack_name -> pack_code
        'set_code': safe_str(card_data.get('pack_code'), ''),  # Código del pack
        'pack_code': safe_str(card_data.get('pack_code'), ''),
        'pack_name': safe_str(card_data.get('pack_name'), ''),
        'faction_code': faction_code,  # Guardar el faction_code original (en minúsculas)
        'type_code': type_code,  # Guardar el type_code original (en minúsculas)
        'card_set': safe_str(card_data.get('card_set_name') or card_data.get('pack_name') or card_data.get('pack_code'), ''),  # Set: card_set_name -> pack_name -> pack_code
        'quantity': safe_int(card_data.get('quantity'), 1),
        'marvelcdb_code': marvelcdb_code,  # CRÍTICO: Guardar el code de MarvelCDB (ej: "01001")
        'deck_limit': None,  # Se procesa abajo
        'health': None,  # Se procesa abajo
        'attack': None,  # Se procesa abajo
        'threat': None,  # Se procesa abajo
        'traits': None,  # Se procesa abajo
        'text': None,  # Se procesa abajo
        'is_unique': 0  # Se procesa abajo
    }
    
    # Procesar deck_limit (opcional)
    deck_limit = card_data.get('deck_limit')
    if deck_limit is not None:
        mapped['deck_limit'] = safe_int(deck_limit, None)
    
    # Procesar health (opcional)
    health = card_data.get('health')
    if health is not None:
        mapped['health'] = safe_int(health, None)
    
    # Procesar attack (opcional)
    attack = card_data.get('attack')
    if attack is not None:
        mapped['attack'] = safe_int(attack, None)
    
    # Procesar threat (opcional)
    # Algunas cartas usan 'scheme' en lugar de 'threat'
    threat = card_data.get('threat') or card_data.get('scheme')
    if threat is not None:
        mapped['threat'] = safe_int(threat, None)
    
    # Procesar traits (opcional, puede ser string, lista o None)
    traits = card_data.get('traits')
    if traits:
        try:
            if isinstance(traits, list):
                mapped['traits'] = ', '.join(str(t) for t in traits)
            else:
                mapped['traits'] = str(traits)
        except:
            mapped['traits'] = None
    
    # Procesar text (opcional)
    text = card_data.get('text')
    if text:
        try:
            mapped['text'] = str(text)
        except:
            mapped['text'] = None
    
    # Procesar is_unique (opcional, puede ser bool, int, string)
    is_unique = card_data.get('is_unique', False)
    try:
        if isinstance(is_unique, bool):
            mapped['is_unique'] = 1 if is_unique else 0
        elif isinstance(is_unique, (int, str)):
            mapped['is_unique'] = 1 if bool(int(str(is_unique))) else 0
        else:
            mapped['is_unique'] = 0
    except:
        mapped['is_unique'] = 0
    
    return mapped

def card_exists_by_code(card_code: str) -> bool:
    """Verifica si una carta existe en la BD usando su code de MarvelCDB"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar por marvelcdb_code (el code original de MarvelCDB)
    # Primero verificar si la columna existe
    cursor.execute("PRAGMA table_info(cards)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'marvelcdb_code' in columns:
        # Buscar por marvelcdb_code (método preferido)
        cursor.execute('SELECT COUNT(*) FROM cards WHERE marvelcdb_code = ?', (card_code,))
        exists = cursor.fetchone()[0] > 0
    else:
        # Fallback: buscar por id (convertir code a id)
        try:
            card_id = int(card_code) if card_code.isdigit() else abs(hash(card_code)) % 1000000
        except:
            card_id = abs(hash(card_code)) % 1000000
        cursor.execute('SELECT COUNT(*) FROM cards WHERE id = ?', (card_id,))
        exists = cursor.fetchone()[0] > 0
    
    conn.close()
    return exists

@app.post("/api/cards/check-missing", status_code=200)
async def check_missing_cards(request_data: CheckMissingRequest):
    """
    Verifica qué cartas faltan en nuestra BD usando los códigos de MarvelCDB.
    El frontend pasa los códigos (code) de MarvelCDB, no los IDs.
    """
    """
    Verifica qué cartas faltan en nuestra base de datos.
    
    Request Body:
    {
        "card_codes": ["01001", "01002", "01003"]
    }
    
    Response:
    {
        "missing": ["01001", "01002"],
        "existing": ["01003"],
        "total_checked": 3
    }
    """
    try:
        card_codes = request_data.card_codes
        
        if not card_codes:
            return {
                "missing": [],
                "existing": [],
                "total_checked": 0
            }
        
        missing = []
        existing = []
        
        for code in card_codes:
            if card_exists_by_code(code):
                existing.append(code)
            else:
                missing.append(code)
        
        return {
            "missing": missing,
            "existing": existing,
            "total_checked": len(card_codes)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verificando cartas: {str(e)}"
        )

@app.post("/api/cards/import-missing", status_code=200)
async def import_missing_cards(
    request_data: ImportMissingRequest,
    request: Request
):
    """
    Importa cartas faltantes desde la API pública de MarvelCDB o desde los datos proporcionados por el frontend.
    
    Request Body (Opción 1 - Solo códigos):
    {
        "card_codes": ["01001", "01002"]
    }
    
    Request Body (Opción 2 - Datos completos):
    {
        "cards": [
            {
                "code": "01001",
                "name": "Spider-Man",
                "type_code": "hero",
                "faction_code": "hero",
                "pack_code": "core",
                "pack_name": "Core Set",
                "cost": 0,
                ...
            }
        ]
    }
    
    Request Body (Opción 3 - Ambos):
    {
        "card_codes": ["01001"],
        "cards": [
            {
                "code": "01002",
                "name": "Black Cat",
                ...
            }
        ]
    }
    
    Response:
    {
        "imported": 2,
        "failed": 0,
        "skipped": 0,
        "message": "2 cartas importadas exitosamente"
    }
    """
    try:
        # Asegurar que todas las columnas necesarias existan
        ensure_cards_columns()
        
        imported = 0
        failed = 0
        skipped = 0
        errors = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Procesar cartas con datos completos (si el frontend los proporciona)
        if request_data.cards:
            for card_data_pydantic in request_data.cards:
                try:
                    code = card_data_pydantic.code
                    
                    # Verificar si ya existe
                    if card_exists_by_code(code):
                        skipped += 1
                        print(f"⏭️  Carta {code} ya existe, omitiendo")
                        continue
                    
                    # Convertir el modelo Pydantic a dict
                    card_dict = card_data_pydantic.dict(exclude_none=True)
                    
                    # Asegurar que tenemos los campos mínimos
                    if not card_dict.get('name'):
                        failed += 1
                        errors.append({
                            "code": code,
                            "error": "La carta debe tener al menos 'code' y 'name'"
                        })
                        continue
                    
                    # Mapear a nuestra estructura
                    try:
                        card_data = map_marvelcdb_card_to_db(card_dict)
                    except Exception as e:
                        failed += 1
                        errors.append({
                            "code": code,
                            "error": f"Error mapeando carta: {str(e)}"
                        })
                        continue
                    
                    # Insertar en BD (mismo código que abajo)
                    try:
                        cursor.execute("PRAGMA table_info(cards)")
                        columns = [column[1] for column in cursor.fetchall()]
                        has_marvelcdb_code = 'marvelcdb_code' in columns
                        
                        if has_marvelcdb_code:
                            cursor.execute('''
                                INSERT OR IGNORE INTO cards (
                                    id, name, aspect, type, cost, set_name, set_code,
                                    pack_code, pack_name, faction_code, type_code, card_set,
                                    quantity, deck_limit, health, attack, threat, traits, text, is_unique, marvelcdb_code
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                card_data['id'],
                                card_data['name'],
                                card_data['aspect'],
                                card_data['type'],
                                card_data['cost'],
                                card_data['set_name'],
                                card_data['set_code'],
                                card_data['pack_code'],
                                card_data['pack_name'],
                                card_data['faction_code'],
                                card_data['type_code'],
                                card_data['card_set'],
                                card_data['quantity'],
                                card_data['deck_limit'],
                                card_data['health'],
                                card_data['attack'],
                                card_data['threat'],
                                card_data['traits'],
                                card_data['text'],
                                card_data['is_unique'],
                                card_data.get('marvelcdb_code', '')
                            ))
                        else:
                            cursor.execute('''
                                INSERT OR IGNORE INTO cards (
                                    id, name, aspect, type, cost, set_name, set_code,
                                    pack_code, pack_name, faction_code, type_code, card_set,
                                    quantity, deck_limit, health, attack, threat, traits, text, is_unique
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                card_data['id'],
                                card_data['name'],
                                card_data['aspect'],
                                card_data['type'],
                                card_data['cost'],
                                card_data['set_name'],
                                card_data['set_code'],
                                card_data['pack_code'],
                                card_data['pack_name'],
                                card_data['faction_code'],
                                card_data['type_code'],
                                card_data['card_set'],
                                card_data['quantity'],
                                card_data['deck_limit'],
                                card_data['health'],
                                card_data['attack'],
                                card_data['threat'],
                                card_data['traits'],
                                card_data['text'],
                                card_data['is_unique']
                            ))
                        
                        if cursor.rowcount > 0:
                            imported += 1
                            print(f"✅ Carta {code} ({card_data['name']}) importada desde datos del frontend")
                        else:
                            skipped += 1
                            print(f"⏭️  Carta {code} ya existía")
                    
                    except Exception as e:
                        failed += 1
                        errors.append({
                            "code": code,
                            "error": f"Error insertando en BD: {str(e)}"
                        })
                        print(f"❌ Error insertando carta {code}: {e}")
                
                except Exception as e:
                    failed += 1
                    errors.append({
                        "code": card_data_pydantic.code if hasattr(card_data_pydantic, 'code') else 'unknown',
                        "error": f"Error procesando carta: {str(e)}"
                    })
                    print(f"❌ Error procesando carta: {e}")
        
        # Procesar códigos (buscar desde MarvelCDB)
        card_codes = request_data.card_codes or []
        
        if not card_codes and not request_data.cards:
            conn.close()
            return {
                "imported": imported,
                "failed": failed,
                "skipped": skipped,
                "message": f"{imported} carta(s) importada(s), {failed} fallaron, {skipped} omitidas",
                "errors": errors if errors else None
            }
        
        for code in card_codes:
            try:
                # Verificar si ya existe
                if card_exists_by_code(code):
                    skipped += 1
                    print(f"⏭️  Carta {code} ya existe, omitiendo")
                    continue
                
                # Obtener carta desde MarvelCDB
                print(f"📡 Obteniendo carta {code} desde MarvelCDB...")
                try:
                    response = requests.get(
                        f"{MARVELCDB_API_BASE}/card/{code}",
                        timeout=10
                    )
                    response.raise_for_status()  # Lanza excepción si status != 200
                except requests.RequestException as e:
                    failed += 1
                    error_msg = f"Error obteniendo carta desde MarvelCDB: {str(e)}"
                    errors.append({
                        "code": code,
                        "error": error_msg
                    })
                    print(f"❌ {error_msg}")
                    continue
                
                try:
                    marvelcdb_card = response.json()
                except json.JSONDecodeError as e:
                    failed += 1
                    error_msg = f"Error parseando JSON de MarvelCDB: {str(e)}"
                    errors.append({
                        "code": code,
                        "error": error_msg
                    })
                    print(f"❌ {error_msg}")
                    continue
                
                # Log de debugging: mostrar campos importantes
                print(f"📋 Campos importantes de la API para carta {code}:")
                print(f"   - code: {marvelcdb_card.get('code')}")
                print(f"   - name: {marvelcdb_card.get('name')}")
                print(f"   - type_code: {marvelcdb_card.get('type_code')}")
                print(f"   - faction_code: {marvelcdb_card.get('faction_code')}")
                print(f"   - pack_code: {marvelcdb_card.get('pack_code')}")
                print(f"   - pack_name: {marvelcdb_card.get('pack_name')}")
                
                # Mapear a nuestra estructura (con manejo de errores robusto)
                try:
                    card_data = map_marvelcdb_card_to_db(marvelcdb_card)
                    
                    # Log de debugging para héroes y aspectos
                    if card_data.get('type') == 'hero':
                        print(f"   🦸 Héroe detectado: {card_data.get('name')} (aspect: {card_data.get('aspect')})")
                    if card_data.get('aspect') in ['aggression', 'justice', 'leadership', 'protection', 'pool']:
                        print(f"   🎯 Carta de aspecto {card_data.get('aspect')}: {card_data.get('name')}")
                        
                except Exception as e:
                    failed += 1
                    error_msg = f"Error mapeando carta: {str(e)}"
                    errors.append({
                        "code": code,
                        "error": error_msg
                    })
                    print(f"❌ {error_msg}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                # Insertar en la base de datos con INSERT OR IGNORE para evitar duplicados
                try:
                    # Verificar si la columna marvelcdb_code existe
                    cursor.execute("PRAGMA table_info(cards)")
                    columns = [column[1] for column in cursor.fetchall()]
                    has_marvelcdb_code = 'marvelcdb_code' in columns
                    
                    if has_marvelcdb_code:
                        cursor.execute('''
                            INSERT OR IGNORE INTO cards (
                                id, name, aspect, type, cost, set_name, set_code,
                                pack_code, pack_name, faction_code, type_code, card_set,
                                quantity, deck_limit, health, attack, threat, traits, text, is_unique, marvelcdb_code
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            card_data['id'],
                            card_data['name'],
                            card_data['aspect'],
                            card_data['type'],
                            card_data['cost'],
                            card_data['set_name'],
                            card_data['set_code'],
                            card_data['pack_code'],
                            card_data['pack_name'],
                            card_data['faction_code'],
                            card_data['type_code'],
                            card_data['card_set'],
                            card_data['quantity'],
                            card_data['deck_limit'],
                            card_data['health'],
                            card_data['attack'],
                            card_data['threat'],
                            card_data['traits'],
                            card_data['text'],
                            card_data['is_unique'],
                            card_data.get('marvelcdb_code', '')  # Guardar el code de MarvelCDB
                        ))
                    else:
                        # Fallback si la columna no existe (para compatibilidad)
                        cursor.execute('''
                            INSERT OR IGNORE INTO cards (
                                id, name, aspect, type, cost, set_name, set_code,
                                pack_code, pack_name, faction_code, type_code, card_set,
                                quantity, deck_limit, health, attack, threat, traits, text, is_unique
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            card_data['id'],
                            card_data['name'],
                            card_data['aspect'],
                            card_data['type'],
                            card_data['cost'],
                            card_data['set_name'],
                            card_data['set_code'],
                            card_data['pack_code'],
                            card_data['pack_name'],
                            card_data['faction_code'],
                            card_data['type_code'],
                            card_data['card_set'],
                            card_data['quantity'],
                            card_data['deck_limit'],
                            card_data['health'],
                            card_data['attack'],
                            card_data['threat'],
                            card_data['traits'],
                            card_data['text'],
                            card_data['is_unique']
                        ))
                    
                    # Verificar si realmente se insertó (puede que ya existiera)
                    if cursor.rowcount > 0:
                        imported += 1
                        print(f"✅ Carta {code} ({card_data['name']}) importada exitosamente")
                        print(f"   - ID en BD: {card_data['id']}")
                        print(f"   - MarvelCDB Code: {card_data.get('marvelcdb_code', 'N/A')}")
                        print(f"   - Aspect (clase): {card_data['aspect']}")
                        print(f"   - Type: {card_data['type']}")
                        print(f"   - Faction Code: {card_data['faction_code']}")
                    else:
                        # La carta ya existe, pero puede que no tenga marvelcdb_code
                        # Intentar actualizar el marvelcdb_code si falta
                        if has_marvelcdb_code:
                            cursor.execute('''
                                UPDATE cards 
                                SET marvelcdb_code = ? 
                                WHERE id = ? AND (marvelcdb_code IS NULL OR marvelcdb_code = '')
                            ''', (code, card_data['id']))
                            if cursor.rowcount > 0:
                                print(f"✅ Actualizado marvelcdb_code para carta {code} (ID: {card_data['id']})")
                                imported += 1  # Contar como importada si se actualizó
                            else:
                                skipped += 1
                                print(f"⏭️  Carta {code} ya existía (INSERT OR IGNORE)")
                        else:
                            skipped += 1
                            print(f"⏭️  Carta {code} ya existía (INSERT OR IGNORE)")
                        
                        # Verificar qué tiene en BD (buscar por marvelcdb_code si existe, sino por id)
                        if has_marvelcdb_code:
                            cursor.execute('SELECT id, name, aspect, type, faction_code, marvelcdb_code FROM cards WHERE marvelcdb_code = ? OR id = ?', (code, card_data['id']))
                        else:
                            cursor.execute('SELECT id, name, aspect, type, faction_code FROM cards WHERE id = ?', (card_data['id'],))
                        existing = cursor.fetchone()
                        if existing:
                            print(f"   - En BD: ID={existing[0]}, Aspect={existing[2]}, Type={existing[3]}, Faction={existing[4]}")
                            if has_marvelcdb_code and len(existing) > 5:
                                print(f"   - MarvelCDB Code en BD: {existing[5]}")
                        
                except sqlite3.IntegrityError as e:
                    # Si hay error de integridad (duplicado), omitir
                    skipped += 1
                    print(f"⏭️  Carta {code} ya existe (error de integridad)")
                except Exception as e:
                    failed += 1
                    error_msg = f"Error guardando en BD: {str(e)}"
                    errors.append({
                        "code": code,
                        "error": error_msg
                    })
                    print(f"❌ {error_msg}")
                
            except requests.RequestException as e:
                failed += 1
                error_msg = f"Error obteniendo carta desde MarvelCDB: {str(e)}"
                errors.append({
                    "code": code,
                    "error": error_msg
                })
                print(f"❌ {error_msg}")
            except Exception as e:
                failed += 1
                error_msg = f"Error procesando carta: {str(e)}"
                errors.append({
                    "code": code,
                    "error": error_msg
                })
                print(f"❌ {error_msg}")
        
        conn.commit()
        conn.close()
        
        # Construir mensaje
        message_parts = []
        if imported > 0:
            message_parts.append(f"{imported} carta(s) importada(s)")
        if failed > 0:
            message_parts.append(f"{failed} fallaron")
        if skipped > 0:
            message_parts.append(f"{skipped} omitida(s)")
        
        message = ", ".join(message_parts) if message_parts else "Ninguna acción realizada"
        
        response_data = {
            "imported": imported,
            "failed": failed,
            "skipped": skipped,
            "message": message
        }
        
        if errors:
            response_data["errors"] = errors
        
        return response_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importando cartas: {str(e)}"
        )

if __name__ == "__main__":
    # Inicializar tabla de usuarios al arrancar
    init_users_table()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
