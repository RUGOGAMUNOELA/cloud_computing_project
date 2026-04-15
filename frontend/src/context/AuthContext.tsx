import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as api from "../api";

type AuthState = {
  ready: boolean;
  user: string | null;
  welcome: string;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<string | null>(null);
  const [welcome, setWelcome] = useState("Welcome Admin");

  useEffect(() => {
    const t = localStorage.getItem("skypipe_token");
    if (!t) {
      setReady(true);
      return;
    }
    api
      .me()
      .then((d) => {
        setUser(d.username);
        setWelcome(d.display_welcome || `Welcome ${d.username}`);
      })
      .catch(() => {
        api.logout();
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (u: string, p: string) => {
    await api.login(u, p);
    const d = await api.me();
    setUser(d.username);
    setWelcome(d.display_welcome || `Welcome ${d.username}`);
  }, []);

  const logout = useCallback(() => {
    api.logout();
    setUser(null);
    setWelcome("Welcome Admin");
  }, []);

  return (
    <Ctx.Provider value={{ ready, user, welcome, login, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const x = useContext(Ctx);
  if (!x) throw new Error("AuthProvider missing");
  return x;
}
