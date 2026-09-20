import { createContext, use, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { getSession, getUser, onAuthStateChange, signIn, signOut, signUp, type AuthError } from "@/lib/api/auth";

interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<AuthError | null>;
  signUp: (email: string, password: string) => Promise<AuthError | null>;
  signOut: () => Promise<AuthError | null>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function restore() {
      try {
        const [sess, u] = await Promise.all([getSession(), getUser()]);
        if (!active) return;
        setSession(sess);
        setUser(u);
      } catch {
        // Supabase may be unconfigured during local dev; treat as signed out.
        if (active) {
          setSession(null);
          setUser(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    const { data } = onAuthStateChange((next) => {
      setSession(next);
      void getUser().then((u) => setUser(u)).catch(() => setUser(null));
    });

    void restore();

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      session,
      loading,
      async signIn(email, password) {
        const res = await signIn(email, password);
        return res.error;
      },
      async signUp(email, password) {
        const res = await signUp(email, password);
        return res.error;
      },
      async signOut() {
        const res = await signOut();
        setUser(null);
        setSession(null);
        return res.error;
      },
    }),
    [user, session, loading],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthState {
  const ctx = use(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }
  return ctx;
}
