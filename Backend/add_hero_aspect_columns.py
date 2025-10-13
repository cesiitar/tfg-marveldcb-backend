import sqlite3


def get_db_connection():
	conn = sqlite3.connect('marvel_cards.db')
	conn.row_factory = sqlite3.Row
	return conn


def ensure_hero_and_aspect_columns():
	conn = get_db_connection()
	cursor = conn.cursor()

	# Obtener columnas actuales de la tabla decks
	cursor.execute("PRAGMA table_info(decks)")
	columns = [column[1] for column in cursor.fetchall()]

	added_any = False

	# Añadir columna hero_name si no existe
	if 'hero_name' not in columns:
		cursor.execute('ALTER TABLE decks ADD COLUMN hero_name TEXT')
		added_any = True

	# Añadir columna aspect si no existe
	if 'aspect' not in columns:
		cursor.execute('ALTER TABLE decks ADD COLUMN aspect TEXT')
		added_any = True

	if added_any:
		conn.commit()
		print("✅ Columnas añadidas (si faltaban): hero_name, aspect")
	else:
		print("ℹ️ Columnas 'hero_name' y 'aspect' ya existen")

	conn.close()


if __name__ == "__main__":
	print("🔧 VERIFICANDO/AGREGANDO COLUMNAS hero_name Y aspect EN 'decks'")
	print("=" * 60)
	ensure_hero_and_aspect_columns()
	print("✅ Esquema actualizado")


