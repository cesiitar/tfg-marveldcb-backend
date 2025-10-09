from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3
import json
import jwt
import requests
from typing import List, Dict, Optional

app = FastAPI(title="MarvelCDB API", version="1.0.0")

# Configuración Auth0
AUTH0_DOMAIN = "dev-zomq55rx35nuubga.eu.auth0.com"
AUTH0_AUDIENCE = "http://localhost:8000/api"
AUTH0_ISSUER = f"https://{AUTH0_DOMAIN}/"

# Configurar seguridad HTTPBearer
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verificar token JWT de Auth0"""
    token = credentials.credentials
    
    try:
        # Obtener las claves públicas de Auth0
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        jwks_response = requests.get(jwks_url)
        jwks = jwks_response.json()
        
        # Decodificar el header del token para obtener el kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        # Buscar la clave pública correspondiente
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break
        
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clave pública no encontrada"
            )
        
        # Verificar y decodificar el token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=AUTH0_ISSUER
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error verificando token: {str(e)}"
        )

def verify_user_in_db(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verificar token JWT de Auth0 y usuario en base de datos"""
    token = credentials.credentials
    
    try:
        # Obtener las claves públicas de Auth0
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        jwks_response = requests.get(jwks_url)
        jwks = jwks_response.json()
        
        # Decodificar el header del token para obtener el kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        # Buscar la clave pública correspondiente
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break
        
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clave pública no encontrada"
            )
        
        # Verificar y decodificar el token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=AUTH0_ISSUER
        )
        
        # Verificar si el usuario existe en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, auth0_id, email, name, picture_url, created_at
            FROM users 
            WHERE auth0_id = ?
        ''', (payload.get("sub"),))
        
        user_row = cursor.fetchone()
        conn.close()
        
        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no existe en la base de datos. Debes registrarte primero."
            )
        
        # Combinar payload del token con datos del usuario
        user_data = {
            "id": user_row["id"],
            "auth0_id": user_row["auth0_id"],
            "email": user_row["email"],
            "name": user_row["name"],
            "picture_url": user_row["picture_url"],
            "created_at": user_row["created_at"]
        }
        
        return user_data
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error verificando usuario: {str(e)}"
        )

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

@app.get("/api/cards")
async def get_all_cards():
    """Obtener todas las cartas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, aspect, type, cost, set_name
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
            "set": row["set_name"]  # Ahora contiene el nombre completo
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
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si existe la columna user_id
    cursor.execute("PRAGMA table_info(decks)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'user_id' in columns:
        cursor.execute('''
            SELECT id, name, description, hero_name, aspect, cards, created_at, user_id
            FROM decks 
            WHERE is_public = 1
            ORDER BY created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT id, name, description, hero_name, aspect, cards, created_at
            FROM decks 
            WHERE is_public = 1
            ORDER BY created_at DESC
        ''')
    
    decks = []
    for row in cursor.fetchall():
        try:
            cards_data = json.loads(row["cards"]) if row["cards"] else []
        except json.JSONDecodeError:
            cards_data = []
        
        deck = {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "heroName": row["hero_name"],
            "aspect": row["aspect"],
            "cards": cards_data,
            "createdAt": row["created_at"]
        }
        
        # Añadir información del usuario si existe
        if 'user_id' in columns and row.get("user_id"):
            deck["userId"] = row["user_id"]
        
        decks.append(deck)
    
    conn.close()
    return {"decks": decks}

@app.post("/api/decks")
async def create_deck(deck_data: dict, user: dict = Depends(verify_user_in_db)):
    """Crear un nuevo mazo público"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Primero verificar si la tabla decks tiene la columna user_id
        cursor.execute("PRAGMA table_info(decks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            # Añadir la columna user_id si no existe
            cursor.execute('ALTER TABLE decks ADD COLUMN user_id TEXT')
        
        cursor.execute('''
            INSERT INTO decks (name, description, hero_name, aspect, cards, is_public, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            deck_data.get("name", ""),
            deck_data.get("description", ""),
            deck_data.get("heroName", ""),
            deck_data.get("aspect", ""),
            json.dumps(deck_data.get("cards", [])),
            1,  # Siempre público por ahora
            user.get("auth0_id")  # ID del usuario de Auth0
        ))
        
        deck_id = cursor.lastrowid
        conn.commit()
        
        return {"id": deck_id, "message": "Mazo creado exitosamente"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando mazo: {str(e)}")
    
    finally:
        conn.close()

@app.get("/api/decks/{deck_id}")
async def get_deck(deck_id: int):
    """Obtener un mazo específico por ID"""
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
        cards_data = json.loads(row["cards"]) if row["cards"] else []
    except json.JSONDecodeError:
        cards_data = []
    
    deck = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "heroName": row["hero_name"],
        "aspect": row["aspect"],
        "cards": cards_data,
        "createdAt": row["created_at"]
    }
    
    conn.close()
    return deck

# =============================================================================
# ENDPOINTS PROTEGIDOS (requieren autenticación)
# =============================================================================

@app.get("/api/user/profile")
async def get_user_profile(user: dict = Depends(verify_user_in_db)):
    """Obtener perfil del usuario autenticado"""
    return {
        "user": {
            "id": user.get("id"),
            "auth0_id": user.get("auth0_id"),
            "email": user.get("email"),
            "name": user.get("name"),
            "picture_url": user.get("picture_url"),
            "created_at": user.get("created_at")
        }
    }

@app.get("/api/user/decks")
async def get_user_decks(user: dict = Depends(verify_user_in_db)):
    """Obtener mazos del usuario autenticado"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_id = user.get("auth0_id")
    
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
    ''', (user_id,))
    
    decks = []
    for row in cursor.fetchall():
        try:
            cards_data = json.loads(row["cards"]) if row["cards"] else []
        except json.JSONDecodeError:
            cards_data = []
        
        deck = {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "heroName": row["hero_name"],
            "aspect": row["aspect"],
            "cards": cards_data,
            "createdAt": row["created_at"],
            "isPublic": bool(row["is_public"])
        }
        decks.append(deck)
    
    conn.close()
    return {"decks": decks}

@app.put("/api/user/decks/{deck_id}")
async def update_user_deck(deck_id: int, deck_data: dict, user: dict = Depends(verify_user_in_db)):
    """Actualizar un mazo del usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_id = user.get("auth0_id")
    
    # Verificar si el mazo pertenece al usuario
    cursor.execute('''
        SELECT id FROM decks 
        WHERE id = ? AND user_id = ?
    ''', (deck_id, user_id))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Mazo no encontrado o no tienes permisos")
    
    try:
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
            user_id
        ))
        
        conn.commit()
        return {"message": "Mazo actualizado exitosamente"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando mazo: {str(e)}")
    
    finally:
        conn.close()

@app.delete("/api/user/decks/{deck_id}")
async def delete_user_deck(deck_id: int, user: dict = Depends(verify_user_in_db)):
    """Eliminar un mazo del usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_id = user.get("auth0_id")
    
    # Verificar si el mazo pertenece al usuario
    cursor.execute('''
        SELECT id FROM decks 
        WHERE id = ? AND user_id = ?
    ''', (deck_id, user_id))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Mazo no encontrado o no tienes permisos")
    
    try:
        cursor.execute('''
            DELETE FROM decks 
            WHERE id = ? AND user_id = ?
        ''', (deck_id, user_id))
        
        conn.commit()
        return {"message": "Mazo eliminado exitosamente"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error eliminando mazo: {str(e)}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    # Inicializar tabla de usuarios al arrancar
    init_users_table()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
