#!/usr/bin/env python3
"""
Script único para inicializar completamente la base de datos de MarvelCDB
Incluye: cartas, sets, mazos públicos y toda la información necesaria
"""

import requests
import sqlite3
import json
import time
from typing import List, Dict, Any

# URL base de la API de MarvelCDB
API_BASE_URL = "https://marvelcdb.com/api/public"

def get_db_connection():
    """Conectar a la base de datos SQLite"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Inicializar la base de datos desde cero"""
    print("🗑️ Eliminando base de datos anterior...")
    import os
    if os.path.exists('marvel_cards.db'):
        os.remove('marvel_cards.db')
    
    print("📋 Creando estructura de base de datos...")
    conn = sqlite3.connect('marvel_cards.db')
    cursor = conn.cursor()
    
    # Tabla cards con información completa
    cursor.execute('''
        CREATE TABLE cards (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            aspect TEXT NOT NULL,  --es la clase de la carta
            type TEXT NOT NULL,
            cost INTEGER DEFAULT 0,
            set_name TEXT,
            set_code TEXT,
            pack_code TEXT,      -- Código del pack original
            pack_name TEXT,       -- Nombre del pack original
            faction_code TEXT,   -- Código de facción
            type_code TEXT,      -- Código de tipo
            card_set TEXT,       -- Set de la carta (ej: "Ms. Marvel", "Spider-Man")
            quantity INTEGER DEFAULT 1,  -- Cantidad de la carta en el mazo
            deck_limit INTEGER           -- Límite de copias por mazo (NULL si no viene)
        )
    ''')
    
    # Tabla card_sets
    cursor.execute('''
        CREATE TABLE card_sets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            card_count INTEGER DEFAULT 0
        )
    ''')
    
    # Tabla decks
    cursor.execute('''
        CREATE TABLE decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            hero_name TEXT NOT NULL,
            aspect TEXT NOT NULL,
            cards TEXT NOT NULL,  -- JSON con las cartas del mazo
            is_public BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada")

def fetch_all_sets() -> List[Dict[str, Any]]:
    """Obtener todos los sets desde la API de MarvelCDB"""
    print("🔄 Obteniendo sets desde MarvelCDB...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/packs/")
        response.raise_for_status()
        sets_data = response.json()
        
        print(f"✅ Obtenidos {len(sets_data)} sets")
        return sets_data
    except requests.RequestException as e:
        print(f"❌ Error al obtener sets: {e}")
        return []

def fetch_all_cards() -> List[Dict[str, Any]]:
    """Obtener todas las cartas desde la API de MarvelCDB"""
    print("🔄 Obteniendo cartas desde MarvelCDB...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/cards/")
        response.raise_for_status()
        cards_data = response.json()
        
        print(f"✅ Obtenidas {len(cards_data)} cartas")
        return cards_data
    except requests.RequestException as e:
        print(f"❌ Error al obtener cartas: {e}")
        return []

def analyze_card_structure(cards_data: List[Dict[str, Any]]):
    """Analizar la estructura de las cartas para entender los campos disponibles"""
    print("🔍 Analizando estructura de cartas...")
    
    if not cards_data:
        return
    
    # Mostrar campos disponibles en las cartas
    sample_card = cards_data[0]
    print("📋 Campos disponibles en las cartas:")
    for key, value in sample_card.items():
        print(f"  - {key}: {type(value).__name__} = {str(value)[:50]}...")
    
    # Buscar cartas de héroes específicos
    print("\n🦸 Buscando cartas de héroes específicos...")
    heroes_to_check = ['hulk', 'captain', 'iron', 'spider']
    
    for hero in heroes_to_check:
        hero_cards = [card for card in cards_data if hero.lower() in card.get('name', '').lower()]
        if hero_cards:
            print(f"\n🃏 Cartas de {hero.upper()}:")
            for card in hero_cards[:3]:  # Mostrar solo las primeras 3
                print(f"  - {card.get('name')} | Pack: {card.get('pack_name')} | Code: {card.get('pack_code')}")
                # Mostrar todos los campos relacionados con sets/packs
                for field in ['pack_name', 'pack_code', 'set_name', 'set_code', 'position']:
                    if field in card:
                        print(f"    {field}: {card[field]}")

def import_sets(sets_data: List[Dict[str, Any]]):
    """Importar sets a la base de datos"""
    print("📦 Importando sets...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    imported_count = 0
    
    for set_data in sets_data:
        try:
            set_id = set_data.get('id', 0)
            if not set_id:
                set_id = abs(hash(set_data.get('code', ''))) % 1000000
            
            cursor.execute('''
                INSERT INTO card_sets (id, name, code, card_count)
                VALUES (?, ?, ?, ?)
            ''', (
                set_id,
                set_data.get('name', ''),
                set_data.get('code', ''),
                set_data.get('total', 0)
            ))
            imported_count += 1
        except Exception as e:
            print(f"⚠️ Error importando set {set_data.get('name', 'Unknown')}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Importados {imported_count} sets")


def import_cards(cards_data: List[Dict[str, Any]]):
    """Importar cartas a la base de datos con información completa"""
    print("🃏 Importando cartas...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    imported_count = 0
    
    for card_data in cards_data:
        try:
            # Convertir cost a int
            cost = card_data.get('cost')
            if cost is None:
                cost = 0
            else:
                cost = int(cost)
            
            # Convertir code a entero para id
            card_id = card_data.get('code', '')
            if card_id and card_id.isdigit():
                card_id = int(card_id)
            else:
                card_id = abs(hash(card_id)) % 1000000
            
            cursor.execute('''
                INSERT INTO cards (
                    id, name, aspect, type, cost, set_name, set_code,
                    pack_code, pack_name, faction_code, type_code, card_set, quantity, deck_limit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                card_id,
                card_data.get('name', ''),
                card_data.get('faction_code', ''),
                card_data.get('type_code', ''),
                cost,
                card_data.get('pack_name', ''),
                card_data.get('pack_code', ''),
                card_data.get('pack_code', ''),
                card_data.get('pack_name', ''),
                card_data.get('faction_code', ''),
                card_data.get('type_code', ''),
                card_data.get('card_set_name'),  # Set real de la API (puede ser NULL)
                card_data.get('quantity', 1),     # Cantidad real de la API
                int(card_data.get('deck_limit')) if str(card_data.get('deck_limit', '')).isdigit() else None
            ))
            imported_count += 1
            
            if imported_count % 100 == 0:
                print(f"📊 Procesadas {imported_count} cartas...")
                time.sleep(0.1)
                
        except Exception as e:
            print(f"⚠️ Error importando carta {card_data.get('name', 'Unknown')}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Importadas {imported_count} cartas")

def fetch_popular_decks() -> List[Dict[str, Any]]:
    """Obtener mazos populares desde MarvelCDB"""
    print("🔄 Obteniendo mazos populares desde MarvelCDB...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/decklists/popular/", timeout=10)
        response.raise_for_status()
        decks_data = response.json()
        
        print(f"✅ Obtenidos {len(decks_data)} mazos populares")
        return decks_data
    except requests.RequestException as e:
        print(f"❌ Error al obtener mazos: {e}")
        return []

def get_card_name_by_code(card_code: str) -> str:
    """Obtener el nombre de una carta por su código"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name FROM cards 
        WHERE id = ? OR CAST(id AS TEXT) = ?
        LIMIT 1
    ''', (card_code, card_code))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result['name']
    else:
        return f"Carta {card_code}"

def import_decks(decks_data: List[Dict[str, Any]]):
    """Importar mazos a la base de datos"""
    print("📦 Importando mazos públicos...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    imported_count = 0
    
    for deck_data in decks_data:
        try:
            decklist = deck_data.get('decklist', {})
            meta = deck_data.get('meta', {})
            
            # Convertir slots a formato de cartas
            slots = decklist.get('slots', {})
            cards_list = []
            
            for card_code, quantity in slots.items():
                card_name = get_card_name_by_code(card_code)
                cards_list.append({
                    "code": card_code,
                    "name": card_name,
                    "quantity": quantity
                })
            
            # Insertar en la base de datos
            cursor.execute('''
                INSERT INTO decks (name, description, hero_name, aspect, cards, is_public)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                decklist.get('name', 'Mazo sin nombre'),
                decklist.get('description_md', ''),
                decklist.get('hero_name', 'Unknown'),
                meta.get('aspect', 'basic'),
                json.dumps(cards_list),
                1
            ))
            
            imported_count += 1
            print(f"✅ Importado: {decklist.get('name', 'Unknown')} ({decklist.get('hero_name', 'Unknown')})")
            
        except Exception as e:
            print(f"⚠️ Error importando mazo: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Importados {imported_count} mazos")

def main():
    """Función principal - inicializar todo"""
    print("🚀 INICIALIZACIÓN COMPLETA DE MARVELCDB")
    print("=" * 60)
    
    # 1. Inicializar base de datos
    initialize_database()
    
    # 2. Obtener datos de la API
    sets_data = fetch_all_sets()
    cards_data = fetch_all_cards()
    
    if not sets_data and not cards_data:
        print("❌ No se pudieron obtener datos de la API")
        return
    
    # 3. Analizar estructura de cartas
    analyze_card_structure(cards_data)
    
    # 4. Importar datos
    if sets_data:
        import_sets(sets_data)
    
    if cards_data:
        import_cards(cards_data)
    
    # 5. Importar mazos públicos
    decks_data = fetch_popular_decks()
    if decks_data:
        import_decks(decks_data)
    
    print("=" * 60)
    print("🎉 ¡INICIALIZACIÓN COMPLETA!")
    print("💡 Base de datos lista con:")
    print("   - Cartas con información de sets de héroes")
    print("   - Sets de cartas")
    print("   - Mazos públicos reales")
    print("🚀 Ahora puedes ejecutar: py main.py")

if __name__ == "__main__":
    main()
