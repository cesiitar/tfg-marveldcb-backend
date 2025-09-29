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

      {/* Main Search Form */}
      <div className="bg-white rounded-xl p-8 shadow-lg border border-gray-100">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-800 flex items-center">
              <svg className="w-7 h-7 mr-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Filtros de Búsqueda
            </h2>
            <p className="text-gray-600 mt-2">Encuentra las cartas perfectas para tu mazo</p>
          </div>
          
          <form onSubmit={handleSearch} className="space-y-8">
            {/* Name */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center">
                <svg className="w-5 h-5 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                Nombre de la Carta
              </h3>
              <div className="relative">
                <input
                  type="text"
                  name="name"
                  value={searchForm.name}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 pl-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                  placeholder="Escribe el nombre de la carta..."
                />
                <svg className="absolute left-4 top-3.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>

            {/* Aspect */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center">
                <svg className="w-5 h-5 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                Clase de la Carta
              </h3>
              <div className="flex flex-wrap gap-3">
                {['aggression', 'justice', 'leadership', 'protection'].map((aspect) => (
                  <button
                    key={aspect}
                    type="button"
                    onClick={() => setSearchForm(prev => ({ ...prev, aspect: prev.aspect === aspect ? '' : aspect }))}
                    className={`px-6 py-3 rounded-lg font-semibold transition-all duration-200 capitalize ${
                      searchForm.aspect === aspect
                        ? 'bg-blue-600 text-white shadow-lg transform scale-105'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 hover:shadow-md'
                    }`}
                  >
                    {aspect}
                  </button>
                ))}
              </div>
            </div>

            {/* Type and Cost */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center">
                <svg className="w-5 h-5 mr-2 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                Tipo y Coste
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-gray-700">
                    Tipo de Carta
                  </label>
                  <div className="relative">
                    <select
                      name="type"
                      value={searchForm.type}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 appearance-none bg-white"
                    >
                      <option value="">Cualquiera</option>
                      <option value="hero">Héroe</option>
                      <option value="ally">Aliado</option>
                      <option value="event">Evento</option>
                      <option value="upgrade">Mejora</option>
                      <option value="support">Apoyo</option>
                    </select>
                    <svg className="absolute right-3 top-3.5 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-gray-700">
                    Coste de la Carta
                  </label>
                  <input
                    type="number"
                    name="cost"
                    value={searchForm.cost}
                    onChange={handleInputChange}
                    min="0"
                    max="10"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                    placeholder="Ej: 3"
                  />
                </div>
              </div>
            </div>

            {/* Set */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center">
                <svg className="w-5 h-5 mr-2 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                Set de Cartas
              </h3>
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-gray-700">
                  Seleccionar Set
                </label>
                <div className="relative">
                  <select
                    name="set_name"
                    value={searchForm.set_name}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 appearance-none bg-white"
                  >
                    <option value="">Cualquiera</option>
                    {sets.map((set) => (
                      <option key={set.id} value={set.name}>
                        {set.name} ({set.cardCount} cartas)
                      </option>
                    ))}
                  </select>
                  <svg className="absolute right-3 top-3.5 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Submit */}
            <div className="flex justify-between items-center pt-8 border-t border-gray-200">
              <button
                type="button"
                onClick={clearSearch}
                className="px-8 py-3 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-all duration-200 font-semibold flex items-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Limpiar Filtros
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-10 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 font-semibold disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Buscando...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    Buscar Cartas
                  </>
                )}
              </button>
            </div>
            </form>
      </div>

      {/* Results Section */}
      <div className="bg-white rounded-xl p-8 shadow-lg border border-gray-100">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-2xl font-bold text-gray-800 flex items-center">
            <svg className="w-7 h-7 mr-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Resultados de la Búsqueda
          </h3>
          {hasSearched && (
            <span className="bg-green-100 text-green-800 text-sm font-medium px-4 py-2 rounded-full">
              {searchResults.length} cartas encontradas
            </span>
          )}
        </div>
        
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {searchResults.map((card, index) => (
              <div key={index} className="bg-gradient-to-br from-gray-50 to-white border border-gray-200 rounded-xl p-5 hover:shadow-lg hover:border-blue-300 transition-all duration-300 hover:-translate-y-1">
                <h4 className="font-bold text-lg text-gray-900 mb-3 line-clamp-2">{card.name}</h4>
                
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 text-sm">Clase:</span>
                    <span className="font-semibold capitalize text-blue-600 bg-blue-50 px-2 py-1 rounded-full text-xs">
                      {card.clase}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 text-sm">Tipo:</span>
                    <span className="font-medium capitalize text-gray-800">{card.type}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 text-sm">Coste:</span>
                    <span className="font-bold text-lg text-green-600 bg-green-50 px-2 py-1 rounded-full">
                      {card.cost}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 text-sm">Set:</span>
                    <span className="font-medium text-sm text-purple-600 bg-purple-50 px-2 py-1 rounded-full">
                      {card.set}
                    </span>
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

