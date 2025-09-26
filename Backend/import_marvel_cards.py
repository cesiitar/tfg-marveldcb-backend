#!/usr/bin/env python3
"""
Script para importar cartas y sets desde la API pública de MarvelCDB
"""

import requests
import sqlite3
import json
from typing import List, Dict, Any
import time

# URL base de la API de MarvelCDB
API_BASE_URL = "https://marvelcdb.com/api/public"

def get_db_connection():
    """Conectar a la base de datos SQLite"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

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

def clear_database():
    """Limpiar la base de datos existente"""
    print("🧹 Limpiando base de datos...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Eliminar datos existentes
    cursor.execute("DELETE FROM cards")
    cursor.execute("DELETE FROM card_sets")
    
    conn.commit()
    conn.close()
    print("✅ Base de datos limpiada")

def import_sets(sets_data: List[Dict[str, Any]]):
    """Importar sets a la base de datos"""
    print("📦 Importando sets...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    imported_count = 0
    
    for set_data in sets_data:
        try:
            # Mapear datos de MarvelCDB a nuestro esquema
            # Usar el ID único de la API de MarvelCDB
            set_id = set_data.get('id', 0)
            if not set_id:  # Si no hay ID, usar hash del code
                set_id = abs(hash(set_data.get('code', ''))) % 1000000
            
            cursor.execute('''
                INSERT INTO card_sets (id, name, description, release_date, card_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                set_id,  # ID único de MarvelCDB
                set_data.get('name', ''),  # name
                f"Set {set_data.get('name', '')}",  # description (no existe en API)
                set_data.get('available', ''),  # available como release_date
                set_data.get('total', 0)  # total como card_count
            ))
            imported_count += 1
        except Exception as e:
            print(f"⚠️ Error importando set {set_data.get('name', 'Unknown')}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Importados {imported_count} sets")

def import_cards(cards_data: List[Dict[str, Any]]):
    """Importar cartas a la base de datos"""
    print("🃏 Importando cartas...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    imported_count = 0
    
    for card_data in cards_data:
        try:
            # Mapear datos de MarvelCDB a nuestro esquema simplificado
            # Convertir cost a int, manejar None
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
                # Si no es numérico, usar hash del string
                card_id = abs(hash(card_id)) % 1000000
            
            cursor.execute('''
                INSERT INTO cards (id, name, aspect, type, cost, set_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                card_id,
                card_data.get('name', ''),
                card_data.get('faction_code', ''),  # aspect
                card_data.get('type_code', ''),     # type
                cost,
                card_data.get('pack_code', '')      # set_name
            ))
            imported_count += 1
            
            # Pequeña pausa para no sobrecargar
            if imported_count % 100 == 0:
                print(f"📊 Procesadas {imported_count} cartas...")
                time.sleep(0.1)
                
        except Exception as e:
            print(f"⚠️ Error importando carta {card_data.get('name', 'Unknown')}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Importadas {imported_count} cartas")

def main():
    """Función principal"""
    print("🚀 Iniciando importación desde MarvelCDB...")
    print("=" * 50)
    
    # Limpiar base de datos
    clear_database()
    
    # Obtener datos de la API
    sets_data = fetch_all_sets()
    cards_data = fetch_all_cards()
    
    if not sets_data and not cards_data:
        print("❌ No se pudieron obtener datos de la API")
        return
    
    # Importar datos
    if sets_data:
        import_sets(sets_data)
    
    if cards_data:
        import_cards(cards_data)
    
    print("=" * 50)
    print("🎉 ¡Importación completada!")
    print("💡 Ahora puedes ejecutar tu aplicación con datos reales de MarvelCDB")

if __name__ == "__main__":
    main()
