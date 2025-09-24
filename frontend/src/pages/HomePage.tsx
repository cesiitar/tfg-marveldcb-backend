import React from 'react'
import { Link } from 'react-router-dom'

const HomePage: React.FC = () => {
  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="text-center py-16">
        <h1 className="text-5xl md:text-6xl font-display font-bold text-primary-800 mb-6">
          Bienvenido a <span className="text-accent-500">MarvelCDB</span>
        </h1>
        <p className="text-xl text-secondary-600 mb-8 max-w-3xl mx-auto">
          La plataforma definitiva para coleccionistas de cartas Marvel. 
          Crea mazos, explora cartas y conecta con otros fans.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link 
            to="/decks" 
            className="px-8 py-3 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-semibold text-lg"
          >
            Explorar Mazos
          </Link>
          <Link 
            to="/cards" 
            className="px-8 py-3 border-2 border-accent-500 text-accent-600 rounded-lg hover:bg-accent-500 hover:text-white transition-colors duration-200 font-semibold text-lg"
          >
            Ver Cartas
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16">
        <h2 className="text-3xl font-bold text-center text-secondary-800 mb-12">
          ¿Por qué elegir MarvelCDB?
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white rounded-xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
            <div className="w-12 h-12 bg-accent-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-accent-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-secondary-800 mb-3">Gestión de Mazos</h3>
            <p className="text-secondary-600">
              Crea y organiza tus mazos de cartas de manera intuitiva. 
              Comparte tus creaciones con la comunidad.
            </p>
          </div>

          <div className="bg-white rounded-xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-primary-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9.5 3A6.5 6.5 0 0 1 16 9.5c0 1.61-.59 3.09-1.56 4.23l.27.27h.79l5 5-1.5 1.5-5-5v-.79l-.27-.27A6.516 6.516 0 0 1 9.5 16 6.5 6.5 0 0 1 3 9.5 6.5 6.5 0 0 1 9.5 3m0 2C7 5 5 7 5 9.5S7 14 9.5 14 14 12 14 9.5 12 5 9.5 5z"/>
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-secondary-800 mb-3">Base de Datos Completa</h3>
            <p className="text-secondary-600">
              Accede a una extensa colección de cartas Marvel con información 
              detallada y estadísticas actualizadas.
            </p>
          </div>

          <div className="bg-white rounded-xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zm4 18v-6h2.5l-2.54-7.63A1.5 1.5 0 0 0 18.54 8H16c-.8 0-1.54.37-2.01.99L12 11l-1.99-2.01A2.5 2.5 0 0 0 8 8H5.46c-.8 0-1.54.37-2.01.99L.91 16.37 3.5 22H6v-6h2v6h2v-6h2v6h2v-6h2v6h2z"/>
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-secondary-800 mb-3">Comunidad Activa</h3>
            <p className="text-secondary-600">
              Conecta con otros coleccionistas, comparte estrategias y 
              participa en eventos de la comunidad.
            </p>
          </div>
        </div>
      </section>

      {/* Featured Decks Section */}
      <section className="py-16 bg-white rounded-2xl shadow-lg">
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-3xl font-bold text-secondary-800">
            Mazos Destacados
          </h2>
          <Link 
            to="/decks" 
            className="px-6 py-2 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-medium"
          >
            Ver Todos
          </Link>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Placeholder para mazos - por ahora vacío */}
          <div className="text-center py-16 text-secondary-500">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-secondary-600 mb-2">
              No hay mazos aún
            </h3>
            <p className="text-secondary-500">
              Los mazos creados por la comunidad aparecerán aquí
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default HomePage
