export interface Card {
  name: string
  clase: 'aggression' | 'justice' | 'leadership' | 'protection'
  type: 'hero' | 'ally' | 'event' | 'upgrade' | 'support'
  cost: number
  set: string
}

export interface CardSet {
  id: number
  name: string
  cardCount: number
}
