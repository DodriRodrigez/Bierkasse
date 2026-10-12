import { useState } from "react";
import { Plus, Receipt } from "lucide-react";
import {
  Alert,
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
import { Beverage } from "../../lib/types";
import { useApi } from "../../lib/useApi";

export default function BeveragesPage() {
  const beverages = useApi<Beverage[]>("/beverages");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    name: "",
    ring_color: "red",
    ring_price: "0.70",
    bottles_per_crate: "20",
    category: "Bier",
    deposit_per_bottle: "0.08",
  });

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/beverages", {
        name: form.name,
        ring_color: form.ring_color,
        ring_price: Number(form.ring_price.replace(",", ".")),
        bottles_per_crate: Number(form.bottles_per_crate) || 20,
        category: form.category,
        deposit_per_bottle: Number(form.deposit_per_bottle.replace(",", ".")),
      });
      setOpen(false);
      setForm({ ...form, name: "" });
      beverages.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Speichern fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Betrieb"
        title="Getränke"
        subtitle="Getränkekatalog mit Ringfarbe, Verkaufspreis und Pfand."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setOpen(true)}>
            Getränk
          </Button>
        }
      />

      <Card padded={false}>
        {beverages.loading ? (
          <Spinner />
        ) : beverages.data && beverages.data.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th className="pl-6">Name</Th>
                <Th>Kategorie</Th>
                <Th align="center">Ring</Th>
                <Th align="right">Preis</Th>
                <Th align="right">Kasten</Th>
                <Th align="right" className="pr-6">Pfand/Flasche</Th>
              </tr>
            </thead>
            <tbody>
              {beverages.data.map((b) => (
                <tr key={b.id} className="hover:bg-bg/60">
                  <Td className="pl-6">{b.name}</Td>
                  <Td className="text-muted">{b.category}</Td>
                  <Td align="center">
                    <span className="inline-flex items-center gap-2">
                      <span
                        className={
                          b.ring_color === "red" ? "h-2.5 w-2.5 rounded-full bg-neg/70" : "h-2.5 w-2.5 rounded-full bg-warn/70"
                        }
                      />
                      <span className="text-muted">{b.ring_color === "red" ? "rot" : "gelb"}</span>
                    </span>
                  </Td>
                  <Td align="right" className="tnum">
                    <Money value={b.ring_price} />
                  </Td>
                  <Td align="right" className="tnum text-muted">{b.bottles_per_crate}</Td>
                  <Td align="right" className="pr-6 tnum text-muted">
                    <Money value={b.deposit_per_bottle} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState icon={<Receipt size={28} />} title="Keine Getränke" />
        )}
      </Card>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Neues Getränk"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="primary" loading={busy} onClick={submit} disabled={!form.name}>
              Anlegen
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Name">
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Ringfarbe">
              <Select value={form.ring_color} onChange={(e) => setForm({ ...form, ring_color: e.target.value })}>
                <option value="red">rot (0,70 €)</option>
                <option value="yellow">gelb (1,00 €)</option>
              </Select>
            </Field>
            <Field label="Verkaufspreis">
              <Input className="tnum" value={form.ring_price} onChange={(e) => setForm({ ...form, ring_price: e.target.value })} />
            </Field>
            <Field label="Kategorie">
              <Input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
            </Field>
            <Field label="Flaschen/Kasten">
              <Input className="tnum" value={form.bottles_per_crate} onChange={(e) => setForm({ ...form, bottles_per_crate: e.target.value })} />
            </Field>
            <Field label="Pfand/Flasche">
              <Input className="tnum" value={form.deposit_per_bottle} onChange={(e) => setForm({ ...form, deposit_per_bottle: e.target.value })} />
            </Field>
          </div>
          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>
    </>
  );
}
