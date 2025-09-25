import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Card, CardSet } from '../types/card'
import { apiService } from '../services/api'

const SetCardsPage: React.FC = () => {
  const { setId } = useParams<{ setId: string }>()
  const [cards, setCards] = useState<Card[]>([])
  const [setInfo, setSetInfo] = useState<CardSet | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      if (!setId) return
      
      try {
        setLoading(true)
        setError(null)
        
        // Obtener información del set y sus cartas
        const [setsResponse, cardsResponse] = await Promise.all([
          apiService.getSets(),
          apiService.getCardsBySet(parseInt(setId))
        ])
        
        // Encontrar la información del set
        const set = setsResponse.find(s => s.id === parseInt(setId))
        if (!set) {
          throw new Error('Set no encontrado')
        }
        
        setSetInfo(set)
        setCards(cardsResponse.cards)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [setId])

  const getAspectColor = (aspect: string) => {
    switch (aspect) {
      case 'aggression': return 'bg-red-100 text-red-800 border-red-200'
      case 'justice': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'leadership': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'protection': return 'bg-green-100 text-green-800 border-green-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'hero': return 'bg-purple-100 text-purple-800'
      case 'ally': return 'bg-orange-100 text-orange-800'
      case 'event': return 'bg-pink-100 text-pink-800'
      case 'upgrade': return 'bg-indigo-100 text-indigo-800'
      case 'support': return 'bg-teal-100 text-teal-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-accent-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-secondary-600">Cargando cartas...</p>
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
        <Link 
          to="/cards" 
          className="px-6 py-3 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-medium"
        >
          Volver a Cartas
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center py-8">
        <Link 
          to="/cards" 
          className="inline-flex items-center text-accent-600 hover:text-accent-700 mb-4"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Volver a Cartas
        </Link>
        
        <h1 className="text-4xl font-display font-bold text-primary-800 mb-4">
          {setInfo?.name}
        </h1>
        <p className="text-xl text-secondary-600 mb-2">
          Cartas del set
        </p>
        <p className="text-secondary-500">
          {cards.length} cartas disponibles
        </p>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {cards.map((card) => (
          <div key={card.id} className="bg-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-shadow duration-300 border-2 border-transparent hover:border-accent-200">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-semibold text-secondary-800 pr-2">
                {card.name}
              </h3>
              <span className="bg-accent-500 text-white px-2 py-1 rounded text-sm font-bold flex-shrink-0">
                {card.cost}
              </span>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className={`px-2 py-1 rounded text-xs font-medium border ${getAspectColor(card.aspect)}`}>
                  {card.aspect}
                </span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(card.type)}`}>
                  {card.type}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {cards.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-secondary-600 mb-2">
            No hay cartas en este set
          </h3>
          <p className="text-secondary-500">
            Las cartas aparecerán aquí cuando estén disponibles
          </p>
        </div>
      )}
    </div>
  )
}

export default SetCardsPage
