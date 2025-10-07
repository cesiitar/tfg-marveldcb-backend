# MarvelCDB Backend - Marvel Champions Database API

Backend API para gestionar y explorar cartas del juego Marvel Champions.

## 🚀 Características

- **API REST** con FastAPI
- **Base de datos SQLite** para almacenamiento local
- **Endpoints** para búsqueda de cartas con filtros avanzados
- **Gestión de sets** de cartas
- **CORS configurado** para frontend separado

## 📋 Requisitos

- **Python** 3.8+
- **pip** (gestor de paquetes Python)

## 🛠️ Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/cesiitar/tfg-marveldcb.git
cd tfg-marveldcb
```

### 2. Configurar Backend (Python)

```bash
cd Backend

# Instalar dependencias Python
py -m pip install -r requirements.txt

# Importar cartas de Marvel Champions (opcional)
py import_marvel_cards.py

# Ejecutar servidor (puerto 8000)
py main.py
```

## 🌐 URLs

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: https://github.com/cesiitar/tfg-marveldcb-frontend

## 📁 Estructura del Proyecto

```
tfg-marveldcb/
├── Backend/
│   ├── main.py              # API FastAPI
│   ├── import_marvel_cards.py # Script para importar cartas
│   ├── requirements.txt     # Dependencias Python
│   └── marvel_cards.db      # Base de datos SQLite
└── README.md
```

## 🔧 Comandos Útiles

### Backend
```bash
# Ejecutar servidor
py main.py

# Con recarga automática
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Importar cartas de Marvel Champions
py import_marvel_cards.py
```

## 🎯 Endpoints de la API

### Sets
- `GET /api/sets` - Obtener todos los sets de cartas
- `GET /api/sets/{set_id}/cards` - Obtener cartas de un set específico

### Cartas
- `GET /api/cards` - Obtener todas las cartas
- `GET /api/cards/search` - Buscar cartas con filtros

### Parámetros de búsqueda
- `name` - Nombre de la carta
- `aspect` - Aspecto/clase de la carta
- `type` - Tipo de carta (hero, ally, event, etc.)
- `cost` - Coste de la carta
- `set_name` - Nombre del set

## 🔧 Configuración CORS

El backend está configurado para aceptar requests desde:
- `http://localhost:3000` (Frontend local)
- `http://localhost:5173` (Vite dev server)
- `https://cesiitar.github.io` (GitHub Pages)
- Otros dominios de despliegue comunes

## 🐛 Solución de Problemas

### Puerto 8000 ocupado
```bash
# Verificar qué usa el puerto 8000
netstat -ano | findstr :8000

# Usar otro puerto
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Dependencias Python
Si hay problemas con pip:
```bash
py -m ensurepip --upgrade
py -m pip install --upgrade pip
```

### Base de datos
Si necesitas recrear la base de datos:
```bash
# Eliminar base de datos existente
rm marvel_cards.db

# Ejecutar script de importación
py import_marvel_cards.py
```

## 📝 Notas de Desarrollo

- El backend se ejecuta en puerto 8000 por defecto
- La base de datos se crea automáticamente si no existe
- Los cambios en el código se reflejan automáticamente con `--reload`
- CORS está configurado para el frontend separado

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 🔗 Enlaces Relacionados

- **Frontend**: https://github.com/cesiitar/tfg-marveldcb-frontend
- **Documentación API**: http://localhost:8000/docs (cuando el servidor esté ejecutándose)