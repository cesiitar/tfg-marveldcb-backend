import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { CardSet } from '../types/card'
import { apiService } from '../services/api'

const CardsPage: React.FC = () => {
  const [sets, setSets] = useState<CardSet[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSets = async () => {
      try {
        setLoading(true)
        setError(null)
        const setsData = await apiService.getSets()
        setSets(setsData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al cargar los sets')
      } finally {
        setLoading(false)
      }
    }

    fetchSets()
  }, [])

  const getSetColor = (index: number) => {
    const colors = [
      'from-red-50 to-red-100 border-red-200',
      'from-blue-50 to-blue-100 border-blue-200',
      'from-yellow-50 to-yellow-100 border-yellow-200',
      'from-green-50 to-green-100 border-green-200',
      'from-purple-50 to-purple-100 border-purple-200',
      'from-orange-50 to-orange-100 border-orange-200',
      'from-teal-50 to-teal-100 border-teal-200',
      'from-pink-50 to-pink-100 border-pink-200'
    ]
    return colors[index % colors.length]
  }

  const getSetIcon = (index: number) => {
    const icons = [
      <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 24 24" key={index}>
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
      </svg>,
      <svg className="w-8 h-8 text-blue-600" fill="currentColor" viewBox="0 0 24 24" key={index}>
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
      </svg>,
      <svg className="w-8 h-8 text-yellow-600" fill="currentColor" viewBox="0 0 24 24" key={index}>
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
      </svg>,
      <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 24 24" key={index}>
        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
      </svg>
    ]
    return icons[index % icons.length]
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-accent-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-secondary-600">Cargando sets de cartas...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h2 className="text-2xl font-semibold text-secondary-800 mb-4">Error</h2>
        <p className="text-secondary-600 mb-6">{error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="px-6 py-3 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-medium"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="text-center py-8">
        <h1 className="text-4xl font-display font-bold text-primary-800 mb-4">Cartas</h1>
        <p className="text-xl text-secondary-600 mb-8">
          Explora las cartas organizadas por set/expansión
        </p>
        <Link 
          to="/cards/search" 
          className="px-6 py-3 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-medium"
        >
          Buscar Cartas
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {sets.map((set, index) => (
          <Link 
            key={set.id}
            to={`/cards/set/${set.id}`}
            className={`bg-gradient-to-br ${getSetColor(index)} rounded-xl p-6 shadow-lg border-2 hover:shadow-xl transition-all duration-300 hover:scale-105`}
          >
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center mr-4 shadow-md">
                {getSetIcon(index)}
              </div>
              <div>
                <h2 className="text-2xl font-display font-bold text-secondary-800">
                  {set.name}
                </h2>
                <p className="text-secondary-600">
                  {set.cardCount} cartas
                </p>
              </div>
            </div>
            
            <p className="text-secondary-700 mb-4">
              {set.description}
            </p>

            <div className="flex justify-between items-center">
              <span className="text-sm text-secondary-500">
                Lanzado en {set.releaseDate}
              </span>
              <svg className="w-5 h-5 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </Link>
        ))}
      </div>

      {/* Search Section */}
      <div className="bg-gradient-to-r from-primary-50 to-accent-50 rounded-xl p-8 text-center">
        <h2 className="text-2xl font-semibold text-secondary-800 mb-4">
          ¿No encuentras lo que buscas?
        </h2>
        <p className="text-secondary-600 mb-6">
          Usa nuestro buscador avanzado para encontrar cartas específicas por nombre, aspecto, tipo, coste y más.
        </p>
      
      </div>
    </div>
  )
}

export default CardsPage
