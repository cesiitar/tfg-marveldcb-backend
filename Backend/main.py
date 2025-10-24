from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
import re
from typing import List, Dict, Optional

app = FastAPI(title="MarvelCDB API", version="1.0.0")

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
        "https://cesiitar.github.io",  # GitHub Pages (si planeas usar GitHub Pages)
        "https://tfg-marveldcb-frontend.vercel.app",  # Vercel (ejemplo)
        "https://tfg-marveldcb-frontend.netlify.app"   # Netlify (ejemplo)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
    return conn

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

    # user_id para asociar el mazo al creador
    if 'user_id' not in columns:
        cursor.execute('ALTER TABLE decks ADD COLUMN user_id TEXT')
        altered = True

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
            user_id TEXT NOT NULL,           -- auth0_sub del usuario
            deck_id INTEGER NOT NULL,        -- ID del mazo
            difficulty TEXT NOT NULL,        -- "normal" o "expert"
            villain TEXT NOT NULL,           -- Nombre del villano
            result TEXT NOT NULL,            -- "win" o "loss"
            played_at TEXT NOT NULL,         -- Timestamp ISO de cuándo se jugó
            created_at TEXT DEFAULT (datetime('now', 'localtime'))  -- Cuándo se guardó
        )
    ''')
    
    conn.commit()
    conn.close()

# =============================================================================
# UTILIDADES DE ESQUEMA (cards)
# =============================================================================
def ensure_cards_columns():
    """Garantiza que la tabla cards tenga columnas requeridas (p. ej., deck_limit)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(cards)")
    columns = [column[1] for column in cursor.fetchall()]

    altered = False
    if 'deck_limit' not in columns:
        cursor.execute('ALTER TABLE cards ADD COLUMN deck_limit INTEGER')
        altered = True

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
    """Obtener todos los nombres únicos de sets de villanos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener solo los nombres únicos de card_set de villanos
    cursor.execute('''
        SELECT DISTINCT card_set
        FROM cards 
        WHERE type = 'villain' AND card_set IS NOT NULL
        ORDER BY card_set
    ''')
    
    villains = []
    for row in cursor.fetchall():
        villains.append(row["card_set"])
    
    conn.close()
    return villains

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
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si existe la columna user_id
    cursor.execute("PRAGMA table_info(decks)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Incluir mazos legacy donde is_public pueda ser NULL y también mazos de usuario
    # Mostrar todo lo que sea público (1) o legacy (NULL). Todos los mazos creados por usuarios se guardan como públicos.
    if 'user_id' in columns:
        cursor.execute('''
            SELECT id, name, description, hero_name, hero_id, aspect, cards, created_at, user_id
            FROM decks 
            WHERE is_public = 1 OR is_public IS NULL
            ORDER BY created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT id, name, description, hero_name, aspect, cards, created_at
            FROM decks 
            WHERE is_public = 1 OR is_public IS NULL
            ORDER BY created_at DESC
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
            "creator_name": creator_name
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
    """Crear un nuevo mazo"""
    try:
        ensure_decks_columns()
        auth0_id = request.headers.get('X-Auth0-ID')
        
        # Debug log
        print(f"🔍 POST /api/decks - Auth0_ID recibido: {auth0_id}")
        print(f"📦 Datos recibidos: {deck_data}")
        
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
        
        # Validar datos requeridos
        if not deck_data.get('name') or not deck_data.get('hero_name') or not deck_data.get('cards') or not deck_data.get('aspect'):
            print(f"❌ Campos faltantes - name: {deck_data.get('name')}, hero_name: {deck_data.get('hero_name')}, cards: {deck_data.get('cards')}, aspect: {deck_data.get('aspect')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: name, hero_name, aspect, cards"
            )
        # Validar aspect permitido
        aspect = deck_data.get('aspect')
        allowed_aspects = {"aggression", "justice", "leadership", "protection"}
        if aspect not in allowed_aspects:
            print(f"❌ Aspect inválido: {aspect}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid aspect. Allowed: aggression, justice, leadership, protection"
            )
        
        print(f"✅ Aspect válido: {aspect}")
        
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
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
            user["id"]  # ID numérico del usuario
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
                "creator_name": user.get("name")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating deck: {str(e)}"
        )

@app.post("/api/game-configurations", status_code=201)
async def create_game_configuration(config_data: dict, request: Request):
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
        required_fields = ['deck_id', 'difficulty', 'villain', 'result', 'played_at']
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
        
        # Validar que el deck pertenece al usuario
        deck_id = config_data.get('deck_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM decks WHERE id = ? AND user_id = ?
        ''', (deck_id, user['id']))
        
        deck_row = cursor.fetchone()
        if not deck_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Deck not found or does not belong to user"
            )
        
        # Validar que el villano existe
        villain = config_data.get('villain')
        cursor.execute('''
            SELECT COUNT(*) FROM cards WHERE type = 'villain' AND card_set = ?
        ''', (villain,))
        
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
                user_id, deck_id, difficulty, villain, result, played_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user['id'],
            deck_id,
            difficulty,
            villain,
            result,
            config_data.get('played_at')
        ))
        
        game_config_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Configuración de partida creada: ID={game_config_id}")
        
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

@app.get("/api/decks/{deck_id}")
async def get_deck(deck_id: int):
    """Obtener un mazo específico por ID"""
    ensure_decks_columns()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, description, hero_name, hero_id, aspect, cards, created_at
        FROM decks 
        WHERE id = ? AND is_public = 1
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
        "creator_name": creator_name
    }
    
    print(f"📤 Devolviendo mazo con descripción: '{row['description']}'")
    
    conn.close()
    return deck

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
        
        cursor.execute('''
            SELECT id, name, description, hero_name, hero_id, aspect, cards, created_at, is_public
            FROM decks 
            WHERE user_id = ?
            ORDER BY created_at DESC
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
                "creator_name": creator_name
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
        
        # Eliminar el mazo
        cursor.execute('DELETE FROM decks WHERE id = ? AND user_id = ?', (deck_id, user["id"]))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Deck deleted successfully",
            "deck_id": deck_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

if __name__ == "__main__":
    # Inicializar tabla de usuarios al arrancar
    init_users_table()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
