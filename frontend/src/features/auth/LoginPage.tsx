import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Lock, Mail } from "lucide-react";
import { Alert, Button, Field, Input } from "../../design/primitives";
import { useAuth } from "../../stores/auth";

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anmeldung fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-bg">
      {/* Brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-accent text-accent-ink">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-md bg-accent-ink/15 grid place-items-center text-sm font-semibold">
            B7
          </div>
          <span className="text-sm font-semibold tracking-tight">Bierkasse7</span>
        </div>
        <div className="max-w-md">
          <h1 className="text-3xl font-semibold tracking-tight leading-tight">
            Buchhaltung für Studentenverbindungen — präzise, ruhig, nachvollziehbar.
          </h1>
          <p className="mt-5 text-sm text-accent-ink/80 leading-relaxed">
            Doppelte Buchführung, Kassenbereiche und Ringbrett in einer Oberfläche, die sich auf das
            Wesentliche konzentriert.
          </p>
        </div>
        <div className="text-2xs text-accent-ink/60 uppercase tracking-[0.16em]">
          Kassenbereiche · Ringbrett · Doppelte Buchführung
        </div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="h-9 w-9 rounded-md bg-accent text-accent-ink grid place-items-center text-sm font-semibold">
              B7
            </div>
            <span className="text-sm font-semibold tracking-tight">Bierkasse7</span>
          </div>

          <h2 className="text-xl font-semibold tracking-tight">Anmelden</h2>
          <p className="mt-2 text-sm text-muted">Bitte mit deinen Zugangsdaten anmelden.</p>

          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            <Field label="E-Mail">
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                <Input
                  type="email"
                  autoComplete="username"
                  className="pl-9"
                  placeholder="name@verbindung.de"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </Field>

            <Field label="Passwort">
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                <Input
                  type="password"
                  autoComplete="current-password"
                  className="pl-9"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </Field>

            {error && <Alert tone="neg" title="Anmeldung fehlgeschlagen">{error}</Alert>}

            <Button type="submit" variant="primary" className="w-full" loading={loading} icon={<ArrowRight size={16} />}>
              Anmelden
            </Button>
          </form>

          <p className="mt-8 text-xs text-muted">
            Zugang vergessen? Bitte an den Kassenwart wenden – die Zugangsdaten werden
            individuell vergeben.
          </p>
        </div>
      </div>
    </div>
  );
}
