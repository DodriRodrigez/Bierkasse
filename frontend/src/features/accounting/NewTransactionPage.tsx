import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Check, Plus, TriangleAlert, X } from "lucide-react";
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
  Select,
} from "../../design/primitives";
import { api, ApiError } from "../../lib/api";
import { todayISO } from "../../lib/format";
import { AccountBalance, Kassenbereich, Semester, Tag } from "../../lib/types";
import { useApi } from "../../lib/useApi";

type Line = {
  key: number;
  account_id: string;
  side: "SOLL" | "HABEN";
  amount: string;
  kassenbereich_id: string;
  description: string;
};

type PreviewArea = { kassenbereich_id: string; name: string; before: number; after: number; overdrawn: boolean };
type Preview = { areas: PreviewArea[]; warnings: string[] };

let keySeq = 1;
const newLine = (area: string): Line => ({
  key: keySeq++,
  account_id: "",
  side: "SOLL",
  amount: "",
  kassenbereich_id: area,
  description: "",
});

export default function NewTransactionPage() {
  const navigate = useNavigate();
  const accounts = useApi<AccountBalance[]>("/accounts");
  const areas = useApi<Kassenbereich[]>("/kassenbereiche");
  const tags = useApi<Tag[]>("/tags");
  const semesters = useApi<Semester>("/semesters/current");

  const [date, setDate] = useState(todayISO());
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("MISC");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [lines, setLines] = useState<Line[]>([newLine(""), newLine("")]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const defaultArea = areas.data?.find((a) => a.is_active)?.id ?? "";

  useEffect(() => {
    if (defaultArea) {
      setLines((ls) => ls.map((l) => (l.kassenbereich_id ? l : { ...l, kassenbereich_id: defaultArea })));
    }
  }, [defaultArea]);

  const totals = useMemo(() => {
    let soll = 0;
    let haben = 0;
    for (const l of lines) {
      const n = Number(l.amount.replace(",", ".")) || 0;
      if (l.side === "SOLL") soll += n;
      else haben += n;
    }
    return { soll, haben, balanced: Math.abs(soll - haben) < 0.0001 && soll > 0 };
  }, [lines]);

  const payloadLines = useMemo(
    () =>
      lines
        .filter((l) => l.account_id && l.kassenbereich_id && Number(l.amount.replace(",", ".")) > 0)
        .map((l) => ({
          account_id: l.account_id,
          side: l.side,
          amount: Number(l.amount.replace(",", ".")),
          kassenbereich_id: l.kassenbereich_id,
          description: l.description || undefined,
        })),
    [lines],
  );

  useEffect(() => {
    if (payloadLines.length < 2) {
      setPreview(null);
      return;
    }
    const handle = setTimeout(() => {
      api
        .post<Preview>("/transactions/preview", { lines: payloadLines })
        .then(setPreview)
        .catch(() => setPreview(null));
    }, 350);
    return () => clearTimeout(handle);
  }, [payloadLines]);

  function updateLine(key: number, patch: Partial<Line>) {
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  }

  function addTag() {
    const value = tagInput.trim();
    if (value && !selectedTags.includes(value)) setSelectedTags((t) => [...t, value]);
    setTagInput("");
  }

  async function submit() {
    setError(null);
    if (!totals.balanced) {
      setError("Buchung ist nicht ausgeglichen: Summe SOLL muss gleich Summe HABEN sein.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/transactions", {
        date,
        description: description || "Buchung",
        category,
        lines: payloadLines,
        tags: selectedTags,
        semester_id: semesters.data?.id,
      });
      navigate("/buchungen");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Buchung fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Buchhaltung"
        title="Neue Buchung"
        subtitle="Doppelte Buchführung mit verpflichtendem Kassenbereich."
        actions={
          <Button variant="ghost" icon={<ArrowLeft size={16} />} onClick={() => navigate("/buchungen")}>
            Zurück
          </Button>
        }
      />

      <div className="grid lg:grid-cols-[minmax(0,1fr)_360px] gap-4 items-start">
        <div className="space-y-4">
          <Card>
            <CardHeader title="Kopfdaten" />
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Datum">
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              </Field>
              <Field label="Kategorie">
                <Select value={category} onChange={(e) => setCategory(e.target.value)}>
                  {["RB", "CB", "VS", "BL", "AB", "MISC"].map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Beschreibung" className="sm:col-span-2">
                <Input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Buchungstext"
                />
              </Field>
            </div>

            <div className="mt-5">
              <div className="text-sm font-medium mb-1.5">Tags</div>
              <div className="flex flex-wrap items-center gap-2">
                {selectedTags.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center gap-1.5 rounded-full bg-accent-weak text-accent px-2.5 py-1 text-2xs font-medium"
                  >
                    {t}
                    <button onClick={() => setSelectedTags((s) => s.filter((x) => x !== t))} aria-label="Tag entfernen">
                      <X size={12} />
                    </button>
                  </span>
                ))}
                <input
                  list="tag-options"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addTag();
                    }
                  }}
                  placeholder="Tag hinzufügen (Enter) …"
                  className="h-9 rounded-md border border-line bg-surface px-3 text-sm w-56 outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                />
                <datalist id="tag-options">
                  {tags.data?.map((t) => (
                    <option key={t.id} value={t.name} />
                  ))}
                </datalist>
              </div>
              <p className="mt-2 text-xs text-muted">
                Tags eignen sich z. B. zur Zuordnung einer CC-Kassen-Buchung zu einer Veranstaltung.
              </p>
            </div>
          </Card>

          <Card padded={false}>
            <div className="p-6 pb-4">
              <CardHeader
                title="Buchungszeilen"
                subtitle="Mindestens zwei Zeilen; jede Zeile braucht einen Kassenbereich."
                action={
                  <Button size="sm" variant="secondary" icon={<Plus size={15} />} onClick={() => setLines((ls) => [...ls, newLine(defaultArea)])}>
                    Zeile
                  </Button>
                }
              />
            </div>
            <div className="divide-y divide-line">
              {lines.map((l) => (
                <div key={l.key} className="p-6 grid gap-3 lg:grid-cols-12">
                  <div className="lg:col-span-4">
                    <label className="text-2xs uppercase tracking-[0.12em] text-muted">Konto</label>
                    <Select
                      className="mt-1"
                      value={l.account_id}
                      onChange={(e) => updateLine(l.key, { account_id: e.target.value })}
                    >
                      <option value="">Konto wählen …</option>
                      {accounts.data?.map((a) => (
                        <option key={a.account.id} value={a.account.id}>
                          {a.account.name}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div className="lg:col-span-2">
                    <label className="text-2xs uppercase tracking-[0.12em] text-muted">Seite</label>
                    <Select
                      className="mt-1"
                      value={l.side}
                      onChange={(e) => updateLine(l.key, { side: e.target.value as "SOLL" | "HABEN" })}
                    >
                      <option value="SOLL">SOLL</option>
                      <option value="HABEN">HABEN</option>
                    </Select>
                  </div>
                  <div className="lg:col-span-2">
                    <label className="text-2xs uppercase tracking-[0.12em] text-muted">Betrag</label>
                    <Input
                      className="mt-1 tnum"
                      inputMode="decimal"
                      placeholder="0,00"
                      value={l.amount}
                      onChange={(e) => updateLine(l.key, { amount: e.target.value })}
                    />
                  </div>
                  <div className="lg:col-span-3">
                    <label className="text-2xs uppercase tracking-[0.12em] text-muted">Kassenbereich</label>
                    <Select
                      className="mt-1"
                      value={l.kassenbereich_id}
                      onChange={(e) => updateLine(l.key, { kassenbereich_id: e.target.value })}
                    >
                      <option value="">Bereich wählen …</option>
                      {areas.data?.filter((a) => a.is_active).map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div className="lg:col-span-1 flex items-end justify-end">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setLines((ls) => (ls.length > 2 ? ls.filter((x) => x.key !== l.key) : ls))}
                      aria-label="Zeile entfernen"
                    >
                      <X size={16} />
                    </Button>
                  </div>
                  <div className="lg:col-span-12">
                    <Input
                      placeholder="Buchungstext dieser Zeile (optional)"
                      value={l.description}
                      onChange={(e) => updateLine(l.key, { description: e.target.value })}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="px-6 py-5 border-t border-line flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted">SOLL</span>
                <Money value={totals.soll} className="font-medium" />
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted">HABEN</span>
                <Money value={totals.haben} className="font-medium" />
              </div>
              <Badge tone={totals.balanced ? "pos" : "warn"}>
                <Check size={12} /> {totals.balanced ? "ausgeglichen" : "nicht ausgeglichen"}
              </Badge>
            </div>
          </Card>
        </div>

        {/* Preview */}
        <div className="lg:sticky lg:top-24 space-y-4">
          <Card>
            <CardHeader title="Buchungsvorschau" subtitle="Bestand je Kassenbereich vor und nach der Buchung" />
            {preview ? (
              <div className="space-y-4">
                {preview.areas.map((a) => (
                  <div key={a.kassenbereich_id}>
                    <div className="flex items-center justify-between text-sm mb-1.5">
                      <span className="text-ink">{a.name}</span>
                      <span className="tnum">
                        <Money value={a.before} /> →
                        <Money value={a.after} className="ml-2 font-medium" />
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-bg overflow-hidden">
                      <div
                        className={a.overdrawn ? "h-full bg-neg/60" : "h-full bg-accent/70"}
                        style={{
                          width: `${Math.min(100, (Math.abs(a.after) / Math.max(1, ...preview.areas.map((x) => Math.abs(x.before)), Math.abs(a.after))) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
                {preview.warnings.map((w, i) => (
                  <Alert key={i} tone="warn" icon={<TriangleAlert size={16} />}>
                    {w}
                  </Alert>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted">
                Sobald Buchungszeilen vollständig sind, erscheint hier die Vorschau mit Beständen und
                Überziehungswarnung.
              </p>
            )}
          </Card>

          <Card>
            {error && (
              <div className="mb-4">
                <Alert tone="neg">{error}</Alert>
              </div>
            )}
            <Button
              variant="primary"
              className="w-full"
              loading={busy}
              disabled={!totals.balanced}
              onClick={submit}
            >
              Buchung speichern
            </Button>
            <p className="mt-3 text-xs text-muted text-center">
              Buchungen sind unveränderlich; Korrekturen erfolgen per Storno.
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}
