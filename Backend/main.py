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
        SELECT id, name, description, release_date 
        FROM card_sets 
        ORDER BY id
    ''')
    
    # Mapeo de nombres a códigos
    set_code_mapping = {
        "Core Set": "core",
        "The Green Goblin": "gob", 
        "Captain America": "cap",
        "Ms. Marvel": "msm",
        "Thor": "thor",
        "The Wrecking Crew": "twc",
        "Black Widow": "bkw",
        "Doctor Strange": "drs",
        "Hulk": "hlk",
        "Ronan Modular Set": "ron",
        "The Rise of Red Skull": "trors",
        "The Once and Future Kang": "toafk",
        "Ant-Man": "ant",
        "Wasp": "wsp",
        "Quicksilver": "qsv",
        "Scarlet Witch": "scw",
        "The Galaxy's Most Wanted": "gmw",
        "Star-Lord": "stld",
        "Gamora": "gam",
        "Drax": "drax",
        "Venom": "vnm",
        "The Mad Titan's Shadow": "mts",
        "Nebula": "nebu",
        "War Machine": "warm",
        "The Hood": "hood",
        "Valkyrie": "valk",
        "Vision": "vision",
        "Sinister Motives": "sm",
        "Nova": "nova",
        "Ironheart": "ironheart",
        "Spider-Ham": "spiderham",
        "SP//dr": "spdr",
        "Mutant Genesis": "mut_gen",
        "Cyclops": "cyclops",
        "Phoenix": "phoenix",
        "Wolverine": "wolv",
        "Storm": "storm",
        "Mojo Mania": "mm",
        "Gambit": "gambit",
        "Rogue": "rogue",
        "NeXt Evolution": "next_evol",
        "Psylocke": "psylocke",
        "Angel": "angel",
        "X-23": "x23",
        "Deadpool": "deadpool",
        "Age of Apocalypse": "aoa",
        "Iceman": "iceman",
        "Jubilee": "jubilee",
        "Nightcrawler": "ncrawler",
        "Magneto": "magneto",
        "Agents of S.H.I.E.L.D.": "aos",
        "Black Panther": "bp",
        "Silk": "silk",
        "Falcon": "falcon",
        "Winter Soldier": "winter"
    }
    
    sets = []
    for row in cursor.fetchall():
        set_name = row["name"]
        set_code = set_code_mapping.get(set_name, set_name.lower().replace(" ", "_"))
        
        # Contar cartas reales
        cursor.execute('SELECT COUNT(*) FROM cards WHERE set_name = ?', (set_code,))
        real_card_count = cursor.fetchone()[0]
        
        sets.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "releaseDate": row["release_date"],
            "cardCount": real_card_count
        })
    
    conn.close()
    return {"sets": sets}

@app.get("/api/sets/{set_id}/cards")
async def get_cards_by_set(set_id: int):
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
    
    # Mapear nombres de sets a códigos
    set_code_mapping = {
        "Core Set": "core",
        "The Green Goblin": "gob", 
        "Captain America": "cap",
        "Ms. Marvel": "msm",
        "Thor": "thor",
        "The Wrecking Crew": "twc",
        "Black Widow": "bkw",
        "Doctor Strange": "drs",
        "Hulk": "hlk",
        "Ronan Modular Set": "ron",
        "The Rise of Red Skull": "trors",
        "The Once and Future Kang": "toafk",
        "Ant-Man": "ant",
        "Wasp": "wsp",
        "Quicksilver": "qsv",
        "Scarlet Witch": "scw",
        "The Galaxy's Most Wanted": "gmw",
        "Star-Lord": "stld",
        "Gamora": "gam",
        "Drax": "drax",
        "Venom": "vnm",
        "The Mad Titan's Shadow": "mts",
        "Nebula": "nebu",
        "War Machine": "warm",
        "The Hood": "hood",
        "Valkyrie": "valk",
        "Vision": "vision",
        "Sinister Motives": "sm",
        "Nova": "nova",
        "Ironheart": "ironheart",
        "Spider-Ham": "spiderham",
        "SP//dr": "spdr",
        "Mutant Genesis": "mut_gen",
        "Cyclops": "cyclops",
        "Phoenix": "phoenix",
        "Wolverine": "wolv",
        "Storm": "storm",
        "Mojo Mania": "mm",
        "Gambit": "gambit",
        "Rogue": "rogue",
        "NeXt Evolution": "next_evol",
        "Psylocke": "psylocke",
        "Angel": "angel",
        "X-23": "x23",
        "Deadpool": "deadpool",
        "Age of Apocalypse": "aoa",
        "Iceman": "iceman",
        "Jubilee": "jubilee",
        "Nightcrawler": "ncrawler",
        "Magneto": "magneto",
        "Agents of S.H.I.E.L.D.": "aos",
        "Black Panther": "bp",
        "Silk": "silk",
        "Falcon": "falcon",
        "Winter Soldier": "winter"
    }
    
    set_code = set_code_mapping.get(set_name, set_name.lower().replace(" ", "_"))
    
    # Obtener las cartas del set usando el código
    cursor.execute('''
        SELECT id, name, aspect, type, cost
        FROM cards 
        WHERE set_name = ?
        ORDER BY type, cost, name
    ''', (set_code,))
    
    cards = []
    for row in cursor.fetchall():
        card = {
            "id": row["id"],
            "name": row["name"],
            "aspect": row["aspect"],
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