"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { User } from "@/types";
import { api } from "./api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    async function loadAuth() {
      const storedToken = localStorage.getItem("access_token");
      if (!storedToken) {
        setIsLoading(false);
        if (pathname !== "/login" && pathname !== "/register") {
          router.push("/login");
        }
        return;
      }

      try {
        setToken(storedToken);
        const currentUser = await api.getMe(storedToken);
        setUser(currentUser);
      } catch (err: any) {
        console.warn("Session expired or invalid token:", err);
        localStorage.removeItem("access_token");
        setToken(null);
        setUser(null);
        if (pathname !== "/login" && pathname !== "/register") {
          router.push("/login");
        }
      } finally {
        setIsLoading(false);
      }
    }

    loadAuth();
  }, [pathname, router]);

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem("access_token", newToken);
    setToken(newToken);
    setUser(newUser);
    router.push("/");
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
