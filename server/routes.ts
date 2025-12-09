import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";

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

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
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
