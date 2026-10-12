import { useMemo, useState } from "react";
import { CalendarDays, Check, Plus, Send } from "lucide-react";
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
import { EventItem, Kassenbereich, Tag } from "../../lib/types";
import { useApi } from "../../lib/useApi";

type DirectoryEntry = { id: string; name: string; membership_status: string };
type Prices = { red: number; yellow: number };

export default function EventsPage() {
  const events = useApi<EventItem[]>("/events");
  const areas = useApi<Kassenbereich[]>("/kassenbereiche");
  const directory = useApi<DirectoryEntry[]>("/users/directory");
  const prices = useApi<Prices>("/beverages/ring-prices");
  const allTags = useApi<Tag[]>("/tags");

  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    name: "",
    date: todayISO(),
    type: "public",
    payer_type: "cc_cash",
    payer_user_id: "",
    red: "",
    yellow: "",
    donation: "",
    kassenbereich_id: "",
    tags: [] as string[],
  });

  const red = prices.data?.red ?? 0.7;
  const yellow = prices.data?.yellow ?? 1.0;
  const gross = useMemo(
    () => (Number(form.red) || 0) * red + (Number(form.yellow) || 0) * yellow,
    [form.red, form.yellow, red, yellow],
  );
  const net = Math.max(gross - (Number(form.donation.replace(",", ".")) || 0), 0);

  function openNew() {
    setForm({
      name: "",
      date: todayISO(),
      type: "public",
      payer_type: "cc_cash",
      payer_user_id: "",
      red: "",
      yellow: "",
      donation: "",
      kassenbereich_id: areas.data?.find((a) => a.is_active)?.id ?? "",
      tags: [],
    });
    setOpen(true);
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/events", {
        name: form.name || "Veranstaltung",
        date: form.date,
        type: form.type,
        payer_type: form.payer_type,
        payer_user_id: form.payer_type === "member" ? form.payer_user_id : undefined,
        red_glasses: Number(form.red) || 0,
        yellow_glasses: Number(form.yellow) || 0,
        donation: Number(form.donation.replace(",", ".")) || 0,
        kassenbereich_id: form.kassenbereich_id,
        tags: form.tags,
        post: true,
      });
      setOpen(false);
      events.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verbuchen fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function post(id: string) {
    try {
      await api.post(`/events/${id}/post`);
      events.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verbuchen fehlgeschlagen.");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Betrieb"
        title="Veranstaltungen"
        subtitle="Ringgläser zählen, Ausgaben dem richtigen Kassenbereich zuordnen und mit Tags markieren."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={openNew}>
            Neue Veranstaltung
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Alert tone="neg">{error}</Alert>
        </div>
      )}

      <Card padded={false}>
        {events.loading ? (
          <Spinner />
        ) : events.data && events.data.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th className="pl-6">Datum</Th>
                <Th>Name</Th>
                <Th>Zahler</Th>
                <Th>Tags</Th>
                <Th align="center">Status</Th>
                <Th align="right" className="pr-6">Aktion</Th>
              </tr>
            </thead>
            <tbody>
              {events.data.map((e) => (
                <tr key={e.id} className="hover:bg-bg/60">
                  <Td className="pl-6 tnum whitespace-nowrap">{formatDate(e.date)}</Td>
                  <Td>{e.name}</Td>
                  <Td>{e.payer_type === "cc_cash" ? "CC-Kasse" : "Mitglied"}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      {e.tags.map((t) => (
                        <Badge key={t.id} tone="accent">
                          {t.name}
                        </Badge>
                      ))}
                    </div>
                  </Td>
                  <Td align="center">
                    {e.is_posted ? (
                      <Badge tone="pos">
                        <Check size={12} /> verbucht
                      </Badge>
                    ) : (
                      <Badge tone="warn">offen</Badge>
                    )}
                  </Td>
                  <Td align="right" className="pr-6">
                    {!e.is_posted && (
                      <Button size="sm" variant="secondary" icon={<Send size={14} />} onClick={() => post(e.id)}>
                        Verbuchen
                      </Button>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState icon={<CalendarDays size={28} />} title="Noch keine Veranstaltungen" />
        )}
      </Card>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Neue Veranstaltung"
        width="max-w-2xl"
        footer={
          <>
            <div className="mr-auto text-sm">
              Betrag: <Money value={net} className="font-semibold" />
            </div>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="primary" loading={busy} onClick={submit}>
              Verbuchen
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Name" className="sm:col-span-2">
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="z. B. Stiftungsfest" />
            </Field>
            <Field label="Datum">
              <Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            </Field>
            <Field label="Kassenbereich">
              <Select value={form.kassenbereich_id} onChange={(e) => setForm({ ...form, kassenbereich_id: e.target.value })}>
                {areas.data?.filter((a) => a.is_active).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Typ">
              <Select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option value="public">öffentlich</option>
                <option value="private">privat</option>
              </Select>
            </Field>
            <Field label="Zahler">
              <Select value={form.payer_type} onChange={(e) => setForm({ ...form, payer_type: e.target.value })}>
                <option value="cc_cash">CC-Kasse</option>
                <option value="member">Mitglied</option>
              </Select>
            </Field>
            {form.payer_type === "member" && (
              <Field label="Zahler-Mitglied" className="sm:col-span-2">
                <Select value={form.payer_user_id} onChange={(e) => setForm({ ...form, payer_user_id: e.target.value })}>
                  <option value="">Mitglied wählen …</option>
                  {directory.data?.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            <Field label="Rote Gläser">
              <Input className="tnum" inputMode="numeric" value={form.red} onChange={(e) => setForm({ ...form, red: e.target.value.replace(/\D/g, "") })} />
            </Field>
            <Field label="Gelbe Gläser">
              <Input className="tnum" inputMode="numeric" value={form.yellow} onChange={(e) => setForm({ ...form, yellow: e.target.value.replace(/\D/g, "") })} />
            </Field>
            <Field label="Spende / Abzug (optional)">
              <Input className="tnum" inputMode="decimal" placeholder="0,00" value={form.donation} onChange={(e) => setForm({ ...form, donation: e.target.value })} />
            </Field>
          </div>

          <div>
            <div className="text-sm font-medium mb-1.5">Tags</div>
            <div className="flex flex-wrap gap-2">
              {allTags.data?.map((t) => {
                const active = form.tags.includes(t.name);
                return (
                  <button
                    key={t.id}
                    onClick={() =>
                      setForm({
                        ...form,
                        tags: active ? form.tags.filter((x) => x !== t.name) : [...form.tags, t.name],
                      })
                    }
                    className={
                      active
                        ? "rounded-full bg-accent-weak text-accent px-3 py-1 text-2xs font-medium"
                        : "rounded-full border border-line text-muted px-3 py-1 text-2xs font-medium"
                    }
                  >
                    {t.name}
                  </button>
                );
              })}
            </div>
          </div>

          {error && <Alert tone="neg">{error}</Alert>}
        </div>
      </Dialog>
    </>
  );
}
