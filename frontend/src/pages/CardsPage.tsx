import React from 'react'

const CardsPage: React.FC = () => {
  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-secondary-800 mb-4">Cartas</h1>
        <p className="text-xl text-secondary-600 mb-8">
          Explora nuestra colección de cartas Marvel
        </p>
      </div>

      <div className="bg-white rounded-xl p-8 shadow-lg">
        <div className="text-center py-16">
          <div className="w-24 h-24 bg-secondary-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-12 h-12 text-secondary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-secondary-800 mb-4">
            Base de Datos en Construcción
          </h2>
          <p className="text-secondary-600 mb-6">
            Estamos trabajando en una extensa base de datos de cartas Marvel. 
            Pronto podrás buscar, filtrar y explorar todas las cartas disponibles.
          </p>
          <button className="px-6 py-3 bg-secondary-600 text-white rounded-lg hover:bg-secondary-700 transition-colors duration-200 font-medium">
            Explorar Cartas
          </button>
        </div>
      </div>
    </div>
  )
}

export default CardsPage
