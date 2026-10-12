import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BookOpen,
  CalendarDays,
  CalendarRange,
  ClipboardList,
  Disc3,
  Landmark,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Receipt,
  ReceiptText,
  Sun,
  UserCircle,
  Users,
} from "lucide-react";
import { Dialog, cx } from "../design/primitives";
import { useAuth } from "../stores/auth";

type NavItem = { to: string; label: string; icon: React.ReactNode };

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Übersicht",
    items: [
      { to: "/", label: "Dashboard", icon: <LayoutDashboard size={18} /> },
      { to: "/buchungen", label: "Buchungen", icon: <BookOpen size={18} /> },
      { to: "/kassenbereiche", label: "Kassenbereiche", icon: <Landmark size={18} /> },
    ],
  },
  {
    group: "Betrieb",
    items: [
      { to: "/ringbrett", label: "Ringbrett", icon: <Disc3 size={18} /> },
      { to: "/veranstaltungen", label: "Veranstaltungen", icon: <CalendarDays size={18} /> },
      { to: "/getraenke", label: "Getränke", icon: <Receipt size={18} /> },
      { to: "/inventur", label: "Inventur", icon: <ClipboardList size={18} /> },
    ],
  },
  {
    group: "Verwaltung",
    items: [
      { to: "/erstattungen", label: "Erstattungen", icon: <ReceiptText size={18} /> },
      { to: "/mitglieder", label: "Mitglieder", icon: <Users size={18} /> },
      { to: "/semester", label: "Semester", icon: <CalendarRange size={18} /> },
      { to: "/profil", label: "Profil", icon: <UserCircle size={18} /> },
    ],
  },
];

const MOBILE_PRIMARY: NavItem[] = [
  { to: "/", label: "Dashboard", icon: <LayoutDashboard size={20} /> },
  { to: "/buchungen", label: "Buchungen", icon: <BookOpen size={20} /> },
  { to: "/kassenbereiche", label: "Kassen", icon: <Landmark size={20} /> },
  { to: "/ringbrett", label: "Ringbrett", icon: <Disc3 size={20} /> },
];

function NavRow({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      onClick={onNavigate}
      title={item.label}
      className={({ isActive }) =>
        cx(
          "group flex items-center gap-3 rounded-md px-3 h-10 text-sm font-medium transition-colors",
          "lg:justify-start justify-center",
          isActive ? "bg-accent-weak text-accent" : "text-muted hover:text-ink hover:bg-bg",
        )
      }
    >
      <span className="shrink-0">{item.icon}</span>
      <span className="hidden lg:inline">{item.label}</span>
    </NavLink>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-8 w-8 rounded-md bg-accent text-accent-ink grid place-items-center text-sm font-semibold">
        B7
      </div>
      {!compact && (
        <div className="hidden lg:block leading-tight">
          <div className="text-sm font-semibold tracking-tight">Bierkasse7</div>
          <div className="text-2xs text-muted">Verbindungsbuchhaltung</div>
        </div>
      )}
    </div>
  );
}

export default function AppShell() {
  const { user, logout, theme, toggleTheme } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const initials = user ? `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase() : "?";

  return (
    <div className="min-h-screen bg-bg">
      {/* Sidebar (tablet + desktop) */}
      <aside className="hidden md:flex fixed inset-y-0 left-0 z-30 flex-col w-[76px] lg:w-64 border-r border-line bg-surface">
        <div className="h-16 flex items-center px-4 lg:px-6 border-b border-line">
          <Brand />
        </div>
        <nav className="flex-1 overflow-y-auto px-3 lg:px-4 py-5 space-y-6">
          {NAV.map((section) => (
            <div key={section.group}>
              <div className="hidden lg:block px-3 mb-2 text-2xs font-medium uppercase tracking-[0.14em] text-muted/80">
                {section.group}
              </div>
              <div className="space-y-1">
                {section.items.map((item) => (
                  <NavRow key={item.to} item={item} />
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="border-t border-line p-3 lg:p-4">
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="flex items-center gap-3 rounded-md px-3 h-10 w-full text-sm font-medium text-muted hover:text-ink hover:bg-bg transition-colors lg:justify-start justify-center"
            title="Abmelden"
          >
            <LogOut size={18} />
            <span className="hidden lg:inline">Abmelden</span>
          </button>
        </div>
      </aside>

      {/* Topbar */}
      <header className="sticky top-0 z-20 md:pl-[76px] lg:pl-64">
        <div className="h-16 flex items-center justify-between gap-4 px-5 sm:px-8 border-b border-line bg-bg/85 backdrop-blur">
          <div className="md:hidden">
            <Brand />
          </div>
          <div className="hidden md:block" />
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="h-9 w-9 grid place-items-center rounded-md text-muted hover:text-ink hover:bg-surface border border-transparent hover:border-line transition"
              aria-label="Farbschema wechseln"
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <div className="flex items-center gap-2.5 rounded-md border border-line bg-surface pl-1.5 pr-3 h-9">
              <span className="h-6 w-6 rounded-full bg-accent-weak text-accent grid place-items-center text-2xs font-semibold">
                {initials}
              </span>
              <span className="hidden sm:block text-xs font-medium text-ink">{user?.first_name}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="md:pl-[76px] lg:pl-64">
        <div className="px-5 sm:px-8 py-8 pb-28 md:pb-12 max-w-[1400px] mx-auto">
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 border-t border-line bg-surface/95 backdrop-blur">
        <div className="grid grid-cols-5 h-16">
          {MOBILE_PRIMARY.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cx(
                  "flex flex-col items-center justify-center gap-1 text-2xs font-medium transition-colors",
                  isActive ? "text-accent" : "text-muted",
                )
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
          <button
            onClick={() => setMenuOpen(true)}
            className="flex flex-col items-center justify-center gap-1 text-2xs font-medium text-muted"
          >
            <Menu size={20} />
            <span>Mehr</span>
          </button>
        </div>
      </nav>

      <Dialog open={menuOpen} onClose={() => setMenuOpen(false)} title="Menü">
        <div className="space-y-6">
          {NAV.map((section) => (
            <div key={section.group}>
              <div className="px-1 mb-2 text-2xs font-medium uppercase tracking-[0.14em] text-muted/80">
                {section.group}
              </div>
              <div className="grid grid-cols-2 gap-2">
                {section.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    onClick={() => setMenuOpen(false)}
                    className={({ isActive }) =>
                      cx(
                        "flex items-center gap-3 rounded-md border px-4 h-12 text-sm font-medium",
                        isActive ? "border-accent/40 bg-accent-weak text-accent" : "border-line text-ink",
                      )
                    }
                  >
                    {item.icon}
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="flex items-center gap-3 rounded-md border border-line px-4 h-12 w-full text-sm font-medium text-neg"
          >
            <LogOut size={18} /> Abmelden
          </button>
        </div>
      </Dialog>
    </div>
  );
}
