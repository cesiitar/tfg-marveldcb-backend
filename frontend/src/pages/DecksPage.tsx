import React from 'react'

const DecksPage: React.FC = () => {
  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-secondary-800 mb-4">Mazos</h1>
        <p className="text-xl text-secondary-600 mb-8">
          Gestiona y crea tus mazos de cartas Marvel
        </p>
      </div>

      <div className="bg-white rounded-xl p-8 shadow-lg">
        <div className="text-center py-16">
          <div className="w-24 h-24 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-12 h-12 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-secondary-800 mb-4">
            Próximamente
          </h2>
          <p className="text-secondary-600 mb-6">
            La funcionalidad de mazos estará disponible pronto. 
            Podrás crear, editar y compartir tus colecciones de cartas.
          </p>
          <button className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors duration-200 font-medium">
            Crear Primer Mazo
          </button>
        </div>
      </div>
    </div>
  )
}

export default DecksPage
