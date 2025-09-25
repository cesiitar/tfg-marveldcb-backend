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
