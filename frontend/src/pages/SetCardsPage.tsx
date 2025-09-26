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
        // Ordenar cartas por aspecto (clase), luego por coste, luego por nombre
        const aspectOrder = ['hero', 'aggression', 'justice', 'leadership', 'protection', 'basic', 'campaign', 'pool']
        const sortedCards = cardsResponse.cards.sort((a, b) => {
          // Primero por aspecto
          const aspectA = a.aspect || 'basic'
          const aspectB = b.aspect || 'basic'
          const aspectIndexA = aspectOrder.indexOf(aspectA)
          const aspectIndexB = aspectOrder.indexOf(aspectB)
          
          if (aspectIndexA !== aspectIndexB) {
            return aspectIndexA - aspectIndexB
          }
          
          // Luego por coste
          if (a.cost !== b.cost) {
            return a.cost - b.cost
          }
          
          // Finalmente por nombre
          return a.name.localeCompare(b.name)
        })
        setCards(sortedCards)
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
      case 'hero': return 'bg-purple-100 text-purple-800 border-purple-200'
      case 'aggression': return 'bg-red-100 text-red-800 border-red-200'
      case 'justice': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'leadership': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'protection': return 'bg-green-100 text-green-800 border-green-200'
      case 'basic': return 'bg-gray-100 text-gray-800 border-gray-200'
      case 'campaign': return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'pool': return 'bg-teal-100 text-teal-800 border-teal-200'
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
          {setInfo?.description}
        </p>
        <p className="text-secondary-500">
          {cards.length} cartas • Lanzado en {setInfo?.releaseDate}
        </p>
      </div>

      {/* Cards Table */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gradient-to-r from-primary-50 to-accent-50">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-secondary-700 uppercase tracking-wider">
                  Carta
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-secondary-700 uppercase tracking-wider">
                  Aspecto
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-secondary-700 uppercase tracking-wider">
                  Tipo
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-secondary-700 uppercase tracking-wider">
                  Coste
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {cards.map((card, index) => {
                const prevCard = index > 0 ? cards[index - 1] : null
                const isNewAspect = !prevCard || prevCard.aspect !== card.aspect
                
                return (
                  <React.Fragment key={card.id}>
                    {isNewAspect && (
                      <tr className="bg-gray-100">
                        <td colSpan={4} className="px-6 py-3">
                          <div className="flex items-center">
                            <span className={`px-3 py-1 rounded-full text-sm font-bold border ${getAspectColor(card.aspect)}`}>
                              {card.aspect.toUpperCase()}
                            </span>
                            <span className="ml-2 text-sm text-gray-600">
                              ({cards.filter(c => c.aspect === card.aspect).length} cartas)
                            </span>
                          </div>
                        </td>
                      </tr>
                    )}
                    <tr className={`hover:bg-gray-50 transition-colors duration-200 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-25'}`}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-8 h-8 bg-accent-100 rounded-lg flex items-center justify-center mr-3">
                            <span className="text-sm font-bold text-accent-700">
                              {card.id}
                            </span>
                          </div>
                          <div>
                            <div className="text-sm font-semibold text-secondary-800">
                              {card.name}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getAspectColor(card.aspect)}`}>
                          {card.aspect}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getTypeColor(card.type)}`}>
                          {card.type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="bg-accent-500 text-white px-3 py-1 rounded-full text-sm font-bold">
                          {card.cost}
                        </span>
                      </td>
                    </tr>
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
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
