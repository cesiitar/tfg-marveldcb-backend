import React, { useState, useEffect } from 'react'
import { apiService } from '../services/api'
import { Card, CardSet } from '../types/card'

const CardSearchPage: React.FC = () => {
  const [searchForm, setSearchForm] = useState({
    name: '',
    aspect: '',
    type: '',
    cost: '',
    set_name: ''
  })
  
  const [sets, setSets] = useState<CardSet[]>([])
  const [searchResults, setSearchResults] = useState<Card[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // Cargar sets al montar el componente
  useEffect(() => {
    const loadSets = async () => {
      try {
        const setsData = await apiService.getSets()
        setSets(setsData)
      } catch (error) {
        console.error('Error loading sets:', error)
      }
    }
    loadSets()
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setSearchForm(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setHasSearched(true)
    
    try {
      const filters: any = {}
      
      if (searchForm.name.trim()) filters.name = searchForm.name.trim()
      if (searchForm.aspect) filters.aspect = searchForm.aspect
      if (searchForm.type) filters.type = searchForm.type
      if (searchForm.cost) filters.cost = parseInt(searchForm.cost)
      if (searchForm.set_name) filters.set_name = searchForm.set_name
      
      const results = await apiService.searchCards(filters)
      setSearchResults(results)
    } catch (error) {
      console.error('Error searching cards:', error)
      setSearchResults([])
    } finally {
      setIsLoading(false)
    }
  }

  const clearSearch = () => {
    setSearchForm({
      name: '',
      aspect: '',
      type: '',
      cost: '',
      set_name: ''
    })
    setSearchResults([])
    setHasSearched(false)
  }

  return (
    <div className="space-y-8">
      <div className="text-center py-8">
        <h1 className="text-4xl font-display font-bold text-primary-800 mb-4">Búsqueda de Cartas</h1>
        <p className="text-xl text-secondary-600 mb-8">
          Encuentra las cartas perfectas para tu mazo
        </p>
      </div>

      <div className="max-w-4xl mx-auto">
        {/* Main Search Form */}
          <div className="bg-white rounded-xl p-8 shadow-lg">
            <form onSubmit={handleSearch} className="space-y-8">
              {/* Name */}
              <div>
                <h3 className="text-lg font-semibold text-secondary-800 mb-4">Nombre</h3>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Nombre de la carta
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={searchForm.name}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent"
                    placeholder="Buscar por nombre..."
                  />
                </div>
              </div>

              {/* Aspect */}
              <div>
                <h3 className="text-lg font-semibold text-secondary-800 mb-4">Aspecto</h3>
                <div className="flex flex-wrap gap-2">
                  {['aggression', 'justice', 'leadership', 'protection'].map((aspect) => (
                    <button
                      key={aspect}
                      type="button"
                      onClick={() => setSearchForm(prev => ({ ...prev, aspect: prev.aspect === aspect ? '' : aspect }))}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors duration-200 capitalize ${
                        searchForm.aspect === aspect
                          ? 'bg-accent-500 text-white'
                          : 'bg-secondary-100 text-secondary-700 hover:bg-secondary-200'
                      }`}
                    >
                      {aspect}
                    </button>
                  ))}
                </div>
              </div>

              {/* Type and Cost */}
              <div>
                <h3 className="text-lg font-semibold text-secondary-800 mb-4">Tipo y Coste</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Tipo
                    </label>
                    <select
                      name="type"
                      value={searchForm.type}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent"
                    >
                      <option value="">Cualquiera</option>
                      <option value="hero">Héroe</option>
                      <option value="ally">Aliado</option>
                      <option value="event">Evento</option>
                      <option value="upgrade">Mejora</option>
                      <option value="support">Apoyo</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Coste
                    </label>
                    <input
                      type="number"
                      name="cost"
                      value={searchForm.cost}
                      onChange={handleInputChange}
                      min="0"
                      max="10"
                      className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent"
                      placeholder="Coste..."
                    />
                  </div>
                </div>
              </div>

              {/* Set */}
              <div>
                <h3 className="text-lg font-semibold text-secondary-800 mb-4">Set</h3>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Seleccionar Set
                  </label>
                  <select
                    name="set_name"
                    value={searchForm.set_name}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent"
                  >
                    <option value="">Cualquiera</option>
                    {sets.map((set) => (
                      <option key={set.id} value={set.name}>
                        {set.name} ({set.cardCount} cartas)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Submit */}
              <div className="flex justify-between items-center pt-6 border-t border-secondary-200">
                <button
                  type="button"
                  onClick={clearSearch}
                  className="px-6 py-2 text-secondary-600 border border-secondary-300 rounded-lg hover:bg-secondary-50 transition-colors duration-200"
                >
                  Limpiar
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-8 py-3 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Buscando...' : 'Buscar Cartas'}
                </button>
              </div>
            </form>
          </div>
      </div>

      {/* Results Section */}
      <div className="bg-white rounded-xl p-8 shadow-lg">
        <h3 className="text-lg font-semibold text-secondary-800 mb-4">
          Resultados {hasSearched && `(${searchResults.length} cartas encontradas)`}
        </h3>
        
        {isLoading ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-secondary-600 mb-2">
              Buscando cartas...
            </h4>
            <p className="text-secondary-500">
              Por favor espera mientras procesamos tu búsqueda
            </p>
          </div>
        ) : !hasSearched ? (
          <div className="text-center py-16 text-secondary-500">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.5 3A6.5 6.5 0 0 1 16 9.5c0 1.61-.59 3.09-1.56 4.23l.27.27h.79l5 5-1.5 1.5-5-5v-.79l-.27-.27A6.516 6.516 0 0 1 9.5 16 6.5 6.5 0 0 1 3 9.5 6.5 6.5 0 0 1 9.5 3m0 2C7 5 5 7 5 9.5S7 14 9.5 14 14 12 14 9.5 12 5 9.5 5z" />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-secondary-600 mb-2">
              No hay resultados aún
            </h4>
            <p className="text-secondary-500">
              Los resultados de tu búsqueda aparecerán aquí
            </p>
          </div>
        ) : searchResults.length === 0 ? (
          <div className="text-center py-16 text-secondary-500">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.29-1.009-5.824-2.57M15 6.343A7.962 7.962 0 0112 4c-2.34 0-4.29 1.009-5.824 2.57" />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-secondary-600 mb-2">
              No se encontraron cartas
            </h4>
            <p className="text-secondary-500">
              Intenta ajustar los filtros de búsqueda
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {searchResults.map((card) => (
              <div key={card.id} className="border border-secondary-200 rounded-lg p-4 hover:shadow-md transition-shadow duration-200">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-secondary-800 text-lg">{card.name}</h4>
                  <span className="text-sm text-secondary-500">#{card.id}</span>
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-secondary-600">Aspecto:</span>
                    <span className="font-medium capitalize text-accent-600">{card.aspect}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-secondary-600">Tipo:</span>
                    <span className="font-medium capitalize">{card.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-secondary-600">Coste:</span>
                    <span className="font-medium">{card.cost}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-secondary-600">Set:</span>
                    <span className="font-medium text-sm">{card.set}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default CardSearchPage

