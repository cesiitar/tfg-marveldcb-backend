"""
Script para generar datos de prueba (mazos y partidas) para entrenar la IA.
Genera mazos y partidas automáticamente usando datos reales de la base de datos.
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_heroes() -> List[Dict]:
    """Obtener lista de héroes disponibles"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT id, name, card_set
        FROM cards 
        WHERE type = 'hero'
        ORDER BY name
    ''')
    
    heroes = []
    for row in cursor.fetchall():
        heroes.append({
            'id': row['id'],
            'name': row['name'],
            'card_set': row['card_set']
        })
    
    conn.close()
    return heroes

def get_villains() -> List[Dict]:
    """Obtener lista de villanos únicos disponibles"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT MIN(id) as id, card_set as name
        FROM cards 
        WHERE type = 'villain' AND card_set IS NOT NULL
        GROUP BY card_set
        ORDER BY card_set
    ''')
    
    villains = []
    for row in cursor.fetchall():
        villains.append({
            'id': row['id'],
            'name': row['name']
        })
    
    conn.close()
    return villains

def get_hero_specific_cards(hero_id: int) -> List[Dict]:
    """
    Obtener las cartas específicas del héroe (15-16 cartas que siempre vienen con el héroe)
    Usa la misma lógica que el endpoint GET /api/heroes/{hero_id}/cards
    """
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
        return []
    
    hero_card_set = result['card_set']
    hero_pack_name = result['pack_name']
    
    # Buscar las cartas que pertenecen al héroe específico dentro del pack correcto
    # EXCLUIR la carta del héroe (type = 'hero') y solo incluir cartas del aspecto 'hero'
    # Usa la misma lógica que el endpoint get_hero_cards
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
    
    hero_cards = []
    for row in cursor.fetchall():
        # Usar la cantidad de la carta (quantity) que viene en la BD
        quantity = row['quantity'] or 1
        
        hero_cards.append({
            'card_id': row['id'],
            'card_name': row['name'],
            'card_set': row['card_set'] or hero_pack_name or 'Unknown',
            'quantity': quantity
        })
    
    conn.close()
    return hero_cards

def get_aspect_cards(aspect: str, num_cards: int = 40) -> List[Dict]:
    """
    Obtener cartas aleatorias del aspecto especificado Y cartas básicas
    Las cartas básicas siempre se pueden meter en cualquier mazo
    Mezcla 70% cartas del aspecto y 30% cartas básicas
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener cartas del aspecto (70% aproximadamente)
    aspect_count = int(num_cards * 0.7)
    cursor.execute('''
        SELECT id, name, cost, type, aspect, pack_name, quantity, deck_limit
        FROM cards 
        WHERE aspect = ?
        AND type != 'alter_ego'
        AND type != 'alter-ego'
        AND type != 'hero'
        AND type != 'villain'
        ORDER BY RANDOM()
        LIMIT ?
    ''', (aspect, aspect_count))
    
    aspect_cards = []
    for row in cursor.fetchall():
        deck_limit = row['deck_limit'] or 3
        quantity = min(random.randint(1, deck_limit), 3)
        aspect_cards.append({
            'card_id': row['id'],
            'card_name': row['name'],
            'card_set': row['pack_name'] or 'Unknown',
            'quantity': quantity
        })
    
    # Obtener cartas básicas (30% aproximadamente)
    basic_count = num_cards - len(aspect_cards)
    cursor.execute('''
        SELECT id, name, cost, type, aspect, pack_name, quantity, deck_limit
        FROM cards 
        WHERE (aspect = '' OR aspect IS NULL OR aspect = 'basic')
        AND type != 'alter_ego'
        AND type != 'alter-ego'
        AND type != 'hero'
        AND type != 'villain'
        ORDER BY RANDOM()
        LIMIT ?
    ''', (basic_count,))
    
    basic_cards = []
    for row in cursor.fetchall():
        deck_limit = row['deck_limit'] or 3
        quantity = min(random.randint(1, deck_limit), 3)
        basic_cards.append({
            'card_id': row['id'],
            'card_name': row['name'],
            'card_set': row['pack_name'] or 'Unknown',
            'quantity': quantity
        })
    
    # Mezclar las cartas del aspecto con las básicas
    all_cards = aspect_cards + basic_cards
    random.shuffle(all_cards)
    
    conn.close()
    return all_cards

def create_test_deck(hero: Dict, aspect: str, user_id: int, deck_name: Optional[str] = None) -> int:
    """Crear un mazo de prueba"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Obtener las cartas específicas del héroe (15-16 cartas que siempre vienen con el héroe)
    hero_cards = get_hero_specific_cards(hero['id'])
    
    if not hero_cards:
        print(f"⚠️  No se encontraron cartas específicas para el héroe {hero['name']} (ID: {hero['id']})")
        hero_cards = []
    
    # 2. Calcular cuántas cartas adicionales necesitamos del aspecto
    # El mazo debe tener entre 40 y 50 cartas TOTALES (sumando cantidades, no cartas distintas)
    target_total = random.randint(40, 50)
    
    # Calcular el total actual de cartas (sumando cantidades)
    current_total = sum(card.get('quantity', 1) for card in hero_cards)
    needed_cards = max(0, target_total - current_total)
    
    # 3. Obtener cartas aleatorias del aspecto Y básicas para completar el mazo
    # La función get_aspect_cards ya mezcla 70% aspecto y 30% básicas
    aspect_cards = get_aspect_cards(aspect, num_cards=100)  # Obtener muchas cartas para elegir
    
    # 4. Combinar las cartas del héroe con las del aspecto/básicas
    all_cards = hero_cards.copy()
    current_total = sum(card.get('quantity', 1) for card in all_cards)
    
    # Añadir cartas del aspecto/básicas hasta llegar al objetivo (sumando cantidades)
    for card in aspect_cards:
        if current_total >= target_total:
            break
        
        card_quantity = card.get('quantity', 1)
        # Si añadir esta carta no excede el límite, añadirla
        if current_total + card_quantity <= target_total:
            all_cards.append(card)
            current_total += card_quantity
        # Si añadir esta carta excede el límite, ajustar la cantidad
        elif current_total < target_total:
            remaining = target_total - current_total
            if remaining > 0:
                card['quantity'] = remaining
                all_cards.append(card)
                current_total += remaining
            break
    
    # Si aún no tenemos suficientes cartas, repetir algunas del aspecto
    while current_total < target_total and aspect_cards:
        for card in aspect_cards:
            if current_total >= target_total:
                break
            
            card_quantity = card.get('quantity', 1)
            remaining = target_total - current_total
            
            if remaining >= card_quantity:
                # Añadir una copia de la carta
                new_card = card.copy()
                all_cards.append(new_card)
                current_total += card_quantity
            elif remaining > 0:
                # Añadir una copia con cantidad ajustada
                new_card = card.copy()
                new_card['quantity'] = remaining
                all_cards.append(new_card)
                current_total += remaining
                break
    
    # Calcular el total final
    final_total = sum(card.get('quantity', 1) for card in all_cards)
    
    # Generar nombre del mazo si no se proporciona
    if not deck_name:
        deck_name = f"Mazo de prueba - {hero['name']} ({aspect})"
    
    # Insertar el mazo
    cursor.execute('''
        INSERT INTO decks (name, description, hero_name, hero_id, aspect, cards, is_public, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        deck_name,
        f"Mazo de prueba generado automáticamente para entrenar la IA",
        hero['name'],
        hero['id'],
        aspect,
        json.dumps(all_cards),
        1,  # Público
        user_id
    ))
    
    deck_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Calcular estadísticas
    hero_cards_count = sum(card.get('quantity', 1) for card in hero_cards)
    aspect_cards_count = final_total - hero_cards_count
    distinct_cards = len(all_cards)
    
    print(f"✅ Mazo creado: ID={deck_id}, Nombre='{deck_name}', Héroe={hero['name']}, Aspecto={aspect}")
    print(f"   - Cartas del héroe: {hero_cards_count} cartas ({len(hero_cards)} distintas)")
    print(f"   - Cartas del aspecto: {aspect_cards_count} cartas ({distinct_cards - len(hero_cards)} distintas)")
    print(f"   - Total: {final_total} cartas ({distinct_cards} distintas)")
    return deck_id

def create_test_game_configuration(deck_id: int, villain: Dict, difficulty: str, result: str, user_id: int) -> int:
    """Crear una configuración de partida de prueba"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generar fecha aleatoria en los últimos 30 días
    days_ago = random.randint(0, 30)
    played_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
    
    # Insertar la configuración de partida
    cursor.execute('''
        INSERT INTO game_configurations (user_id, deck_id, difficulty, villain_id, result, played_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        deck_id,
        difficulty,
        villain['id'],
        result,
        played_at
    ))
    
    game_config_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"✅ Partida creada: ID={game_config_id}, Mazo={deck_id}, Villano={villain['name']}, Dificultad={difficulty}, Resultado={result}")
    return game_config_id

def get_or_create_test_user() -> int:
    """Obtener o crear un usuario de prueba"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar usuario de prueba
    cursor.execute('''
        SELECT id FROM users WHERE auth0_id = 'test_user_ai_training'
    ''')
    
    user_row = cursor.fetchone()
    
    if user_row:
        user_id = user_row['id']
        print(f"✅ Usuario de prueba encontrado: ID={user_id}")
    else:
        # Crear usuario de prueba
        cursor.execute('''
            INSERT INTO users (auth0_id, email, name)
            VALUES (?, ?, ?)
        ''', (
            'test_user_ai_training',
            'test_ai@example.com',
            'Usuario de Prueba IA'
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        print(f"✅ Usuario de prueba creado: ID={user_id}")
    
    conn.close()
    return user_id

def generate_test_data(
    num_decks: int = 10,
    num_games_per_deck: int = 3,
    win_rate: float = 0.6
):
    """
    Generar datos de prueba para entrenar la IA
    
    Args:
        num_decks: Número de mazos a crear
        num_games_per_deck: Número de partidas por mazo
        win_rate: Probabilidad de victoria (0.0 a 1.0)
    """
    print("🚀 Iniciando generación de datos de prueba...")
    print(f"📊 Configuración: {num_decks} mazos, {num_games_per_deck} partidas/mazo, {win_rate*100}% tasa de victoria\n")
    
    # Obtener datos de la base de datos
    print("📥 Obteniendo datos de la base de datos...")
    heroes = get_heroes()
    villains = get_villains()
    aspects = ['aggression', 'justice', 'leadership', 'protection']
    difficulties = ['normal', 'expert']
    
    if not heroes:
        print("❌ Error: No se encontraron héroes en la base de datos")
        return
    
    if not villains:
        print("❌ Error: No se encontraron villanos en la base de datos")
        return
    
    print(f"✅ Encontrados: {len(heroes)} héroes, {len(villains)} villanos\n")
    
    # Obtener o crear usuario de prueba
    user_id = get_or_create_test_user()
    print()
    
    # Generar mazos y partidas
    total_games = 0
    
    for i in range(num_decks):
        print(f"📦 Generando mazo {i+1}/{num_decks}...")
        
        # Seleccionar héroe y aspecto aleatorios
        hero = random.choice(heroes)
        aspect = random.choice(aspects)
        
        # Crear mazo
        deck_id = create_test_deck(hero, aspect, user_id)
        
        # Generar partidas para este mazo
        for j in range(num_games_per_deck):
            # Seleccionar villano y dificultad aleatorios
            villain = random.choice(villains)
            difficulty = random.choice(difficulties)
            
            # Determinar resultado basado en win_rate
            result = 'win' if random.random() < win_rate else 'loss'
            
            # Crear partida
            create_test_game_configuration(deck_id, villain, difficulty, result, user_id)
            total_games += 1
        
        print()
    
    print(f"🎉 ¡Datos de prueba generados exitosamente!")
    print(f"📊 Resumen:")
    print(f"   - Mazos creados: {num_decks}")
    print(f"   - Partidas creadas: {total_games}")
    print(f"   - Usuario: ID={user_id}")
    print()
    print(f"💡 Ahora puedes entrenar la IA ejecutando:")
    print(f"   python ml/models/train_model.py")
    print()
    print(f"   O usando el endpoint:")
    print(f"   POST /api/recommendations/train")

if __name__ == '__main__':
    import sys
    
    # Configuración por defecto
    num_decks = 10
    num_games_per_deck = 3
    win_rate = 0.6
    
    # Permitir argumentos desde línea de comandos
    if len(sys.argv) > 1:
        num_decks = int(sys.argv[1])
    if len(sys.argv) > 2:
        num_games_per_deck = int(sys.argv[2])
    if len(sys.argv) > 3:
        win_rate = float(sys.argv[3])
    
    generate_test_data(num_decks, num_games_per_deck, win_rate)

