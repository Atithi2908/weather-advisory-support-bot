import {
  AdvisoryResponse,
  ConversationDetail,
  ConversationSummary,
  User,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errMsg = `Request failed (${res.status})`;
      try {
        const errData = await res.json();
        errMsg = errData.detail || errData.message || errMsg;
      } catch {
        // Fallback to text
        const text = await res.text();
        if (text) errMsg = text;
      }
      throw new ApiError(errMsg, res.status);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return await res.json();
  } catch (error: any) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      `Unable to connect to the backend server (${API_BASE}). Please ensure the backend is running.`,
      0
    );
  }
}

export const api = {
  // Auth
  async register(email: string, password: string): Promise<User> {
    return request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async login(
    email: string,
    password: string
  ): Promise<{ access_token: string; token_type: string; user: User }> {
    return request<{ access_token: string; token_type: string; user: User }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }
    );
  },

  async getMe(token: string): Promise<User> {
    return request<User>("/auth/me", { method: "GET" }, token);
  },

  // Conversations
  async listConversations(token: string): Promise<ConversationSummary[]> {
    return request<ConversationSummary[]>("/conversations", { method: "GET" }, token);
  },

  async getConversation(token: string, id: string): Promise<ConversationDetail> {
    return request<ConversationDetail>(`/conversations/${id}`, { method: "GET" }, token);
  },

  async createConversation(
    token: string,
    title: string = "New Weather Chat"
  ): Promise<ConversationDetail> {
    return request<ConversationDetail>(
      "/conversations",
      {
        method: "POST",
        body: JSON.stringify({ title }),
      },
      token
    );
  },

  async deleteConversation(token: string, id: string): Promise<void> {
    return request<void>(`/conversations/${id}`, { method: "DELETE" }, token);
  },

  // Advisory
  async postAdvisory(
    query: string,
    conversationId?: string | null,
    token?: string | null
  ): Promise<AdvisoryResponse> {
    return request<AdvisoryResponse>(
      "/advisory",
      {
        method: "POST",
        body: JSON.stringify({
          query,
          conversation_id: conversationId || undefined,
        }),
      },
      token
    );
  },
};
