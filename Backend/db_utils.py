"""
Utilidades centralizadas para la base de datos.
Este módulo proporciona funciones compartidas para todos los módulos del backend.
"""
import sqlite3
import os


def get_db_path() -> str:
    """
    Obtiene la ruta a la base de datos de forma consistente en todo el proyecto.
    
    Prioridad:
    1. Variable de entorno DB_PATH (para producción)
    2. Ruta relativa por defecto (para desarrollo)
    
    Returns:
        str: Ruta absoluta a la base de datos
    """
    db_path = os.getenv('DB_PATH')
    if db_path:
        return db_path
    
    # Ruta por defecto: Backend/marvel_cards.db
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'marvel_cards.db')
    return db_path


def get_db_connection():
    """
    Obtiene una conexión a la base de datos con configuración estándar.
    
    Returns:
        sqlite3.Connection: Conexión configurada con row_factory para diccionarios
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
    # Habilitar foreign keys para que funcionen las eliminaciones en cascada
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_table_exists(table_name: str, create_query: str = None):
    """
    Verifica que una tabla exista, y la crea si no existe.
    
    Args:
        table_name: Nombre de la tabla a verificar
        create_query: Query SQL para crear la tabla si no existe (opcional)
    
    Returns:
        bool: True si la tabla existe o se creó exitosamente
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    exists = cursor.fetchone() is not None
    
    if not exists and create_query:
        cursor.execute(create_query)
        conn.commit()
        exists = True
    
    conn.close()
    return exists


def verify_tables_exist(required_tables: list) -> bool:
    """
    Verifica que todas las tablas requeridas existan.
    
    Args:
        required_tables: Lista de nombres de tablas requeridas
    
    Returns:
        bool: True si todas las tablas existen
    
    Raises:
        ValueError: Si alguna tabla no existe
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    missing_tables = []
    for table_name in required_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            missing_tables.append(table_name)
    
    conn.close()
    
    if missing_tables:
        raise ValueError(
            f"Las siguientes tablas no existen: {', '.join(missing_tables)}. "
            "Asegúrate de que la base de datos esté inicializada."
        )
    
    return True

