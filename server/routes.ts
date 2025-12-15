import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { hashPassword, verifyPassword, generateToken, verifyToken, extractTokenFromHeader } from "./auth";
import { insertUserSchema, updateUserSchema } from "@shared/schema";

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || "http://localhost:5001";

async function proxyToPython(req: Request, res: Response, path: string) {
  try {
    const response = await fetch(`${PYTHON_BACKEND_URL}${path}`, {
      method: req.method,
      headers: {
        "Content-Type": "application/json",
      },
      body: req.method !== "GET" ? JSON.stringify(req.body) : undefined,
    });

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    console.error("Error proxying to Python backend:", error);
    res.status(503).json({
      error: "AI service temporarily unavailable. Please try again.",
      message: {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: "I apologize, but the AI service is temporarily unavailable. Please try again in a moment.",
        timestamp: new Date().toISOString(),
        flightResults: [],
      },
      conversationId: req.body?.conversationId || `conv-${Date.now()}`,
    });
  }
}

// Middleware to verify authentication
async function authenticateRequest(req: Request, res: Response, next: Function) {
  const token = extractTokenFromHeader(req.headers.authorization);
  if (!token) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const payload = verifyToken(token);
  if (!payload) {
    return res.status(401).json({ error: "Invalid or expired token" });
  }

  (req as any).userId = payload.userId;
  next();
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  // Auth Routes
  app.post("/api/auth/register", async (req: Request, res: Response) => {
    try {
      const parsed = insertUserSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ error: parsed.error.errors[0].message });
      }

      const existingEmail = await storage.getUserByEmail(parsed.data.email);
      if (existingEmail) {
        return res.status(409).json({ error: "Email already registered" });
      }

      const existingUsername = await storage.getUserByUsername(parsed.data.username);
      if (existingUsername) {
        return res.status(409).json({ error: "Username already taken" });
      }

      const passwordHash = await hashPassword(parsed.data.password);
      const user = await storage.createUser(parsed.data, passwordHash);

      const token = generateToken(user);
      const { passwordHash: _, ...userWithoutPassword } = user;

      res.status(201).json({
        user: userWithoutPassword,
        token,
      });
    } catch (error) {
      console.error("Register error:", error);
      res.status(500).json({ error: "Registration failed" });
    }
  });

  app.post("/api/auth/login", async (req: Request, res: Response) => {
    try {
      const { email, password } = req.body;

      if (!email || !password) {
        return res.status(400).json({ error: "Email and password required" });
      }

      const user = await storage.getUserByEmail(email);
      if (!user) {
        return res.status(401).json({ error: "Invalid credentials" });
      }

      const isValidPassword = await verifyPassword(password, user.passwordHash);
      if (!isValidPassword) {
        return res.status(401).json({ error: "Invalid credentials" });
      }

      const token = generateToken(user);
      const { passwordHash: _, ...userWithoutPassword } = user;

      res.json({
        user: userWithoutPassword,
        token,
      });
    } catch (error) {
      console.error("Login error:", error);
      res.status(500).json({ error: "Login failed" });
    }
  });

  app.get("/api/auth/me", authenticateRequest, async (req: Request, res: Response) => {
    try {
      const userId = (req as any).userId;
      const user = await storage.getUser(userId);

      if (!user) {
        return res.status(404).json({ error: "User not found" });
      }

      const { passwordHash: _, ...userWithoutPassword } = user;
      res.json(userWithoutPassword);
    } catch (error) {
      console.error("Get user error:", error);
      res.status(500).json({ error: "Failed to fetch user" });
    }
  });

  app.put("/api/auth/profile", authenticateRequest, async (req: Request, res: Response) => {
    try {
      const userId = (req as any).userId;
      const parsed = updateUserSchema.safeParse(req.body);

      if (!parsed.success) {
        return res.status(400).json({ error: parsed.error.errors[0].message });
      }

      const user = await storage.updateUser(userId, parsed.data);
      if (!user) {
        return res.status(404).json({ error: "User not found" });
      }

      const { passwordHash: _, ...userWithoutPassword } = user;
      res.json(userWithoutPassword);
    } catch (error) {
      console.error("Update profile error:", error);
      res.status(500).json({ error: "Failed to update profile" });
    }
  });

  // Chat Routes
  app.post("/api/chat", async (req: Request, res: Response) => {
    await proxyToPython(req, res, "/api/chat");
  });

  app.get("/api/health", async (req: Request, res: Response) => {
    await proxyToPython(req, res, "/api/health");
  });

  app.get("/api/conversations/:id", async (req: Request, res: Response) => {
    await proxyToPython(req, res, `/api/conversations/${req.params.id}`);
  });

  app.get("/api/conversations", async (req: Request, res: Response) => {
    const userId = req.query.userId || "default-user";
    await proxyToPython(req, res, `/api/conversations?userId=${userId}`);
  });

  return httpServer;
}
