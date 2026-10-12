import { useState } from "react";
import { Check, Plus, ReceiptText, X } from "lucide-react";
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
import { Kassenbereich, Refund } from "../../lib/types";
import { useApi } from "../../lib/useApi";
import { useAuth } from "../../stores/auth";

const STATUS_TONE: Record<string, "neutral" | "accent" | "pos" | "neg" | "warn"> = {
  pending: "warn",
  approved: "accent",
  rejected: "neg",
  paid: "pos",
};

export default function RefundsPage() {
  const can = useAuth((s) => s.can);
  const refunds = useApi<Refund[]>("/refunds");
  const areas = useApi<Kassenbereich[]>("/kassenbereiche");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ date: todayISO(), amount: "", description: "", kassenbereich_id: "" });

  const areaName = (id: string) => areas.data?.find((a) => a.id === id)?.name ?? "—";

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/refunds", {
        date: form.date,
        amount: Number(form.amount.replace(",", ".")),
        description: form.description,
        kassenbereich_id: form.kassenbereich_id || areas.data?.[0]?.id,
      });
      setOpen(false);
      setForm({ date: todayISO(), amount: "", description: "", kassenbereich_id: "" });
      refunds.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Antrag fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function act(id: string, action: "approve" | "reject") {
    try {
      await api.post(`/refunds/${id}/${action}`);
      refunds.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Aktion fehlgeschlagen.");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Verwaltung"
        title="Auslagenerstattungen"
        subtitle="Anträge erfassen, genehmigen und als Buchung buchen."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setOpen(true)}>
            Neuer Antrag
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Alert tone="neg">{error}</Alert>
        </div>
      )}

      <Card padded={false}>
        {refunds.loading ? (
          <Spinner />
        ) : refunds.data && refunds.data.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th className="pl-6">Datum</Th>
                <Th>Beschreibung</Th>
                <Th>Kassenbereich</Th>
                <Th align="right">Betrag</Th>
                <Th align="center">Status</Th>
                <Th align="right" className="pr-6">Aktion</Th>
              </tr>
            </thead>
            <tbody>
              {refunds.data.map((r) => (
                <tr key={r.id} className="hover:bg-bg/60">
                  <Td className="pl-6 tnum whitespace-nowrap">{formatDate(r.date)}</Td>
                  <Td className="max-w-sm truncate">{r.description}</Td>
                  <Td>{areaName(r.kassenbereich_id)}</Td>
                  <Td align="right" className="tnum">
                    <Money value={r.amount} />
                  </Td>
                  <Td align="center">
                    <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>
                  </Td>
                  <Td align="right" className="pr-6">
                    {r.status === "pending" && can("refund:approve") && (
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="secondary" icon={<Check size={14} />} onClick={() => act(r.id, "approve")}>
                          OK
                        </Button>
                        <Button size="sm" variant="ghost" icon={<X size={14} />} onClick={() => act(r.id, "reject")}>
                          Ablehnen
                        </Button>
                      </div>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState icon={<ReceiptText size={28} />} title="Keine Anträge" description="Es liegen keine Auslagenerstattungen vor." />
        )}
      </Card>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Neuer Erstattungsantrag"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="primary" loading={busy} onClick={submit} disabled={!form.amount || !form.description}>
              Einreichen
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Datum">
              <Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            </Field>
            <Field label="Betrag">
              <Input className="tnum" inputMode="decimal" placeholder="0,00" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </Field>
          </div>
          <Field label="Beschreibung">
            <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </Field>
          <Field label="Kassenbereich">
            <Select value={form.kassenbereich_id} onChange={(e) => setForm({ ...form, kassenbereich_id: e.target.value })}>
              <option value="">Bereich wählen …</option>
              {areas.data?.filter((a) => a.is_active).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </Field>
          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>
    </>
  );
}
