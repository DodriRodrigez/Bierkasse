import { useState } from "react";
import { ClipboardList, Plus } from "lucide-react";
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
  Spinner,
  Table,
  Td,
  Th,
} from "../../design/primitives";
import { api, ApiError } from "../../lib/api";
import { formatDate, todayISO } from "../../lib/format";
import { Beverage, Inventory } from "../../lib/types";
import { useApi } from "../../lib/useApi";

type ComparisonRow = {
  beverage_id: string;
  name: string;
  delivered: number;
  counted: number;
  difference: number;
  deviation_percent: number;
};

export default function InventoryPage() {
  const inventories = useApi<Inventory[]>("/inventories");
  const beverages = useApi<Beverage[]>("/beverages");

  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(todayISO());
  const [notes, setNotes] = useState("");
  const [counts, setCounts] = useState<Record<string, { crates: string; singles: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [comparison, setComparison] = useState<{ rows: ComparisonRow[] } | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    const items = Object.entries(counts)
      .map(([beverage_id, c]) => ({
        beverage_id,
        crates: Number(c.crates) || 0,
        single_bottles: Number(c.singles) || 0,
      }))
      .filter((i) => i.crates > 0 || i.single_bottles > 0);
    if (items.length === 0) {
      setError("Mindestens ein Getränk erfassen.");
      setBusy(false);
      return;
    }
    try {
      await api.post("/inventories", { date, notes: notes || undefined, items });
      setOpen(false);
      setCounts({});
      inventories.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Speichern fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function showComparison(id: string) {
    try {
      const data = await api.get<{ rows: ComparisonRow[] }>(`/inventories/${id}/comparison`);
      setComparison(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Vergleich fehlgeschlagen.");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Betrieb"
        title="Inventur"
        subtitle="Bestand erfassen und Soll-Ist-Abweichung je Getränk prüfen."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setOpen(true)}>
            Neue Inventur
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Alert tone="neg">{error}</Alert>
        </div>
      )}

      <Card padded={false}>
        {inventories.loading ? (
          <Spinner />
        ) : inventories.data && inventories.data.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th className="pl-6">Datum</Th>
                <Th align="center">Positionen</Th>
                <Th>Notiz</Th>
                <Th align="right" className="pr-6">Aktion</Th>
              </tr>
            </thead>
            <tbody>
              {inventories.data.map((inv) => (
                <tr key={inv.id} className="hover:bg-bg/60">
                  <Td className="pl-6 tnum">{formatDate(inv.date)}</Td>
                  <Td align="center" className="tnum">{inv.items.length}</Td>
                  <Td className="text-muted">{inv.notes ?? "—"}</Td>
                  <Td align="right" className="pr-6">
                    <Button size="sm" variant="secondary" onClick={() => showComparison(inv.id)}>
                      Soll-Ist
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState icon={<ClipboardList size={28} />} title="Noch keine Inventuren" />
        )}
      </Card>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Neue Inventur"
        width="max-w-2xl"
        footer={
          <>
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
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Datum">
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </Field>
            <Field label="Notiz (optional)">
              <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
            </Field>
          </div>
          <div className="rounded-lg border border-line overflow-hidden">
            <Table>
              <thead>
                <tr>
                  <Th>Getränk</Th>
                  <Th align="right" className="w-28">Kästen</Th>
                  <Th align="right" className="w-32 pr-4">Einzelflaschen</Th>
                </tr>
              </thead>
              <tbody>
                {beverages.data?.map((b) => {
                  const c = counts[b.id] ?? { crates: "", singles: "" };
                  return (
                    <tr key={b.id}>
                      <Td>{b.name}</Td>
                      <Td align="right">
                        <Input
                          className="tnum h-9 text-right"
                          inputMode="numeric"
                          value={c.crates}
                          onChange={(e) => setCounts({ ...counts, [b.id]: { ...c, crates: e.target.value.replace(/\D/g, "") } })}
                        />
                      </Td>
                      <Td align="right" className="pr-4">
                        <Input
                          className="tnum h-9 text-right"
                          inputMode="numeric"
                          value={c.singles}
                          onChange={(e) => setCounts({ ...counts, [b.id]: { ...c, singles: e.target.value.replace(/\D/g, "") } })}
                        />
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

      <Dialog open={!!comparison} onClose={() => setComparison(null)} title="Soll-Ist-Vergleich" width="max-w-2xl">
        {comparison && (
          <Table>
            <thead>
              <tr>
                <Th>Getränk</Th>
                <Th align="right">Geliefert</Th>
                <Th align="right">Gezählt</Th>
                <Th align="right">Differenz</Th>
                <Th align="right">Abweichung</Th>
              </tr>
            </thead>
            <tbody>
              {comparison.rows.map((r) => (
                <tr key={r.beverage_id}>
                  <Td>{r.name}</Td>
                  <Td align="right" className="tnum">{r.delivered}</Td>
                  <Td align="right" className="tnum">{r.counted}</Td>
                  <Td align="right" className="tnum">{r.difference}</Td>
                  <Td align="right">
                    <Badge tone={Math.abs(r.deviation_percent) > 5 ? "warn" : "neutral"}>
                      {r.deviation_percent.toFixed(1)} %
                    </Badge>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Dialog>
    </>
  );
}
