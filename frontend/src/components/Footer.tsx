import React from 'react'

const Footer: React.FC = () => {
  return (
    <footer className="bg-primary-800 text-white py-12 mt-16">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Logo y descripción */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-8 h-8 bg-accent-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-display font-bold">M</span>
              </div>
              <span className="text-xl font-display font-bold text-accent-400">MarvelCDB</span>
            </div>
            <p className="text-gray-300 mb-4">
              Tu plataforma definitiva para gestionar y explorar tu colección de cartas Marvel. 
              Crea mazos, descubre nuevas cartas y conecta con otros coleccionistas.
            </p>
          </div>

          {/* Enlaces rápidos */}
          <div>
            <h3 className="text-lg font-semibold mb-4 text-accent-400">Enlaces Rápidos</h3>
            <ul className="space-y-2">
              <li><a href="/decks" className="text-gray-300 hover:text-accent-400 transition-colors">My Decks</a></li>
              <li><a href="/cards" className="text-gray-300 hover:text-accent-400 transition-colors">Cards</a></li>
              <li><a href="/faq" className="text-gray-300 hover:text-accent-400 transition-colors">FAQs</a></li>
            </ul>
          </div>

          {/* Contacto */}
          <div>
            <h3 className="text-lg font-semibold mb-4 text-accent-400">Contacto</h3>
            <ul className="space-y-2">
              <li className="text-gray-300">Soporte</li>
              <li className="text-gray-300">Comunidad</li>
              <li className="text-gray-300">Reportar Bug</li>
            </ul>
          </div>
        </div>

        <div className="border-t border-primary-700 mt-8 pt-8 text-center">
          <p className="text-gray-400">
            © 2024 MarvelCDB. Proyecto TFG - Todos los derechos reservados.
          </p>
        </div>
      </div>
    </footer>
  )
}

export default Footer
