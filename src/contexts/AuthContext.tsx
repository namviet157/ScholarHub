import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import type { UserProfile } from "@/types/user";

/** Cột password trên bảng public.users được giữ NOT NULL; mật khẩu thật do Supabase Auth quản lý. */
const AUTH_PASSWORD_PLACEHOLDER = "__supabase_auth__";

export type SignUpInput = {
  fullname: string;
  email: string;
  password: string;
  university?: string;
  major?: string;
};

type AuthContextValue = {
  session: Session | null;
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (input: SignUpInput) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function ensureUserProfile(session: Session): Promise<void> {
  const uid = session.user.id;
  const { data: existing, error: selErr } = await supabase
    .from("users")
    .select("id")
    .eq("id", uid)
    .maybeSingle();
  if (selErr) throw new Error(selErr.message);
  if (existing) return;

  const meta = session.user.user_metadata as Record<string, string | undefined>;
  const fullname = meta.fullname || session.user.email?.split("@")[0] || "User";
  const email = session.user.email;
  if (!email) return;

  const row = {
    id: uid,
    fullname,
    email,
    university: meta.university?.trim() || null,
    major: meta.major?.trim() || null,
    password: AUTH_PASSWORD_PLACEHOLDER,
  };

  const { error: upErr } = await supabase.from("users").upsert(row, { onConflict: "email" });
  if (upErr) throw new Error(upErr.message);
}

async function fetchProfile(userId: string): Promise<UserProfile | null> {
  const { data, error } = await supabase
    .from("users")
    .select("id, fullname, email, university, major, created_at")
    .eq("id", userId)
    .maybeSingle();
  if (error) throw new Error(error.message);
  return data;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshProfile = useCallback(async () => {
    const {
      data: { session: s },
    } = await supabase.auth.getSession();
    const uid = s?.user?.id;
    if (!uid) {
      setProfile(null);
      return;
    }
    const p = await fetchProfile(uid);
    setProfile(p);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const applySession = async (next: Session | null) => {
      setSession(next);
      setUser(next?.user ?? null);
      if (next?.user) {
        try {
          await ensureUserProfile(next);
        } catch (e) {
          console.error("ensureUserProfile:", e);
        }
        try {
          const p = await fetchProfile(next.user.id);
          if (!cancelled) setProfile(p);
        } catch (e) {
          console.error("fetchProfile:", e);
          if (!cancelled) setProfile(null);
        }
      } else if (!cancelled) {
        setProfile(null);
      }
      if (!cancelled) setLoading(false);
    };

    supabase.auth.getSession().then(({ data: { session: s } }) => {
      if (!cancelled) void applySession(s);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      void applySession(s);
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return { error: error ? new Error(error.message) : null };
  }, []);

  const signUp = useCallback(async (input: SignUpInput) => {
    const { fullname, email, password, university, major } = input;
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          fullname,
          university: university ?? "",
          major: major ?? "",
        },
      },
    });
    return { error: error ? new Error(error.message) : null };
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
  }, []);

  const value = useMemo(
    () => ({
      session,
      user,
      profile,
      loading,
      signIn,
      signUp,
      signOut,
      refreshProfile,
    }),
    [session, user, profile, loading, signIn, signUp, signOut, refreshProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
