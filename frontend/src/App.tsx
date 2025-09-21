import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import DecksPage from './pages/DecksPage'
import CardsPage from './pages/CardsPage'
import FAQPage from './pages/FAQPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/decks" element={<DecksPage />} />
        <Route path="/cards" element={<CardsPage />} />
        <Route path="/faq" element={<FAQPage />} />
      </Routes>
    </Layout>
  )
}

export default App
