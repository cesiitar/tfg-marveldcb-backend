from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
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

    if altered:
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
        SELECT name, aspect, type, cost, set_name
        FROM cards 
        WHERE set_code = ?
    '''
    params = [set_code]
    
    # Añadir filtro de búsqueda si se proporciona
    if search:
        query += ' AND name LIKE ?'
        params.append(f'%{search}%')
    
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
    
    cursor.execute('''
        SELECT DISTINCT name, pack_name, cost
        FROM cards 
        WHERE type = 'hero'
        ORDER BY pack_name, name
    ''')
    
    heroes = []
    for row in cursor.fetchall():
        heroes.append({
            "name": row["name"],
            "pack_name": row["pack_name"],
            "cost": row["cost"]
        })
    
    conn.close()
    return heroes  # Devolver array directo como espera el frontend

@app.get("/api/heroes/{hero_name}/cards")
async def get_hero_cards(hero_name: str):
    """Obtener las cartas específicas del héroe (excluyendo la carta del héroe)"""
    ensure_cards_columns()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar las cartas que pertenecen al set del héroe específico
    # EXCLUIR la carta del héroe (type = 'hero') y solo incluir cartas del aspecto 'hero'
    cursor.execute('''
        SELECT name, cost, type, aspect, card_set, quantity, deck_limit
        FROM cards 
        WHERE card_set = ? 
        AND type != 'hero' 
        AND LOWER(type) != 'alter_ego' 
        AND LOWER(type) != 'alter-ego'
        AND aspect = 'hero'
        ORDER BY type, cost, name
    ''', (hero_name,))
    
    cards = []
    for row in cursor.fetchall():
        cards.append({
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
        SELECT name, cost, type, aspect, pack_name, quantity, deck_limit
        FROM cards 
        WHERE aspect = ?
        ORDER BY type, cost, name
    ''', (aspect,))
    
    cards = []
    for row in cursor.fetchall():
        cards.append({
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
        params.append(f'%{name}%')
    
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
            SELECT id, name, description, hero_name, aspect, cards, created_at, user_id
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
        # Normalizar a formato { card_name, quantity, type, clase }
        cards_data = []
        for c in raw_cards:
            card_name = c.get("card_name") or c.get("name") or c.get("code")
            # Buscar información adicional de la carta en la tabla cards
            cursor.execute('SELECT type, aspect, pack_name FROM cards WHERE name = ?', (card_name,))
            card_info = cursor.fetchone()
            
            card_data = {
                "card_name": card_name,
                "quantity": c.get("quantity", 1)
            }
            
            if card_info:
                card_data["type"] = card_info["type"]
                card_data["clase"] = card_info["aspect"]
                card_data["set"] = card_info["pack_name"] or "Unknown"
            
            cards_data.append(card_data)
        
        # Obtener nombre del creador si existe user_id
        creator_name = None
        if 'user_id' in columns:
            try:
                uid = row["user_id"]
                if uid:
                    cursor.execute('SELECT name FROM users WHERE auth0_id = ?', (uid,))
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
        
        # Validar datos requeridos
        if not deck_data.get('name') or not deck_data.get('hero_name') or not deck_data.get('cards') or not deck_data.get('aspect'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: name, hero_name, aspect, cards"
            )
        # Validar aspect permitido
        aspect = deck_data.get('aspect')
        allowed_aspects = {"aggression", "justice", "leadership", "protection"}
        if aspect not in allowed_aspects:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid aspect. Allowed: aggression, justice, leadership, protection"
            )
        
        # Validar que el mazo tenga exactamente 40 cartas (sin contar el héroe)
        cards = deck_data.get('cards', [])
        # Validar quantity > 0 y entero
        for card in cards:
            quantity = card.get('quantity', 0)
            if not isinstance(quantity, int) or quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each card quantity must be a positive integer"
                )
        total_cards = sum(card.get('quantity', 1) for card in cards)
        
        if total_cards != 40:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deck must have exactly 40 cards (excluding hero). Current: {total_cards} cards"
            )
        
        # Validar que todas las cartas existan en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for card in cards:
            card_name = card.get('card_name', card.get('name', ''))
            cursor.execute('SELECT name, deck_limit FROM cards WHERE name = ?', (card_name,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Card '{card_name}' does not exist in database"
                )
            # Enforce deck_limit si existe
            deck_limit = None
            try:
                deck_limit = row["deck_limit"]
            except Exception:
                deck_limit = None
            if deck_limit is not None and isinstance(deck_limit, int):
                if card.get('quantity', 1) > deck_limit:
                    conn.close()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card '{card_name}' exceeds deck limit ({deck_limit})"
                    )
        
        # Reutilizar la conexión existente
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Primero verificar si la tabla decks tiene la columna user_id
        cursor.execute("PRAGMA table_info(decks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            # Añadir la columna user_id si no existe
            cursor.execute('ALTER TABLE decks ADD COLUMN user_id TEXT')
        
        # Procesar cartas para el formato correcto
        processed_cards = []
        for card in deck_data.get('cards', []):
            processed_cards.append({
                "card_name": card.get('card_name', card.get('name', '')),
                "quantity": card.get('quantity', 1)
            })
        
        cursor.execute('''
            INSERT INTO decks (name, description, hero_name, aspect, cards, is_public, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            deck_data.get("name", ""),
            deck_data.get("description", ""),
            deck_data.get("hero_name", ""),
            deck_data.get("aspect"),
            json.dumps(processed_cards),
            1,  # Siempre público por ahora
            auth0_id  # ID del usuario de Auth0
        ))
        
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

@app.get("/api/decks/{deck_id}")
async def get_deck(deck_id: int):
    """Obtener un mazo específico por ID"""
    ensure_decks_columns()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, description, hero_name, aspect, cards, created_at
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
    
    # Normalizar a formato { card_name, quantity, type, clase }
    cards_data = []
    for c in raw_cards:
        card_name = c.get("card_name") or c.get("name") or c.get("code")
        # Buscar información adicional de la carta en la tabla cards
        cursor.execute('SELECT type, aspect, pack_name FROM cards WHERE name = ?', (card_name,))
        card_info = cursor.fetchone()
        
        card_data = {
            "card_name": card_name,
            "quantity": c.get("quantity", 1)
        }
        
        if card_info:
            card_data["type"] = card_info["type"]
            card_data["clase"] = card_info["aspect"]
            card_data["set"] = card_info["pack_name"] or "Unknown"
        
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
                cursor.execute('SELECT name FROM users WHERE auth0_id = ?', (uid_row[0],))
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
        "aspect": row["aspect"],
        "cards": cards_data,
        "created_at": row["created_at"],
        "creator_name": creator_name
    }
    
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
        
        # Contar mazos del usuario usando el Auth0 ID almacenado en decks.user_id
        cursor.execute('SELECT COUNT(*) FROM decks WHERE user_id = ?', (auth0_id,))
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
            SELECT id, name, description, hero_name, aspect, cards, created_at, is_public
            FROM decks 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (auth0_id,))
        
        decks = []
        for row in cursor.fetchall():
            try:
                raw_cards = json.loads(row["cards"]) if row["cards"] else []
            except json.JSONDecodeError:
                raw_cards = []
            # Normalizar a formato { card_name, quantity, type, clase }
            cards_data = []
            for c in raw_cards:
                card_name = c.get("card_name") or c.get("name") or c.get("code")
                # Buscar información adicional de la carta en la tabla cards
                cursor.execute('SELECT type, aspect, pack_name FROM cards WHERE name = ?', (card_name,))
                card_info = cursor.fetchone()
                
                card_data = {
                    "card_name": card_name,
                    "quantity": c.get("quantity", 1)
                }
                
                if card_info:
                    card_data["type"] = card_info["type"]
                    card_data["clase"] = card_info["aspect"]
                    card_data["set"] = card_info["pack_name"] or "Unknown"
                
                cards_data.append(card_data)
            
            # Obtener nombre del creador (el propio usuario)
            creator_name = user.get("name")

            deck = {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "hero_name": row["hero_name"],
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

@app.put("/api/user/decks/{deck_id}")
async def update_user_deck(deck_id: int, deck_data: dict, request: Request):
    """Actualizar un mazo del usuario"""
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el mazo pertenece al usuario
        cursor.execute('''
            SELECT id FROM decks 
            WHERE id = ? AND user_id = ?
        ''', (deck_id, auth0_id))
        
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mazo no encontrado o no tienes permisos"
            )
        
        cursor.execute('''
            UPDATE decks 
            SET name = ?, description = ?, hero_name = ?, aspect = ?, cards = ?
            WHERE id = ? AND user_id = ?
        ''', (
            deck_data.get("name", ""),
            deck_data.get("description", ""),
            deck_data.get("heroName", ""),
            deck_data.get("aspect", ""),
            json.dumps(deck_data.get("cards", [])),
            deck_id,
            auth0_id
        ))
        
        conn.commit()
        conn.close()
        
        return {"message": "Mazo actualizado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.delete("/api/user/decks/{deck_id}")
async def delete_user_deck(deck_id: int, request: Request):
    """Eliminar un mazo del usuario"""
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el mazo pertenece al usuario
        cursor.execute('''
            SELECT id FROM decks 
            WHERE id = ? AND user_id = ?
        ''', (deck_id, auth0_id))
        
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mazo no encontrado o no tienes permisos"
            )
        
        cursor.execute('''
            DELETE FROM decks 
            WHERE id = ? AND user_id = ?
        ''', (deck_id, auth0_id))
        
        conn.commit()
        conn.close()
        
        return {"message": "Mazo eliminado exitosamente"}
        
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
