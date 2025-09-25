import sqlite3
import json
from typing import List, Dict

# Conectar a la base de datos (se crea automáticamente si no existe)
conn = sqlite3.connect('marvel_cards.db')
cursor = conn.cursor()

# Crear tabla de cartas (simplificada)
cursor.execute('''
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    aspect TEXT NOT NULL,
    type TEXT NOT NULL,
    cost INTEGER NOT NULL,
    set_name TEXT NOT NULL
)
''')

# Crear tabla de sets
cursor.execute('''
CREATE TABLE IF NOT EXISTS card_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    card_count INTEGER DEFAULT 0
)
''')

# Insertar datos de prueba - Sets
sets_data = [
    ('Core Set',),
    ('The Green Goblin',),
    ('Captain America',),
    ('Ms. Marvel',),
    ('Thor',),
    ('Black Widow',),
    ('Doctor Strange',),
    ('Hulk',)
]

cursor.executemany('''
INSERT OR IGNORE INTO card_sets (name) 
VALUES (?)
''', sets_data)

# Insertar cartas de prueba - Solo los atributos esenciales
cards_data = [
    # Core Set
    ('Spider-Man', 'aggression', 'hero', 0, 'Core Set'),
    ('Iron Man', 'justice', 'hero', 0, 'Core Set'),
    ('Web-Shot', 'aggression', 'event', 1, 'Core Set'),
    ('Arc Reactor', 'justice', 'support', 3, 'Core Set'),
    ('Captain America', 'leadership', 'hero', 0, 'Core Set'),
    ('Avengers Assemble', 'leadership', 'event', 4, 'Core Set'),
    ('Black Widow', 'justice', 'hero', 0, 'Core Set'),
    ('Widow\'s Bite', 'justice', 'event', 1, 'Core Set'),
    ('Hulk', 'protection', 'hero', 0, 'Core Set'),
    ('Defensive Stance', 'protection', 'event', 1, 'Core Set'),
    ('Thor', 'aggression', 'hero', 0, 'Core Set'),
    ('Lightning Strike', 'aggression', 'event', 2, 'Core Set'),
    ('Doctor Strange', 'justice', 'hero', 0, 'Core Set'),
    ('Mystic Arts', 'justice', 'event', 2, 'Core Set'),
    ('Ms. Marvel', 'protection', 'hero', 0, 'Core Set'),
    
    # The Green Goblin
    ('Green Goblin', 'aggression', 'hero', 0, 'The Green Goblin'),
    ('Pumpkin Bomb', 'aggression', 'event', 2, 'The Green Goblin'),
    ('Goblin Glider', 'aggression', 'upgrade', 2, 'The Green Goblin'),
    ('Osborn Industries', 'aggression', 'support', 3, 'The Green Goblin'),
    ('Norman Osborn', 'aggression', 'ally', 3, 'The Green Goblin'),
    ('Goblin Serum', 'aggression', 'upgrade', 1, 'The Green Goblin'),
    ('Explosive Device', 'aggression', 'event', 1, 'The Green Goblin'),
    ('Goblin Mask', 'aggression', 'upgrade', 2, 'The Green Goblin'),
    ('Harry Osborn', 'aggression', 'ally', 2, 'The Green Goblin'),
    ('Goblin Tech', 'aggression', 'support', 2, 'The Green Goblin'),
    ('Toxic Gas', 'aggression', 'event', 3, 'The Green Goblin'),
    ('Goblin Formula', 'aggression', 'upgrade', 1, 'The Green Goblin'),
    
    # Captain America
    ('Captain America', 'leadership', 'hero', 0, 'Captain America'),
    ('Shield Throw', 'leadership', 'event', 2, 'Captain America'),
    ('Vibranium Shield', 'leadership', 'upgrade', 3, 'Captain America'),
    ('Falcon', 'leadership', 'ally', 2, 'Captain America'),
    ('Team Training', 'leadership', 'upgrade', 1, 'Captain America'),
    ('Bucky Barnes', 'leadership', 'ally', 3, 'Captain America'),
    ('Shield Block', 'leadership', 'event', 1, 'Captain America'),
    ('Super Soldier Serum', 'leadership', 'upgrade', 2, 'Captain America'),
    ('Peggy Carter', 'leadership', 'ally', 2, 'Captain America'),
    ('Avengers Initiative', 'leadership', 'support', 4, 'Captain America'),
    
    # Ms. Marvel
    ('Ms. Marvel', 'protection', 'hero', 0, 'Ms. Marvel'),
    ('Embiggen', 'protection', 'event', 1, 'Ms. Marvel'),
    ('Stretch', 'protection', 'upgrade', 2, 'Ms. Marvel'),
    ('Kamala Khan', 'protection', 'hero', 0, 'Ms. Marvel'),
    ('Shape Shift', 'protection', 'event', 2, 'Ms. Marvel'),
    ('Inhuman DNA', 'protection', 'upgrade', 1, 'Ms. Marvel'),
    ('Bruno Carrelli', 'protection', 'ally', 2, 'Ms. Marvel'),
    ('Hard Light Constructs', 'protection', 'upgrade', 3, 'Ms. Marvel'),
    
    # Thor
    ('Thor', 'aggression', 'hero', 0, 'Thor'),
    ('Mjolnir', 'aggression', 'upgrade', 3, 'Thor'),
    ('Lightning Strike', 'aggression', 'event', 2, 'Thor'),
    ('Asgardian', 'aggression', 'ally', 3, 'Thor'),
    ('God of Thunder', 'aggression', 'upgrade', 2, 'Thor'),
    ('Loki', 'aggression', 'ally', 2, 'Thor'),
    ('Stormbreaker', 'aggression', 'upgrade', 4, 'Thor'),
    ('Heimdall', 'aggression', 'ally', 3, 'Thor'),
    ('Bifrost', 'aggression', 'support', 3, 'Thor'),
    
    # Black Widow
    ('Black Widow', 'justice', 'hero', 0, 'Black Widow'),
    ('Widow\'s Bite', 'justice', 'event', 1, 'Black Widow'),
    ('Spy Network', 'justice', 'support', 2, 'Black Widow'),
    ('Natasha Romanoff', 'justice', 'hero', 0, 'Black Widow'),
    ('Stealth Suit', 'justice', 'upgrade', 2, 'Black Widow'),
    ('Yelena Belova', 'justice', 'ally', 2, 'Black Widow'),
    ('Grappling Hook', 'justice', 'upgrade', 1, 'Black Widow'),
    
    # Doctor Strange
    ('Doctor Strange', 'justice', 'hero', 0, 'Doctor Strange'),
    ('Mystic Arts', 'justice', 'event', 2, 'Doctor Strange'),
    ('Eye of Agamotto', 'justice', 'upgrade', 3, 'Doctor Strange'),
    ('Stephen Strange', 'justice', 'hero', 0, 'Doctor Strange'),
    ('Cloak of Levitation', 'justice', 'upgrade', 2, 'Doctor Strange'),
    ('Wong', 'justice', 'ally', 2, 'Doctor Strange'),
    ('Sling Ring', 'justice', 'upgrade', 1, 'Doctor Strange'),
    ('Sanctum Sanctorum', 'justice', 'support', 3, 'Doctor Strange'),
    ('Time Stone', 'justice', 'upgrade', 4, 'Doctor Strange'),
    ('Ancient One', 'justice', 'ally', 3, 'Doctor Strange'),
    ('Mystic Portal', 'justice', 'event', 1, 'Doctor Strange'),
    
    # Hulk
    ('Hulk', 'protection', 'hero', 0, 'Hulk'),
    ('HULK SMASH!', 'protection', 'event', 3, 'Hulk'),
    ('Gamma Radiation', 'protection', 'upgrade', 2, 'Hulk'),
    ('Bruce Banner', 'protection', 'hero', 0, 'Hulk'),
    ('Rage', 'protection', 'event', 1, 'Hulk'),
    ('She-Hulk', 'protection', 'ally', 3, 'Hulk')
]

cursor.executemany('''
INSERT OR IGNORE INTO cards (name, aspect, type, cost, set_name) 
VALUES (?, ?, ?, ?, ?)
''', cards_data)

# Actualizar el conteo de cartas en cada set
cursor.execute('''
    UPDATE card_sets 
    SET card_count = (
        SELECT COUNT(*) 
        FROM cards 
        WHERE cards.set_name = card_sets.name
    )
''')

# Confirmar cambios
conn.commit()

print("Base de datos creada exitosamente!")
print("Tablas creadas: cards, card_sets")
print("Datos de prueba insertados")
print(f"Total de cartas insertadas: {len(cards_data)}")

# Mostrar resumen
cursor.execute('SELECT name, card_count FROM card_sets ORDER BY name')
sets = cursor.fetchall()
print("\nSets creados:")
for set_info in sets:
    print(f"- {set_info[0]}: {set_info[1]} cartas")

# Cerrar conexión
conn.close()
