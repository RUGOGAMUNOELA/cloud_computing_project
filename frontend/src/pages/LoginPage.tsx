import { motion } from "framer-motion";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Sparkles } from "lucide-react";

export function LoginPage() {
  const [u, setU] = useState("admin");
  const [p, setP] = useState("skypipe");
  const [err, setErr] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await login(u, p);
      navigate("/app/dashboard");
    } catch {
      setErr("Invalid credentials. Default: admin / skypipe (change in .env).");
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-flyer-gradient px-4">
      <motion.div
        className="pointer-events-none absolute inset-0 opacity-40"
        animate={{
          background: [
            "radial-gradient(circle at 20% 30%, #ff2d95 0%, transparent 40%)",
            "radial-gradient(circle at 80% 20%, #00d4ff 0%, transparent 45%)",
            "radial-gradient(circle at 50% 70%, #a855f7 0%, transparent 50%)",
            "radial-gradient(circle at 20% 30%, #ff2d95 0%, transparent 40%)",
          ],
        }}
        transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative z-10 w-full max-w-md glass-panel p-10"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <Sparkles className="mb-4 h-12 w-12 text-cyan-300" />
          <h1 className="font-display text-4xl uppercase tracking-tight text-white">
            SkyPipe
          </h1>
          <p className="mt-2 text-xs uppercase tracking-[0.35em] text-white/50">
            Admin access
          </p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-widest text-white/50">
              Username
            </label>
            <input
              className="glass-input"
              value={u}
              onChange={(e) => setU(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-widest text-white/50">
              Password
            </label>
            <input
              type="password"
              className="glass-input"
              value={p}
              onChange={(e) => setP(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {err && <p className="text-sm text-rose-300">{err}</p>}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            className="w-full rounded-xl bg-gradient-to-r from-fuchsia-600 to-cyan-500 py-4 font-display text-lg uppercase tracking-widest text-white shadow-lg shadow-fuchsia-900/40"
          >
            Enter dashboard
          </motion.button>
        </form>
      </motion.div>
    </div>
  );
}
