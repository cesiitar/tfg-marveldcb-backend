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

      {/* Quick Actions */}
      <section className="py-16 bg-white rounded-2xl shadow-lg">
        <h2 className="text-3xl font-bold text-center text-secondary-800 mb-12">
          Acciones Rápidas
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Link 
            to="/decks" 
            className="group p-6 bg-gradient-to-br from-accent-50 to-accent-100 rounded-xl hover:from-accent-100 hover:to-accent-200 transition-all duration-300"
          >
            <div className="text-center">
              <div className="w-16 h-16 bg-accent-500 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
                <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-secondary-800 mb-2">Mis Mazos</h3>
              <p className="text-secondary-600 text-sm">Gestiona tus colecciones</p>
            </div>
          </Link>

          <Link 
            to="/cards" 
            className="group p-6 bg-gradient-to-br from-primary-50 to-primary-100 rounded-xl hover:from-primary-100 hover:to-primary-200 transition-all duration-300"
          >
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-500 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
                <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M9.5 3A6.5 6.5 0 0 1 16 9.5c0 1.61-.59 3.09-1.56 4.23l.27.27h.79l5 5-1.5 1.5-5-5v-.79l-.27-.27A6.516 6.516 0 0 1 9.5 16 6.5 6.5 0 0 1 3 9.5 6.5 6.5 0 0 1 9.5 3m0 2C7 5 5 7 5 9.5S7 14 9.5 14 14 12 14 9.5 12 5 9.5 5z"/>
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-secondary-800 mb-2">Buscar Cartas</h3>
              <p className="text-secondary-600 text-sm">Explora la colección</p>
            </div>
          </Link>

          <Link 
            to="/faq" 
            className="group p-6 bg-gradient-to-br from-green-50 to-green-100 rounded-xl hover:from-green-100 hover:to-green-200 transition-all duration-300"
          >
            <div className="text-center">
              <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
                <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-secondary-800 mb-2">FAQ</h3>
              <p className="text-secondary-600 text-sm">Preguntas frecuentes</p>
            </div>
          </Link>

          <div className="group p-6 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl hover:from-purple-100 hover:to-purple-200 transition-all duration-300">
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-500 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
                <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-secondary-800 mb-2">Próximamente</h3>
              <p className="text-secondary-600 text-sm">Nuevas funciones</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export default HomePage
