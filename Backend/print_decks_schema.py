import sqlite3


def main():
	conn = sqlite3.connect('marvel_cards.db')
	conn.row_factory = sqlite3.Row
	cur = conn.cursor()
	cur.execute('PRAGMA table_info(decks)')
	cols = [row[1] for row in cur.fetchall()]
	print('decks columns:', cols)
	try:
		cur.execute('SELECT id, name, hero_name, aspect, created_at FROM decks LIMIT 3')
		rows = cur.fetchall()
		print('sample rows:', [dict(r) for r in rows])
	except Exception as e:
		print('sample rows error:', e)
	conn.close()


if __name__ == '__main__':
	main()


