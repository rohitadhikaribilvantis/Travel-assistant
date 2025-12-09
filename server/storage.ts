import { randomUUID } from "crypto";
import type { User, InsertUser, Conversation, ChatMessage } from "@shared/schema";

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  getConversation(id: string): Promise<Conversation | undefined>;
  getConversationsByUser(userId: string): Promise<Conversation[]>;
  createConversation(userId: string): Promise<Conversation>;
  addMessageToConversation(conversationId: string, message: ChatMessage): Promise<Conversation | undefined>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private conversations: Map<string, Conversation>;

  constructor() {
    this.users = new Map();
    this.conversations = new Map();
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = randomUUID();
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  async getConversation(id: string): Promise<Conversation | undefined> {
    return this.conversations.get(id);
  }

  async getConversationsByUser(userId: string): Promise<Conversation[]> {
    return Array.from(this.conversations.values()).filter(
      (conv) => conv.userId === userId
    );
  }

  async createConversation(userId: string): Promise<Conversation> {
    const id = randomUUID();
    const now = new Date().toISOString();
    const conversation: Conversation = {
      id,
      userId,
      messages: [],
      createdAt: now,
      updatedAt: now,
    };
    this.conversations.set(id, conversation);
    return conversation;
  }

  async addMessageToConversation(
    conversationId: string,
    message: ChatMessage
  ): Promise<Conversation | undefined> {
    const conversation = this.conversations.get(conversationId);
    if (!conversation) return undefined;

    conversation.messages.push(message);
    conversation.updatedAt = new Date().toISOString();
    this.conversations.set(conversationId, conversation);
    return conversation;
  }
}

export const storage = new MemStorage();
