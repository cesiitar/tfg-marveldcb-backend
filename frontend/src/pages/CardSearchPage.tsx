import React, { useState } from 'react'

const CardSearchPage: React.FC = () => {
  const [searchForm, setSearchForm] = useState({
    name: '',
    text: '',
    aspect: '',
    type: '',
    cost: '',
    attack: '',
    health: ''
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setSearchForm(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Buscando cartas:', searchForm)
    // Aquí irá la lógica de búsqueda
  }

  return (
    <div className="space-y-8">
      <div className="text-center py-8">
        <h1 className="text-4xl font-display font-bold text-primary-800 mb-4">Búsqueda de Cartas</h1>
        <p className="text-xl text-secondary-600 mb-8">
          Encuentra las cartas perfectas para tu mazo
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar - Browse by Set */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-secondary-800 mb-4">Explorar por Set</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {[
                'Core Set',
                'The Green Goblin',
                'Captain America',
                'Thor',
                'Doctor Strange',
                'Hulk',
                'The Rise of Red Skull',
                'Quicksilver',
                'Scarlet Witch',
                'Gamora',
                'Drax',
                'Venom',
                'The Mad Titan\'s Shadow',
                'Mutant Genesis',
                'Wolverine',
                'Storm',
                'Deadpool',
                'Age of Apocalypse',
                'Agents of S.H.I.E.L.D.',
                'Ronan Modular Set'
              ].map((set, index) => (
                <button
                  key={index}
                  className="w-full text-left px-3 py-2 text-secondary-600 hover:text-accent-600 hover:bg-accent-50 rounded transition-colors duration-200"
                >
                  {index + 1}. {set}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Main Search Form */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-xl p-8 shadow-lg">
            <form onSubmit={handleSearch} className="space-y-8">
              {/* Name and Texts */}
              <div>
                <h3 className="text-lg font-semibold text-secondary-800 mb-4">Nombre y Texto</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Nombre
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
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Texto
                    </label>
                    <input
                      type="text"
                      name="text"
                      value={searchForm.text}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent"
                      placeholder="Buscar en texto..."
                    />
                  </div>
                </div>
              </div>

              {/* Aspect */}
              <div>
                <h3 className="text-lg font-semibold text-secondary-800 mb-4">Aspecto</h3>
                <div className="flex flex-wrap gap-2">
                  {['Pool', 'Aggression', 'Basic', 'Campaign', 'Encounter', 'Hero', 'Justice', 'Leadership', 'Protection'].map((aspect) => (
                    <button
                      key={aspect}
                      type="button"
                      onClick={() => setSearchForm(prev => ({ ...prev, aspect: prev.aspect === aspect ? '' : aspect }))}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors duration-200 ${
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

              {/* Attributes */}
              <div>
                <h3 className="text-lg font-semibold text-secondary-800 mb-4">Atributos</h3>
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
                      className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent"
                      placeholder="Coste..."
                    />
                  </div>
                </div>
              </div>

              {/* Numerics */}
              <div>
                <h3 className="text-lg font-semibold text-secondary-800 mb-4">Valores Numéricos</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Ataque
                    </label>
                    <input
                      type="number"
                      name="attack"
                      value={searchForm.attack}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent"
                      placeholder="Ataque..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Salud
                    </label>
                    <input
                      type="number"
                      name="health"
                      value={searchForm.health}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent"
                      placeholder="Salud..."
                    />
                  </div>
                </div>
              </div>

              {/* Submit */}
              <div className="flex justify-between items-center pt-6 border-t border-secondary-200">
                <div className="flex items-center space-x-4">
                  <label className="flex items-center">
                    <input type="checkbox" className="mr-2" />
                    <span className="text-sm text-secondary-700">Solo cartas de jugador</span>
                  </label>
                </div>
                <button
                  type="submit"
                  className="px-8 py-3 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-semibold"
                >
                  Buscar Cartas
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Results Section */}
      <div className="bg-white rounded-xl p-8 shadow-lg">
        <h3 className="text-lg font-semibold text-secondary-800 mb-4">Resultados</h3>
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
      </div>
    </div>
  )
}

export default CardSearchPage

