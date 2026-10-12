import { useState } from "react";
import { ArrowLeftRight, Landmark, Pencil, Plus } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Dialog,
  Field,
  Input,
  Money,
  PageHeader,
  Spinner,
} from "../../design/primitives";
import { api, ApiError } from "../../lib/api";
import { todayISO } from "../../lib/format";
import { Kassenbereich, KassenbereichBalance } from "../../lib/types";
import { useApi } from "../../lib/useApi";
import { useAuth } from "../../stores/auth";

export default function KassenbereichePage() {
  const can = useAuth((s) => s.can);
  const balances = useApi<KassenbereichBalance[]>("/kassenbereiche/balances");
  const areas = useApi<Kassenbereich[]>("/kassenbereiche");

  const [createOpen, setCreateOpen] = useState(false);
  const [edit, setEdit] = useState<Kassenbereich | null>(null);
  const [transferOpen, setTransferOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [form, setForm] = useState({ name: "", code: "", description: "", sort_order: 0 });
  const [transfer, setTransfer] = useState({ from: "", to: "", amount: "", note: "" });

  async function submitCreate() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/kassenbereiche", form);
      setCreateOpen(false);
      setForm({ name: "", code: "", description: "", sort_order: 0 });
      balances.reload();
      areas.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Anlegen fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function submitEdit(patch: Partial<Kassenbereich>) {
    if (!edit) return;
    setBusy(true);
    setError(null);
    try {
      await api.patch(`/kassenbereiche/${edit.id}`, patch);
      setEdit(null);
      balances.reload();
      areas.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Speichern fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function submitTransfer() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/kassenbereiche/transfer", {
        from_kassenbereich_id: transfer.from,
        to_kassenbereich_id: transfer.to,
        amount: Number(transfer.amount.replace(",", ".")),
        date: todayISO(),
        note: transfer.note || undefined,
      });
      setTransferOpen(false);
      setTransfer({ from: "", to: "", amount: "", note: "" });
      balances.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Umbuchung fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  const total = balances.data?.reduce((s, b) => s + b.balance, 0) ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Kassen"
        title="Kassenbereiche"
        subtitle="Interne Ansprüche getrennt von den tatsächlichen Zahlungskonten. Jede Buchungszeile wird einem Kassenbereich zugeordnet."
        actions={
          <>
            {can("transfer:create") && (
              <Button variant="secondary" icon={<ArrowLeftRight size={16} />} onClick={() => setTransferOpen(true)}>
                Interne Umbuchung
              </Button>
            )}
            {can("kassenbereich:manage") && (
              <Button variant="primary" icon={<Plus size={16} />} onClick={() => setCreateOpen(true)}>
                Kassenbereich
              </Button>
            )}
          </>
        }
      />

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {balances.loading && <Spinner />}
        {balances.data?.map((a) => (
          <Card key={a.id}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="h-9 w-9 rounded-md bg-accent-weak text-accent grid place-items-center">
                  <Landmark size={16} />
                </span>
                <div>
                  <div className="text-sm font-medium">{a.name}</div>
                  <div className="text-2xs text-muted tnum">{a.code}</div>
                </div>
              </div>
              {can("kassenbereich:manage") && (
                <button
                  onClick={() => setEdit(areas.data?.find((x) => x.id === a.id) ?? null)}
                  className="text-muted hover:text-ink transition-colors"
                  aria-label="Bearbeiten"
                >
                  <Pencil size={15} />
                </button>
              )}
            </div>
            <div className="mt-5 flex items-end justify-between">
              <Money value={a.balance} className="text-2xl font-semibold" />
              {!a.is_active && <Badge>inaktiv</Badge>}
            </div>
          </Card>
        ))}
      </div>

      {balances.data && (
        <Card className="mt-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xs uppercase tracking-[0.12em] text-muted">Summe Kassenbereiche</div>
              <Money value={total} className="mt-1 text-xl font-semibold block" />
            </div>
            <Badge tone={total < 0 ? "neg" : "accent"}>rechnerischer Bestand</Badge>
          </div>
        </Card>
      )}

      {/* Create */}
      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Neuer Kassenbereich"
        footer={
          <>
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="primary" loading={busy} onClick={submitCreate} disabled={!form.name || !form.code}>
              Anlegen
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Name">
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="z. B. Hausbereich" />
          </Field>
          <Field label="Code" hint="Kurzkennung, z. B. HAUS">
            <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
          </Field>
          <Field label="Beschreibung (optional)">
            <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </Field>
          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>

      {/* Edit */}
      <Dialog
        open={!!edit}
        onClose={() => setEdit(null)}
        title="Kassenbereich bearbeiten"
        footer={
          <>
            <Button variant="ghost" onClick={() => setEdit(null)}>
              Abbrechen
            </Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={() => edit && submitEdit({ name: edit.name, description: edit.description, is_active: edit.is_active })}
            >
              Speichern
            </Button>
          </>
        }
      >
        {edit && (
          <div className="space-y-4">
            <Field label="Name">
              <Input value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} />
            </Field>
            <Field label="Beschreibung">
              <Input
                value={edit.description ?? ""}
                onChange={(e) => setEdit({ ...edit, description: e.target.value })}
              />
            </Field>
            <label className="flex items-center gap-3 text-sm">
              <input
                type="checkbox"
                checked={edit.is_active}
                onChange={(e) => setEdit({ ...edit, is_active: e.target.checked })}
                className="h-4 w-4 rounded border-line accent-[rgb(var(--accent))]"
              />
              Aktiv (für neue Buchungen auswählbar)
            </label>
            {error && <Alert tone="neg">{error}</Alert>}
          </div>
        )}
      </Dialog>

      {/* Transfer */}
      <Dialog
        open={transferOpen}
        onClose={() => setTransferOpen(false)}
        title="Interne Umbuchung"
        footer={
          <>
            <Button variant="ghost" onClick={() => setTransferOpen(false)}>
              Abbrechen
            </Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={submitTransfer}
              disabled={!transfer.from || !transfer.to || transfer.from === transfer.to || !transfer.amount}
            >
              Umbuchen
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Verschiebt rechnerischen Bestand zwischen Kassenbereichen, ohne den tatsächlichen Kontostand zu
            verändern.
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Von">
              <select
                className="w-full h-10 rounded-md border border-line bg-surface px-3 text-sm"
                value={transfer.from}
                onChange={(e) => setTransfer({ ...transfer, from: e.target.value })}
              >
                <option value="">Bereich wählen …</option>
                {areas.data?.filter((a) => a.is_active).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Nach">
              <select
                className="w-full h-10 rounded-md border border-line bg-surface px-3 text-sm"
                value={transfer.to}
                onChange={(e) => setTransfer({ ...transfer, to: e.target.value })}
              >
                <option value="">Bereich wählen …</option>
                {areas.data?.filter((a) => a.is_active).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Betrag">
              <Input
                className="tnum"
                inputMode="decimal"
                placeholder="0,00"
                value={transfer.amount}
                onChange={(e) => setTransfer({ ...transfer, amount: e.target.value })}
              />
            </Field>
            <Field label="Notiz (optional)">
              <Input value={transfer.note} onChange={(e) => setTransfer({ ...transfer, note: e.target.value })} />
            </Field>
          </div>
          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>
    </>
  );
}
