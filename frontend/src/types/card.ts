export interface Card {
  id: number
  name: string
  aspect: 'aggression' | 'justice' | 'leadership' | 'protection'
  type: 'hero' | 'ally' | 'event' | 'upgrade' | 'support'
  cost: number
  set: string
}

export interface CardSet {
  id: number
  name: string
  description: string
  releaseDate: string
  cardCount: number
}
