#!/bin/bash
# Script de inicio para producción

# Crear directorio para la base de datos si no existe
mkdir -p /data

# Copiar base de datos si existe localmente, o inicializar si no existe
if [ ! -f /data/marvel_cards.db ]; then
    echo "📦 Inicializando base de datos..."
    # Si existe localmente, copiarla
    if [ -f marvel_cards.db ]; then
        cp marvel_cards.db /data/marvel_cards.db
    else
        # Inicializar base de datos vacía
        python init_all.py
        if [ -f marvel_cards.db ]; then
            cp marvel_cards.db /data/marvel_cards.db
        fi
    fi
fi

# Crear symlink para que la app encuentre la BD en /data
ln -sf /data/marvel_cards.db marvel_cards.db

# Iniciar la aplicación
echo "🚀 Iniciando servidor..."
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

