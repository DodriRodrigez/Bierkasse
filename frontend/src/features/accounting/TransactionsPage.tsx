import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, Undo2 } from "lucide-react";
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
import { api } from "../../lib/api";
import { formatDate, formatDateTime } from "../../lib/format";
import { Kassenbereich, Semester, Tag, Transaction } from "../../lib/types";
import { useApi } from "../../lib/useApi";
import { useAuth } from "../../stores/auth";

function totalOf(t: Transaction): number {
  return t.lines.filter((l) => l.side === "SOLL").reduce((sum, l) => sum + l.amount, 0);
}

export default function TransactionsPage() {
  const can = useAuth((s) => s.can);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [areaId, setAreaId] = useState("");
  const [tagId, setTagId] = useState("");
  const [semesterId, setSemesterId] = useState("");
  const [detail, setDetail] = useState<Transaction | null>(null);
  const [storno, setStorno] = useState<Transaction | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => {
    const p = new URLSearchParams();
    if (search) p.set("search", search);
    if (category) p.set("category", category);
    if (areaId) p.set("kassenbereich_id", areaId);
    if (tagId) p.set("tag_id", tagId);
    if (semesterId) p.set("semester_id", semesterId);
    p.set("per_page", "100");
    return p.toString();
  }, [search, category, areaId, tagId, semesterId]);

  const txs = useApi<Transaction[]>(`/transactions?${query}`, [query]);
  const areas = useApi<Kassenbereich[]>("/kassenbereiche");
  const tags = useApi<Tag[]>("/tags");
  const semesters = useApi<Semester[]>("/semesters");

  const areaName = (id: string) => areas.data?.find((a) => a.id === id)?.name ?? "—";

  async function doStorno() {
    if (!storno) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/transactions/${storno.id}/stornate`, { reason: reason || "Korrektur" });
      setStorno(null);
      setReason("");
      txs.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Storno fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Buchhaltung"
        title="Buchungsjournal"
        subtitle="Alle Buchungen mit Kassenbereich, Tags und Status."
        actions={
          can("booking:create") && (
            <Link to="/buchungen/neu">
              <Button variant="primary" icon={<Plus size={16} />}>
                Neue Buchung
              </Button>
            </Link>
          )
        }
      />

      <Card className="mb-4" padded={false}>
        <div className="p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <Input
              placeholder="Beschreibung suchen …"
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={semesterId} onChange={(e) => setSemesterId(e.target.value)}>
            <option value="">Alle Semester</option>
            {semesters.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
          <Select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">Alle Kategorien</option>
            {["RB", "CB", "VS", "BL", "AB", "MISC"].map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
          <Select value={areaId} onChange={(e) => setAreaId(e.target.value)}>
            <option value="">Alle Kassenbereiche</option>
            {areas.data?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
          <Select value={tagId} onChange={(e) => setTagId(e.target.value)}>
            <option value="">Alle Tags</option>
            {tags.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        </div>
      </Card>

      <Card padded={false}>
        {txs.loading ? (
          <Spinner />
        ) : txs.data && txs.data.length > 0 ? (
          <>
            {/* Desktop table */}
            <div className="hidden md:block">
              <Table>
                <thead>
                  <tr>
                    <Th className="pl-6">Beleg</Th>
                    <Th>Datum</Th>
                    <Th>Beschreibung</Th>
                    <Th>Kategorie</Th>
                    <Th>Tags</Th>
                    <Th align="right">Betrag</Th>
                    <Th align="right" className="pr-6">Status</Th>
                  </tr>
                </thead>
                <tbody>
                  {txs.data.map((t) => (
                    <tr
                      key={t.id}
                      onClick={() => setDetail(t)}
                      className="hover:bg-bg/60 cursor-pointer"
                    >
                      <Td className="pl-6 tnum text-muted">#{t.sequential_number}</Td>
                      <Td className="tnum whitespace-nowrap">{formatDate(t.date)}</Td>
                      <Td className="max-w-sm truncate">{t.description}</Td>
                      <Td>
                        <Badge>{t.category}</Badge>
                      </Td>
                      <Td>
                        <div className="flex flex-wrap gap-1">
                          {t.tags.slice(0, 2).map((tg) => (
                            <Badge key={tg.id} tone="accent">
                              {tg.name}
                            </Badge>
                          ))}
                        </div>
                      </Td>
                      <Td align="right" className="font-medium">
                        <Money value={totalOf(t)} />
                      </Td>
                      <Td align="right" className="pr-6">
                        {t.is_storno ? (
                          <Badge tone="neg">Storno</Badge>
                        ) : t.is_locked ? (
                          <Badge tone="accent">festgeschrieben</Badge>
                        ) : (
                          <Badge tone="pos">offen</Badge>
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden divide-y divide-line">
              {txs.data.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setDetail(t)}
                  className="w-full text-left p-5 hover:bg-bg/60"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-2xs text-muted tnum">
                        #{t.sequential_number} · {formatDate(t.date)}
                      </div>
                      <div className="mt-1 text-sm font-medium truncate">{t.description}</div>
                    </div>
                    <Money value={totalOf(t)} className="font-semibold shrink-0" />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    <Badge>{t.category}</Badge>
                    {t.tags.map((tg) => (
                      <Badge key={tg.id} tone="accent">
                        {tg.name}
                      </Badge>
                    ))}
                    {t.is_storno && <Badge tone="neg">Storno</Badge>}
                  </div>
                </button>
              ))}
            </div>
          </>
        ) : (
          <EmptyState
            icon={<Search size={28} />}
            title="Keine Buchungen gefunden"
            description="Passe die Filter an oder lege eine neue Buchung an."
          />
        )}
      </Card>

      {/* Detail dialog */}
      <Dialog
        open={!!detail}
        onClose={() => setDetail(null)}
        title={detail ? `Buchung #${detail.sequential_number}` : ""}
        width="max-w-2xl"
        footer={
          detail && !detail.is_storno && can("booking:storno") ? (
            <Button variant="danger" icon={<Undo2 size={15} />} onClick={() => { setStorno(detail); setDetail(null); }}>
              Stornieren
            </Button>
          ) : null
        }
      >
        {detail && (
          <div className="space-y-5">
            <div className="grid sm:grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-2xs uppercase tracking-[0.12em] text-muted">Datum</div>
                <div className="mt-1 tnum">{formatDate(detail.date)}</div>
              </div>
              <div>
                <div className="text-2xs uppercase tracking-[0.12em] text-muted">Kategorie</div>
                <div className="mt-1">
                  <Badge>{detail.category}</Badge>
                </div>
              </div>
              <div className="sm:col-span-2">
                <div className="text-2xs uppercase tracking-[0.12em] text-muted">Beschreibung</div>
                <div className="mt-1">{detail.description}</div>
              </div>
              <div className="sm:col-span-2">
                <div className="text-2xs uppercase tracking-[0.12em] text-muted">Erstellt</div>
                <div className="mt-1 tnum">{formatDateTime(detail.created_at)}</div>
              </div>
            </div>

            {detail.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {detail.tags.map((t) => (
                  <Badge key={t.id} tone="accent">
                    {t.name}
                  </Badge>
                ))}
              </div>
            )}

            <div className="rounded-lg border border-line overflow-hidden">
              <Table>
                <thead>
                  <tr>
                    <Th>Seite</Th>
                    <Th>Kassenbereich</Th>
                    <Th>Buchungstext</Th>
                    <Th align="right">Betrag</Th>
                  </tr>
                </thead>
                <tbody>
                  {detail.lines.map((l) => (
                    <tr key={l.id}>
                      <Td>
                        <Badge tone={l.side === "SOLL" ? "accent" : "neutral"}>{l.side}</Badge>
                      </Td>
                      <Td>{areaName(l.kassenbereich_id)}</Td>
                      <Td className="text-muted">{l.description ?? "—"}</Td>
                      <Td align="right" className="tnum font-medium">
                        <Money value={l.amount} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          </div>
        )}
      </Dialog>

      {/* Storno dialog */}
      <Dialog
        open={!!storno}
        onClose={() => setStorno(null)}
        title="Buchung stornieren"
        footer={
          <>
            <Button variant="ghost" onClick={() => setStorno(null)}>
              Abbrechen
            </Button>
            <Button variant="primary" loading={busy} onClick={doStorno}>
              Storno verbuchen
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Es wird eine Gegenbuchung erzeugt. Kassenbereich und Tags werden übernommen.
          </p>
          <Field label="Begründung">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="z. B. fehlerhafte Zählung" />
          </Field>
          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>
    </>
  );
}
