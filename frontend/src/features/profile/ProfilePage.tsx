import { useState } from "react";
import { KeyRound, Mail, Moon, Sun } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  Money,
  PageHeader,
  StatCard,
} from "../../design/primitives";
import { api, ApiError } from "../../lib/api";
import { MemberDashboard } from "../../lib/types";
import { useApi } from "../../lib/useApi";
import { useAuth } from "../../stores/auth";

export default function ProfilePage() {
  const { user, theme, setTheme } = useAuth();
  const dashboard = useApi<MemberDashboard>("/users/me/dashboard");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [msg, setMsg] = useState<{ tone: "pos" | "neg"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [emailTo, setEmailTo] = useState(user?.email ?? "");
  const [mailBusy, setMailBusy] = useState(false);
  const [mailMsg, setMailMsg] = useState<{ tone: "pos" | "neg"; text: string } | null>(null);

  async function sendSettlement() {
    setMailBusy(true);
    setMailMsg(null);
    try {
      const res = await api.post<{
        delivered: boolean;
        transport: string;
        to: string;
        reason?: string;
        path?: string;
      }>("/users/me/settlement-email", { to: emailTo });
      if (res.delivered) {
        setMailMsg({ tone: "pos", text: `Ausstandsaufstellung an ${res.to} versendet.` });
      } else {
        setMailMsg({
          tone: "pos",
          text: `E-Mail erzeugt (${res.transport}). ${res.reason ?? ""} Ablage: ${res.path ?? ""}`.trim(),
        });
      }
    } catch (err) {
      setMailMsg({ tone: "neg", text: err instanceof ApiError ? err.message : "Versand fehlgeschlagen." });
    } finally {
      setMailBusy(false);
    }
  }

  async function changePassword() {
    setBusy(true);
    setMsg(null);
    try {
      await api.post("/auth/change-password", { old_password: oldPassword, new_password: newPassword });
      setMsg({ tone: "pos", text: "Passwort geändert." });
      setOldPassword("");
      setNewPassword("");
    } catch (err) {
      setMsg({ tone: "neg", text: err instanceof ApiError ? err.message : "Änderung fehlgeschlagen." });
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <>
      <PageHeader eyebrow="Konto" title="Profil" subtitle="Deine Daten, dein Saldo und deine Einstellungen." />

      <div className="grid lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader title="Persönliche Daten" />
          <div className="grid sm:grid-cols-2 gap-x-6 gap-y-5 text-sm">
            <div>
              <div className="text-2xs uppercase tracking-[0.12em] text-muted">Name</div>
              <div className="mt-1">
                {user.first_name} {user.last_name}
              </div>
            </div>
            <div>
              <div className="text-2xs uppercase tracking-[0.12em] text-muted">E-Mail</div>
              <div className="mt-1">{user.email}</div>
            </div>
            <div>
              <div className="text-2xs uppercase tracking-[0.12em] text-muted">Verbindungsstatus</div>
              <div className="mt-1">
                <Badge>{user.membership_status}</Badge>
              </div>
            </div>
            <div>
              <div className="text-2xs uppercase tracking-[0.12em] text-muted">Rolle</div>
              <div className="mt-1 capitalize">{user.system_role}</div>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="Darstellung" />
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink">Farbschema</span>
            <div className="inline-flex rounded-md border border-line p-0.5">
              <button
                onClick={() => setTheme("light")}
                className={
                  theme === "light"
                    ? "flex items-center gap-2 rounded px-3 h-8 text-sm bg-accent-weak text-accent"
                    : "flex items-center gap-2 rounded px-3 h-8 text-sm text-muted"
                }
              >
                <Sun size={15} /> Hell
              </button>
              <button
                onClick={() => setTheme("dark")}
                className={
                  theme === "dark"
                    ? "flex items-center gap-2 rounded px-3 h-8 text-sm bg-accent-weak text-accent"
                    : "flex items-center gap-2 rounded px-3 h-8 text-sm text-muted"
                }
              >
                <Moon size={15} /> Dunkel
              </button>
            </div>
          </div>
        </Card>

        {dashboard.data && (
          <>
            <StatCard
              label="Mein Saldo"
              value={<Money value={dashboard.data.total_balance} showSign />}
              tone={dashboard.data.total_balance < 0 ? "neg" : "pos"}
              hint={dashboard.data.total_balance < 0 ? "Offener Ausstand" : "Guthaben"}
            />
            {dashboard.data.by_kassenbereich.map((a) => (
              <StatCard key={a.kassenbereich_id} label={a.name} value={<Money value={a.balance} showSign />} />
            ))}
          </>
        )}

        <Card className="lg:col-span-3">
          <CardHeader title="Passwort ändern" />
          <div className="grid sm:grid-cols-2 gap-4 max-w-xl">
            <Field label="Aktuelles Passwort">
              <Input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
            </Field>
            <Field label="Neues Passwort">
              <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            </Field>
          </div>
          {msg && (
            <div className="mt-4 max-w-xl">
              <Alert tone={msg.tone}>{msg.text}</Alert>
            </div>
          )}
          <div className="mt-5">
            <Button
              variant="primary"
              icon={<KeyRound size={16} />}
              loading={busy}
              disabled={!oldPassword || newPassword.length < 8}
              onClick={changePassword}
            >
              Passwort speichern
            </Button>
          </div>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader
            title="Ausstände per E-Mail"
            subtitle="Die Verrechnung sendet deine Ausstandsaufstellung an die angegebene Adresse."
          />
          <div className="flex flex-col sm:flex-row sm:items-end gap-4 max-w-xl">
            <Field label="Empfänger" className="flex-1">
              <Input
                type="email"
                value={emailTo}
                onChange={(e) => setEmailTo(e.target.value)}
                placeholder="name@example.com"
              />
            </Field>
            <Button
              variant="primary"
              icon={<Mail size={16} />}
              loading={mailBusy}
              disabled={!emailTo}
              onClick={sendSettlement}
            >
              E-Mail senden
            </Button>
          </div>
          {mailMsg && (
            <div className="mt-4 max-w-2xl">
              <Alert tone={mailMsg.tone}>{mailMsg.text}</Alert>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
