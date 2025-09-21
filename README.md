# MarvelCDB - TFG Project

Una plataforma web moderna para coleccionistas de cartas Marvel, inspirada en MarvelCDB.com pero con un diseño propio y funcionalidades personalizadas.

## 🚀 Características

- **Frontend Moderno**: React + TypeScript + Vite + Tailwind CSS
- **Backend Robusto**: Python + FastAPI (próximamente)
- **Diseño Responsivo**: Optimizado para móviles y escritorio
- **Navegación Intuitiva**: React Router para navegación fluida
- **UI/UX Atractiva**: Diseño moderno con gradientes y animaciones

## 📁 Estructura del Proyecto

```
tfg-marveldcb/
├── frontend/                 # Aplicación React
│   ├── src/
│   │   ├── components/       # Componentes reutilizables
│   │   │   ├── Layout.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Footer.tsx
│   │   ├── pages/           # Páginas de la aplicación
│   │   │   ├── HomePage.tsx
│   │   │   ├── DecksPage.tsx
│   │   │   ├── CardsPage.tsx
│   │   │   └── FAQPage.tsx
│   │   ├── types/           # Definiciones de TypeScript
│   │   ├── assets/          # Imágenes y recursos
│   │   ├── App.tsx          # Componente principal
│   │   ├── main.tsx         # Punto de entrada
│   │   └── index.css        # Estilos globales
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── Backend/                 # API Python (en desarrollo)
│   └── main.py
└── README.md
```

## 🛠️ Tecnologías Utilizadas

### Frontend
- **React 18** - Biblioteca de UI
- **TypeScript** - Tipado estático
- **Vite** - Herramienta de construcción rápida
- **Tailwind CSS** - Framework de CSS utilitario
- **React Router** - Enrutamiento del lado del cliente
- **Inter Font** - Tipografía moderna

### Backend (Próximamente)
- **Python 3.11+**
- **FastAPI** - Framework web moderno
- **PostgreSQL** - Base de datos relacional
- **SQLAlchemy** - ORM

## 🚀 Instalación y Ejecución

### Prerrequisitos
- Node.js 18+ 
- npm o yarn
- Python 3.11+ (para el backend)

### Frontend

1. **Instalar dependencias:**
   ```bash
   cd frontend
   npm install
   ```

2. **Ejecutar en modo desarrollo:**
   ```bash
   npm run dev
   ```

3. **Construir para producción:**
   ```bash
   npm run build
   ```

4. **Vista previa de producción:**
   ```bash
   npm run preview
   ```

### Backend (Próximamente)
```bash
cd Backend
pip install -r requirements.txt
python main.py
```

## 📱 Páginas Disponibles

- **Inicio** (`/`) - Página principal con hero section y características
- **Mazos** (`/decks`) - Gestión de colecciones de cartas
- **Cartas** (`/cards`) - Exploración de base de datos de cartas
- **FAQ** (`/faq`) - Preguntas frecuentes

## 🎨 Diseño

El proyecto utiliza un sistema de diseño moderno con:

- **Paleta de colores**: Azules primarios con grises secundarios
- **Tipografía**: Inter para una apariencia limpia y profesional
- **Componentes**: Diseño modular y reutilizable
- **Responsive**: Adaptable a todos los tamaños de pantalla
- **Animaciones**: Transiciones suaves y efectos hover

## 🔮 Roadmap

### Fase 1 - Base (Actual)
- ✅ Estructura del proyecto
- ✅ Frontend básico con React
- ✅ Diseño y navegación
- ✅ Páginas principales

### Fase 2 - Funcionalidad Core
- [ ] Backend con FastAPI
- [ ] Base de datos de cartas Marvel
- [ ] Sistema de autenticación
- [ ] CRUD de mazos

### Fase 3 - Características Avanzadas
- [ ] Búsqueda y filtros avanzados
- [ ] Compartir mazos
- [ ] Sistema de comentarios
- [ ] Estadísticas de cartas

### Fase 4 - IA y Machine Learning
- [ ] Recomendaciones inteligentes
- [ ] Análisis de mazos
- [ ] Predicción de estrategias

## 👨‍💻 Desarrollo

Este proyecto forma parte de un Trabajo de Fin de Grado (TFG) y está diseñado para demostrar habilidades en desarrollo web moderno, diseño de interfaces y arquitectura de software.

## 📄 Licencia

Este proyecto es parte de un TFG académico. Todos los derechos reservados.

---

**Desarrollado con ❤️ para la comunidad de coleccionistas Marvel**