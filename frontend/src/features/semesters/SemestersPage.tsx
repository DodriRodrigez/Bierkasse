import { useState } from "react";
import { CalendarRange, Lock, Plus } from "lucide-react";
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
import { formatDate } from "../../lib/format";
import { Semester } from "../../lib/types";
import { useApi } from "../../lib/useApi";
import { useAuth } from "../../stores/auth";

export default function SemestersPage() {
  const can = useAuth((s) => s.can);
  const semesters = useApi<Semester[]>("/semesters");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", type: "winter", start_date: "", end_date: "" });

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/semesters", form);
      setOpen(false);
      setForm({ name: "", type: "winter", start_date: "", end_date: "" });
      semesters.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Anlegen fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function close(id: string) {
    try {
      await api.post(`/semesters/${id}/close`);
      semesters.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Abschluss fehlgeschlagen.");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Verwaltung"
        title="Semester"
        subtitle="Abrechnungszeiträume verwalten und abschließen."
        actions={
          can("semester:manage") && (
            <Button variant="primary" icon={<Plus size={16} />} onClick={() => setOpen(true)}>
              Semester
            </Button>
          )
        }
      />

      {error && (
        <div className="mb-4">
          <Alert tone="neg">{error}</Alert>
        </div>
      )}

      <Card padded={false}>
        {semesters.loading ? (
          <Spinner />
        ) : semesters.data && semesters.data.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th className="pl-6">Name</Th>
                <Th>Typ</Th>
                <Th>Zeitraum</Th>
                <Th align="center">Status</Th>
                <Th align="right" className="pr-6">Aktion</Th>
              </tr>
            </thead>
            <tbody>
              {semesters.data.map((s) => (
                <tr key={s.id} className="hover:bg-bg/60">
                  <Td className="pl-6">{s.name}</Td>
                  <Td className="text-muted">{s.type === "winter" ? "Wintersemester" : "Sommersemester"}</Td>
                  <Td className="tnum text-muted">
                    {formatDate(s.start_date)} – {formatDate(s.end_date)}
                  </Td>
                  <Td align="center">
                    <Badge tone={s.status === "active" ? "pos" : "neutral"}>{s.status}</Badge>
                  </Td>
                  <Td align="right" className="pr-6">
                    {s.status === "active" && can("semester:close") && (
                      <Button size="sm" variant="secondary" icon={<Lock size={14} />} onClick={() => close(s.id)}>
                        Abschließen
                      </Button>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState icon={<CalendarRange size={28} />} title="Keine Semester" />
        )}
      </Card>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Neues Semester"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="primary" loading={busy} onClick={submit} disabled={!form.name || !form.start_date || !form.end_date}>
              Anlegen
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Name">
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="z. B. WiSe 2027/28" />
          </Field>
          <div className="grid sm:grid-cols-3 gap-4">
            <Field label="Typ">
              <Select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option value="winter">Winter</option>
                <option value="summer">Sommer</option>
              </Select>
            </Field>
            <Field label="Beginn">
              <Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
            </Field>
            <Field label="Ende">
              <Input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </Field>
          </div>
          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>
    </>
  );
}
