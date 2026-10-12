import { useState } from "react";
import { Plus, UserCheck, UserX, Users } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Dialog,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th,
} from "../../design/primitives";
import { api, ApiError } from "../../lib/api";
import { Member } from "../../lib/types";
import { useApi } from "../../lib/useApi";
import { useAuth } from "../../stores/auth";

const STATUSES = ["CB", "IaCB", "IdC", "F", "Spef", "FcK", "AH", "AH-IdC", "CK", "EXT"];
const ROLES = [
  { id: "admin", label: "Administrator" },
  { id: "senior", label: "Senior" },
  { id: "buchhalter", label: "Buchhalter" },
  { id: "organisator", label: "Organisator" },
  { id: "mitglied", label: "Mitglied" },
  { id: "gast", label: "Gast" },
];

export default function MembersPage() {
  const can = useAuth((s) => s.can);
  const members = useApi<Member[]>(can("user:manage") ? "/users" : null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    membership_status: "CB",
    system_role: "mitglied",
  });

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/users", { ...form, is_active: true });
      setOpen(false);
      setForm({ email: "", password: "", first_name: "", last_name: "", membership_status: "CB", system_role: "mitglied" });
      members.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Anlegen fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(m: Member) {
    try {
      await api.post(`/users/${m.id}/${m.is_active ? "deactivate" : "activate"}`);
      members.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Aktion fehlgeschlagen.");
    }
  }

  if (!can("user:manage")) {
    return (
      <>
        <PageHeader eyebrow="Verwaltung" title="Mitglieder" />
        <Card>
          <EmptyState icon={<Users size={28} />} title="Keine Berechtigung" description="Die Mitgliederverwaltung ist Administratoren vorbehalten." />
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Verwaltung"
        title="Mitglieder"
        subtitle="Benutzer, Verbindungsstatus und Rollen verwalten."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setOpen(true)}>
            Mitglied
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Alert tone="neg">{error}</Alert>
        </div>
      )}

      <Card padded={false}>
        {members.loading ? (
          <Spinner />
        ) : members.data && members.data.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th className="pl-6">Name</Th>
                <Th>E-Mail</Th>
                <Th align="center">Status</Th>
                <Th>Rolle</Th>
                <Th align="center">Aktiv</Th>
                <Th align="right" className="pr-6">Aktion</Th>
              </tr>
            </thead>
            <tbody>
              {members.data.map((m) => (
                <tr key={m.id} className="hover:bg-bg/60">
                  <Td className="pl-6">
                    <div className="flex items-center gap-3">
                      <span className="h-8 w-8 rounded-full bg-accent-weak text-accent grid place-items-center text-2xs font-semibold">
                        {m.first_name[0]}
                        {m.last_name[0]}
                      </span>
                      <span>
                        {m.first_name} {m.last_name}
                      </span>
                    </div>
                  </Td>
                  <Td className="text-muted">{m.email}</Td>
                  <Td align="center">
                    <Badge>{m.membership_status}</Badge>
                  </Td>
                  <Td className="text-muted">{ROLES.find((r) => r.id === m.system_role)?.label ?? m.system_role}</Td>
                  <Td align="center">
                    {m.is_active ? (
                      <Badge tone="pos">aktiv</Badge>
                    ) : (
                      <Badge tone="warn">inaktiv</Badge>
                    )}
                  </Td>
                  <Td align="right" className="pr-6">
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={m.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                      onClick={() => toggle(m)}
                    >
                      {m.is_active ? "Deaktivieren" : "Aktivieren"}
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState icon={<Users size={28} />} title="Keine Mitglieder" />
        )}
      </Card>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Neues Mitglied"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="primary" loading={busy} onClick={submit} disabled={!form.email || !form.first_name || !form.last_name}>
              Anlegen
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Vorname">
              <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </Field>
            <Field label="Nachname">
              <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </Field>
            <Field label="E-Mail" className="sm:col-span-2">
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Passwort (min. 8 Zeichen)" className="sm:col-span-2">
              <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </Field>
            <Field label="Verbindungsstatus">
              <Select value={form.membership_status} onChange={(e) => setForm({ ...form, membership_status: e.target.value })}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Systemrolle">
              <Select value={form.system_role} onChange={(e) => setForm({ ...form, system_role: e.target.value })}>
                {ROLES.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>
    </>
  );
}
