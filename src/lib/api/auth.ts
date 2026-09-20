import type { Session, User } from "@supabase/supabase-js";
import { getSupabase } from "@/lib/supabase";

export interface AuthError {
  message: string;
}

/**
 * Owner authentication via Supabase Auth. These functions run only in the
 * browser; they are never imported by server-side code.
 */

export async function signUp(
  email: string,
  password: string,
): Promise<{ user: User | null; session: Session | null; error: AuthError | null }> {
  const { data, error } = await getSupabase().auth.signUp({ email, password });
  return { user: data.user, session: data.session, error: error ? { message: error.message } : null };
}

export async function signIn(
  email: string,
  password: string,
): Promise<{ user: User | null; session: Session | null; error: AuthError | null }> {
  const { data, error } = await getSupabase().auth.signInWithPassword({ email, password });
  return { user: data.user, session: data.session, error: error ? { message: error.message } : null };
}

export async function signOut(): Promise<{ error: AuthError | null }> {
  const { error } = await getSupabase().auth.signOut();
  return { error: error ? { message: error.message } : null };
}

export async function getSession(): Promise<Session | null> {
  const { data } = await getSupabase().auth.getSession();
  return data.session;
}

export async function getUser(): Promise<User | null> {
  const { data } = await getSupabase().auth.getUser();
  return data.user ?? null;
}

/** Returns the current access token for calling the Dscape backend. */
export async function getAccessToken(): Promise<string | null> {
  const session = await getSession();
  return session?.access_token ?? null;
}

export function onAuthStateChange(
  callback: (session: Session | null) => void,
): { data: { subscription: { unsubscribe: () => void } } } {
  return getSupabase().auth.onAuthStateChange((_event, session) => callback(session));
}
