import { useMemo, useState } from "react";
import { Check, Disc3, Plus, Send } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Dialog,
  EmptyState,
  Field,
  Input,
  Money,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th,
} from "../../design/primitives";
import { api, ApiError } from "../../lib/api";
import { formatDate, todayISO } from "../../lib/format";
import { Kassenbereich, RingbrettSession } from "../../lib/types";
import { useApi } from "../../lib/useApi";

type DirectoryEntry = { id: string; name: string; membership_status: string };
type Prices = { red: number; yellow: number };

export default function RingbrettPage() {
  const sessions = useApi<RingbrettSession[]>("/ringbrett-sessions");
  const areas = useApi<Kassenbereich[]>("/kassenbereiche");
  const directory = useApi<DirectoryEntry[]>("/users/directory");
  const prices = useApi<Prices>("/beverages/ring-prices");

  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(todayISO());
  const [areaId, setAreaId] = useState("");
  const [notes, setNotes] = useState("");
  const [rows, setRows] = useState<{ id: string; red: string; yellow: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const red = prices.data?.red ?? 0.7;
  const yellow = prices.data?.yellow ?? 1.0;

  const total = useMemo(
    () => rows.reduce((s, r) => s + (Number(r.red) || 0) * red + (Number(r.yellow) || 0) * yellow, 0),
    [rows, red, yellow],
  );

  function openNew() {
    setAreaId(areas.data?.find((a) => a.is_active)?.id ?? "");
    setRows((directory.data ?? []).map((d) => ({ id: d.id, red: "", yellow: "" })));
    setOpen(true);
  }

  async function submit() {
    setBusy(true);
    setError(null);
    const entries = rows
      .filter((r) => Number(r.red) > 0 || Number(r.yellow) > 0)
      .map((r) => ({ user_id: r.id, red_rings: Number(r.red) || 0, yellow_rings: Number(r.yellow) || 0 }));
    if (entries.length === 0) {
      setError("Mindestens ein Mitglied mit Ringen > 0 angeben.");
      setBusy(false);
      return;
    }
    try {
      await api.post("/ringbrett-sessions", {
        date,
        kassenbereich_id: areaId,
        notes: notes || undefined,
        entries,
      });
      setOpen(false);
      setNotes("");
      sessions.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Speichern fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function post(id: string) {
    try {
      await api.post(`/ringbrett-sessions/${id}/post`);
      sessions.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verbuchen fehlgeschlagen.");
    }
  }

  const areaName = (id: string) => areas.data?.find((a) => a.id === id)?.name ?? "—";

  return (
    <>
      <PageHeader
        eyebrow="Betrieb"
        title="Ringbrett"
        subtitle="Ringzählung erfassen und als ausgeglichene Buchung (Forderung je Mitglied) verbuchen."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={openNew}>
            Neue Zählung
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Alert tone="neg">{error}</Alert>
        </div>
      )}

      <Card padded={false}>
        {sessions.loading ? (
          <Spinner />
        ) : sessions.data && sessions.data.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th className="pl-6">Nr.</Th>
                <Th>Datum</Th>
                <Th>Kassenbereich</Th>
                <Th align="center">Positionen</Th>
                <Th align="center">Status</Th>
                <Th align="right" className="pr-6">Aktion</Th>
              </tr>
            </thead>
            <tbody>
              {sessions.data.map((s) => (
                <tr key={s.id} className="hover:bg-bg/60">
                  <Td className="pl-6 tnum text-muted">#{s.zaehlungsnummer}</Td>
                  <Td className="tnum whitespace-nowrap">{formatDate(s.date)}</Td>
                  <Td>{areaName(s.kassenbereich_id)}</Td>
                  <Td align="center" className="tnum">{s.entries.length}</Td>
                  <Td align="center">
                    {s.status === "posted" ? (
                      <Badge tone="pos">
                        <Check size={12} /> verbucht
                      </Badge>
                    ) : (
                      <Badge tone="warn">Entwurf</Badge>
                    )}
                  </Td>
                  <Td align="right" className="pr-6">
                    {s.status !== "posted" && (
                      <Button size="sm" variant="secondary" icon={<Send size={14} />} onClick={() => post(s.id)}>
                        Verbuchen
                      </Button>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState icon={<Disc3 size={28} />} title="Noch keine Ringzählungen" description="Erfasse die erste Zählung." />
        )}
      </Card>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Neue Ringzählung"
        width="max-w-2xl"
        footer={
          <>
            <div className="mr-auto text-sm">
              Gesamt: <Money value={total} className="font-semibold" />
            </div>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="primary" loading={busy} onClick={submit}>
              Speichern
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          <div className="grid sm:grid-cols-3 gap-4">
            <Field label="Datum">
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </Field>
            <Field label="Kassenbereich">
              <Select value={areaId} onChange={(e) => setAreaId(e.target.value)}>
                {areas.data?.filter((a) => a.is_active).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Notiz (optional)">
              <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
            </Field>
          </div>

          <div className="rounded-lg border border-line overflow-hidden">
            <Table>
              <thead>
                <tr>
                  <Th>Mitglied</Th>
                  <Th align="right" className="w-28">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-neg/70" /> Rot
                    </span>
                  </Th>
                  <Th align="right" className="w-28">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-warn/70" /> Gelb
                    </span>
                  </Th>
                  <Th align="right" className="w-28 pr-4">Betrag</Th>
                </tr>
              </thead>
              <tbody>
                {(directory.data ?? []).map((d, i) => {
                  const row = rows[i] ?? { id: d.id, red: "", yellow: "" };
                  const amount = (Number(row.red) || 0) * red + (Number(row.yellow) || 0) * yellow;
                  return (
                    <tr key={d.id}>
                      <Td>
                        <span className="text-ink">{d.name}</span>
                        <Badge className="ml-2">{d.membership_status}</Badge>
                      </Td>
                      <Td align="right">
                        <Input
                          className="tnum h-9 text-right"
                          inputMode="numeric"
                          value={row.red}
                          onChange={(e) => {
                            const next = [...rows];
                            next[i] = { ...row, red: e.target.value.replace(/\D/g, "") };
                            setRows(next);
                          }}
                        />
                      </Td>
                      <Td align="right">
                        <Input
                          className="tnum h-9 text-right"
                          inputMode="numeric"
                          value={row.yellow}
                          onChange={(e) => {
                            const next = [...rows];
                            next[i] = { ...row, yellow: e.target.value.replace(/\D/g, "") };
                            setRows(next);
                          }}
                        />
                      </Td>
                      <Td align="right" className="pr-4 tnum">
                        <Money value={amount} />
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          </div>
          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>
    </>
  );
}
