import React, { useState } from 'react'
import { Link } from 'react-router-dom'

const Header: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="bg-primary-800 shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center py-3">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-accent-500 rounded-lg flex items-center justify-center shadow-lg">
              <span className="text-white font-display font-bold text-2xl">M</span>
            </div>
            <span className="text-accent-400 font-display font-bold text-3xl">MarvelCDB</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-8">
            <Link 
              to="/decks" 
              className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200 text-lg"
            >
              My Decks
            </Link>
            <Link 
              to="/decklists" 
              className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200 text-lg"
            >
              Decklists
            </Link>
            <Link 
              to="/cards" 
              className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200 text-lg"
            >
              Cards
            </Link>
            <Link 
              to="/reviews" 
              className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200 text-lg"
            >
              Reviews
            </Link>
            <Link 
              to="/rules" 
              className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200 text-lg"
            >
              Rules
            </Link>
            <Link 
              to="/faq" 
              className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200 text-lg"
            >
              FAQs
            </Link>
          </nav>

          {/* Auth Buttons */}
          <div className="hidden md:flex space-x-4">
            <button className="px-4 py-2 text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200">
              Login
            </button>
            <button className="px-6 py-2 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-medium">
              Sign Up
            </button>
          </div>

          {/* Mobile Menu Button */}
          <button 
            className="md:hidden p-2 text-gray-300 hover:text-accent-400"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-primary-700">
            <nav className="flex flex-col space-y-4">
              <Link 
                to="/decks" 
                className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200"
                onClick={() => setIsMenuOpen(false)}
              >
                My Decks
              </Link>
              <Link 
                to="/decklists" 
                className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200"
                onClick={() => setIsMenuOpen(false)}
              >
                Decklists
              </Link>
              <Link 
                to="/cards" 
                className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200"
                onClick={() => setIsMenuOpen(false)}
              >
                Cards
              </Link>
              <Link 
                to="/reviews" 
                className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200"
                onClick={() => setIsMenuOpen(false)}
              >
                Reviews
              </Link>
              <Link 
                to="/rules" 
                className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200"
                onClick={() => setIsMenuOpen(false)}
              >
                Rules
              </Link>
              <Link 
                to="/faq" 
                className="text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200"
                onClick={() => setIsMenuOpen(false)}
              >
                FAQs
              </Link>
              <div className="flex flex-col space-y-2 pt-4 border-t border-primary-700">
                <button className="px-4 py-2 text-gray-300 hover:text-accent-400 font-medium transition-colors duration-200 text-left">
                  Login
                </button>
                <button className="px-4 py-2 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors duration-200 font-medium text-left">
                  Sign Up
                </button>
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  )
}

export default Header
