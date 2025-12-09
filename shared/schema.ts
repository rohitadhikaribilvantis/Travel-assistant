import { z } from "zod";

// Chat Message types
export const messageRoleSchema = z.enum(["user", "assistant", "system"]);
export type MessageRole = z.infer<typeof messageRoleSchema>;

export const flightSegmentSchema = z.object({
  departure: z.object({
    iataCode: z.string(),
    terminal: z.string().optional(),
    at: z.string(),
  }),
  arrival: z.object({
    iataCode: z.string(),
    terminal: z.string().optional(),
    at: z.string(),
  }),
  carrierCode: z.string(),
  carrierName: z.string().optional(),
  number: z.string(),
  aircraft: z.string().optional(),
  duration: z.string(),
  numberOfStops: z.number(),
});
export type FlightSegment = z.infer<typeof flightSegmentSchema>;

export const flightOfferSchema = z.object({
  id: z.string(),
  price: z.object({
    total: z.string(),
    currency: z.string(),
    base: z.string().optional(),
  }),
  itineraries: z.array(z.object({
    duration: z.string(),
    segments: z.array(flightSegmentSchema),
  })),
  numberOfBookableSeats: z.number().optional(),
  validatingAirlineCodes: z.array(z.string()).optional(),
  travelClass: z.string().optional(),
  tags: z.array(z.string()).optional(),
});
export type FlightOffer = z.infer<typeof flightOfferSchema>;

export const chatMessageSchema = z.object({
  id: z.string(),
  role: messageRoleSchema,
  content: z.string(),
  timestamp: z.string(),
  flightResults: z.array(flightOfferSchema).optional(),
  isStreaming: z.boolean().optional(),
  memoryContext: z.string().optional(),
});
export type ChatMessage = z.infer<typeof chatMessageSchema>;

// User preferences for mem0
export const userPreferencesSchema = z.object({
  preferredAirlines: z.array(z.string()).optional(),
  seatPreference: z.enum(["window", "aisle", "middle", "no_preference"]).optional(),
  cabinClass: z.enum(["economy", "premium_economy", "business", "first"]).optional(),
  maxStops: z.number().optional(),
  preferredTimeOfDay: z.enum(["morning", "afternoon", "evening", "night", "any"]).optional(),
  avoidRedEye: z.boolean().optional(),
  directFlightsOnly: z.boolean().optional(),
});
export type UserPreferences = z.infer<typeof userPreferencesSchema>;

// Flight search request
export const flightSearchRequestSchema = z.object({
  originLocationCode: z.string().min(3).max(3),
  destinationLocationCode: z.string().min(3).max(3),
  departureDate: z.string(),
  returnDate: z.string().optional(),
  adults: z.number().min(1).max(9).default(1),
  children: z.number().min(0).max(9).optional(),
  infants: z.number().min(0).max(9).optional(),
  travelClass: z.enum(["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]).optional(),
  nonStop: z.boolean().optional(),
  maxPrice: z.number().optional(),
  max: z.number().default(10),
});
export type FlightSearchRequest = z.infer<typeof flightSearchRequestSchema>;

// Chat request/response
export const chatRequestSchema = z.object({
  message: z.string().min(1),
  conversationId: z.string().optional(),
  userId: z.string().default("default-user"),
});
export type ChatRequest = z.infer<typeof chatRequestSchema>;

export const chatResponseSchema = z.object({
  message: chatMessageSchema,
  conversationId: z.string(),
});
export type ChatResponse = z.infer<typeof chatResponseSchema>;

// Conversation
export const conversationSchema = z.object({
  id: z.string(),
  userId: z.string(),
  messages: z.array(chatMessageSchema),
  createdAt: z.string(),
  updatedAt: z.string(),
});
export type Conversation = z.infer<typeof conversationSchema>;

// Legacy user schema for compatibility
export const insertUserSchema = z.object({
  username: z.string(),
  password: z.string(),
});
export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = InsertUser & { id: string };
