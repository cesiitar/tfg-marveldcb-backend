# MarvelCDB - Marvel Champions Database

Una aplicación web para gestionar y explorar cartas del juego Marvel Champions.

## 🚀 Características

- **Búsqueda de cartas** con filtros avanzados
- **Gestión de sets** de cartas
- **API REST** con FastAPI
- **Interfaz moderna** con React + TypeScript
- **Base de datos SQLite** para almacenamiento local

## 📋 Requisitos

- **Node.js** 16+ 
- **Python** 3.8+
- **npm** o **yarn**

## 🛠️ Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone <tu-repo-url>
cd tfg-marveldcb
```

### 2. Configurar Backend (Python)

```bash
cd Backend

# Instalar dependencias Python
py -m pip install -r requirements.txt

# Inicializar base de datos
py setup_database.py

# Ejecutar servidor (puerto 8000)
py main.py
```

### 3. Configurar Frontend (React)

```bash
cd frontend

# Instalar dependencias Node.js
npm install

# Ejecutar servidor de desarrollo
npm run dev
```

## 🌐 URLs

- **Frontend**: http://localhost:3000 (o 3001 si 3000 está ocupado)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📁 Estructura del Proyecto

```
tfg-marveldcb/
├── Backend/
│   ├── main.py              # API FastAPI
│   ├── setup_database.py    # Configuración de BD
│   ├── requirements.txt     # Dependencias Python
│   └── marvel_cards.db      # Base de datos SQLite
├── frontend/
│   ├── src/
│   │   ├── pages/           # Páginas React
│   │   ├── components/      # Componentes reutilizables
│   │   ├── services/        # Servicios API
│   │   └── types/           # Tipos TypeScript
│   ├── package.json         # Dependencias Node.js
│   └── vite.config.ts       # Configuración Vite
└── README.md
```

## 🔧 Comandos Útiles

### Backend
```bash
# Ejecutar servidor
py main.py

# Con recarga automática
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Recrear base de datos
py setup_database.py
```

### Frontend
```bash
# Desarrollo
npm run dev

# Build para producción
npm run build

# Preview build
npm run preview
```

## 🎯 Funcionalidades

### ✅ Implementadas
- [x] API REST con FastAPI
- [x] Base de datos SQLite con cartas de prueba
- [x] Búsqueda de cartas con filtros
- [x] Interfaz de usuario moderna
- [x] Navegación entre páginas

### 🚧 En desarrollo
- [ ] Gestión de mazos
- [ ] Sistema de usuarios
- [ ] Más cartas en la base de datos

## 🐛 Solución de Problemas

### Puerto 3000 ocupado
Si el frontend usa el puerto 3001:
```bash
# Verificar qué usa el puerto 3000
netstat -ano | findstr :3000

# Forzar puerto específico
npm run dev -- --port 3000
```

### Caché del navegador
Si no ves cambios:
- Refresco fuerte: `Ctrl + Shift + R`
- Modo incógnito
- Limpiar caché del navegador

### Dependencias Python
Si hay problemas con pip:
```bash
py -m ensurepip --upgrade
py -m pip install --upgrade pip
```

## 📝 Notas de Desarrollo

- El backend se ejecuta en puerto 8000
- El frontend se ejecuta en puerto 3000 (o 3001 si está ocupado)
- La base de datos se crea automáticamente si no existe
- Los cambios en el código se reflejan automáticamente (hot reload)

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request