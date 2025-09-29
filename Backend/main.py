from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
from typing import List, Dict, Optional

app = FastAPI(title="MarvelCDB API", version="1.0.0")

# Configurar CORS para permitir requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
    return conn

@app.get("/")
async def root():
    return {"message": "MarvelCDB API está funcionando!"}

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
        cursor.execute('SELECT COUNT(*) FROM cards WHERE set_name = ?', (row["code"],))
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
        SELECT name, aspect, type, cost
        FROM cards 
        WHERE set_name = ?
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
            "set": set_name
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
            "aspect": row["aspect"],
            "type": row["type"],
            "cost": row["cost"],
            "set": row["set_name"]
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
            "aspect": row["aspect"],
            "type": row["type"],
            "cost": row["cost"],
            "set": row["set_name"]
        }
        cards.append(card)
    
    conn.close()
    return {"cards": cards}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)