import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, Upload, BarChart3, Cpu, LogOut, Sparkles } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const nav = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/input", label: "Input", icon: Upload },
  { to: "/app/processing", label: "Processing", icon: Cpu },
  { to: "/app/results", label: "Results", icon: BarChart3 },
];

export function AppShell() {
  const { welcome, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen bg-flyer-gradient text-white">
      <aside className="hidden w-64 flex-col border-r border-white/10 bg-black/20 backdrop-blur-xl md:flex">
        <div className="flex items-center gap-2 border-b border-white/10 p-6">
          <Sparkles className="h-8 w-8 text-cyan-300" />
          <div>
            <p className="font-display text-xl uppercase leading-tight tracking-tight">
              SkyPipe
            </p>
            <p className="text-xs uppercase tracking-[0.2em] text-white/50">
              Pipeline
            </p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-4">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold uppercase tracking-wider transition ${
                  isActive
                    ? "bg-white/15 text-white"
                    : "text-white/60 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>
        <button
          type="button"
          onClick={() => {
            logout();
            navigate("/login");
          }}
          className="m-4 flex items-center justify-center gap-2 rounded-xl border border-white/20 py-3 text-sm uppercase tracking-widest text-white/80 hover:bg-white/10"
        >
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-white/10 bg-black/30 px-4 py-4 backdrop-blur-md md:px-8">
          <div className="md:hidden">
            <p className="font-display text-lg uppercase">SkyPipe</p>
          </div>
          <p className="font-sans text-sm font-semibold tracking-wide text-white md:text-base">
            {welcome}
          </p>
          <div className="flex gap-2 md:hidden">
            {nav.map(({ to, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className="rounded-lg border border-white/20 p-2"
              >
                <Icon className="h-5 w-5" />
              </NavLink>
            ))}
          </div>
        </header>
        <main className="relative flex-1 overflow-auto p-4 md:p-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
