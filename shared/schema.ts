export interface FlightOffer {
  id: string;
  price: Record<string, any>;
  itineraries: any[];
  numberOfBookableSeats?: number;
  validatingAirlineCodes?: string[];
  travelClass?: string;
  tags?: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  flightResults?: FlightOffer[];
  isStreaming?: boolean;
  memoryContext?: string;
  appliedPrefs?: string;
}

export interface ChatResponse {
  message: ChatMessage;
  conversationId: string;
  extractedPreferences?: string[];
  appliedPrefs?: string;
}

export interface User {
  id: string;
  email: string;
  username: string;
  fullName?: string;
  avatar?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Conversation {
  id: string;
  userId: string;
  title: string;
  messages: ChatMessage[];
  archived: boolean;
  createdAt: string;
  updatedAt: string;
}
