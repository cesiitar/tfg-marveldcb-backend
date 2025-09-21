import React from 'react'

const FAQPage: React.FC = () => {
  const faqs = [
    {
      question: "¿Qué es MarvelDCB?",
      answer: "MarvelDCB es una plataforma web diseñada para coleccionistas de cartas Marvel. Permite crear mazos, explorar cartas y conectar con otros fans."
    },
    {
      question: "¿Cómo puedo crear mi primer mazo?",
      answer: "Una vez que la funcionalidad esté disponible, podrás crear mazos desde la sección 'Mazos' usando nuestro constructor intuitivo."
    },
    {
      question: "¿Es gratis usar la plataforma?",
      answer: "Sí, MarvelDCB es completamente gratuito para todos los usuarios. No hay costos ocultos ni suscripciones premium."
    },
    {
      question: "¿Puedo compartir mis mazos con otros usuarios?",
      answer: "¡Por supuesto! Una de las características principales será la capacidad de compartir tus creaciones con la comunidad."
    },
    {
      question: "¿Cuándo estará disponible la IA?",
      answer: "La funcionalidad de IA se implementará en una fase posterior del proyecto, una vez que la plataforma base esté completamente funcional."
    }
  ]

  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-secondary-800 mb-4">Preguntas Frecuentes</h1>
        <p className="text-xl text-secondary-600 mb-8">
          Encuentra respuestas a las preguntas más comunes sobre MarvelDCB
        </p>
      </div>

      <div className="max-w-4xl mx-auto space-y-6">
        {faqs.map((faq, index) => (
          <div key={index} className="bg-white rounded-xl p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-secondary-800 mb-3">
              {faq.question}
            </h3>
            <p className="text-secondary-600">
              {faq.answer}
            </p>
          </div>
        ))}
      </div>

      <div className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl p-8 text-center">
        <h2 className="text-2xl font-semibold text-secondary-800 mb-4">
          ¿No encuentras tu pregunta?
        </h2>
        <p className="text-secondary-600 mb-6">
          Si tienes alguna pregunta específica sobre MarvelDCB, no dudes en contactarnos.
        </p>
        <button className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors duration-200 font-medium">
          Contactar Soporte
        </button>
      </div>
    </div>
  )
}

export default FAQPage
