import { Link } from "react-router-dom";
import {
  ArrowRight,
  Banknote,
  Landmark,
  Receipt,
  Scale,
  TriangleAlert,
  TrendingUp,
} from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Money,
  PageHeader,
  Spinner,
  StatCard,
  Table,
  Td,
  Th,
} from "../../design/primitives";
import { formatDate } from "../../lib/format";
import { MemberDashboard } from "../../lib/types";
import { DashboardSummary } from "../../lib/types";
import { useApi } from "../../lib/useApi";
import { useAuth } from "../../stores/auth";

function AdminDashboard({ data }: { data: DashboardSummary }) {
  const eq = data.control_equation;
  const maxArea = Math.max(1, ...data.kassenbereiche.items.map((i) => Math.abs(i.balance)));
  const maxLiq = Math.max(1, ...data.liquidity.items.map((i) => Math.abs(i.balance)));

  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Gesamtliquidität" value={<Money value={data.liquidity.total} />} icon={<Banknote size={16} />} />
        <StatCard
          label="Σ Kassenbereiche"
          value={<Money value={data.kassenbereiche.total} />}
          icon={<Landmark size={16} />}
          tone="accent"
        />
        <StatCard label="Forderungen" value={<Money value={data.forderungen} />} icon={<Receipt size={16} />} />
        <StatCard
          label="Verbindlichkeiten"
          value={<Money value={data.verbindlichkeiten} />}
          icon={<TrendingUp size={16} />}
        />
      </div>

      {data.overdrawn.length > 0 && (
        <div className="mt-4">
          <Alert tone="warn" title="Überzogene Kassenbereiche" icon={<TriangleAlert size={18} />}>
            <div className="mt-1 flex flex-wrap gap-x-6 gap-y-1">
              {data.overdrawn.map((o) => (
                <span key={o.id}>
                  {o.name}: <Money value={o.balance} className="font-medium" />
                </span>
              ))}
            </div>
          </Alert>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-4 mt-4">
        <Card>
          <CardHeader
            title="Tatsächliche Liquidität"
            subtitle="Real vorhandene Bestände der Zahlungskonten"
          />
          <div className="space-y-4">
            {data.liquidity.items.map((item) => (
              <div key={item.id}>
                <div className="flex items-center justify-between text-sm mb-1.5">
                  <span className="text-ink">{item.name}</span>
                  <Money value={item.balance} className="font-medium" />
                </div>
                <div className="h-1.5 rounded-full bg-bg overflow-hidden">
                  <div
                    className="h-full rounded-full bg-accent/70"
                    style={{ width: `${(Math.abs(item.balance) / maxLiq) * 100}%` }}
                  />
                </div>
              </div>
            ))}
            {data.liquidity.items.length === 0 && <p className="text-sm text-muted">Keine Konten.</p>}
          </div>
          <div className="mt-6 pt-4 border-t border-line flex items-center justify-between">
            <span className="text-2xs uppercase tracking-[0.12em] text-muted">Gesamt</span>
            <Money value={data.liquidity.total} className="text-lg font-semibold" />
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Rechnerische Bestände"
            subtitle="Interne Ansprüche nach Kassenbereich"
          />
          <div className="space-y-4">
            {data.kassenbereiche.items.map((item) => (
              <div key={item.id}>
                <div className="flex items-center justify-between text-sm mb-1.5">
                  <span className="flex items-center gap-2 text-ink">
                    {item.name}
                    {!item.is_active && <Badge>inaktiv</Badge>}
                  </span>
                  <Money value={item.balance} className="font-medium" />
                </div>
                <div className="h-1.5 rounded-full bg-bg overflow-hidden">
                  <div
                    className={item.balance < 0 ? "h-full rounded-full bg-neg/60" : "h-full rounded-full bg-accent/70"}
                    style={{ width: `${(Math.abs(item.balance) / maxArea) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 pt-4 border-t border-line flex items-center justify-between">
            <span className="text-2xs uppercase tracking-[0.12em] text-muted">Summe</span>
            <Money value={data.kassenbereiche.total} className="text-lg font-semibold" />
          </div>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Kontrollgleichung"
          subtitle="Σ Kassenbereiche = Liquidität + Forderungen − Verbindlichkeiten"
          action={
            <Badge tone={eq.balanced ? "pos" : "neg"}>
              <Scale size={12} /> {eq.balanced ? "ausgeglichen" : "Abweichung"}
            </Badge>
          }
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-lg border border-line p-4">
            <div className="text-2xs uppercase tracking-[0.12em] text-muted">Kassenbereiche</div>
            <Money value={eq.sum_kassenbereiche} className="mt-2 block text-lg font-semibold" />
          </div>
          <div className="rounded-lg border border-line p-4">
            <div className="text-2xs uppercase tracking-[0.12em] text-muted">+ Liquidität</div>
            <Money value={eq.liquiditaet} className="mt-2 block text-lg font-semibold" />
          </div>
          <div className="rounded-lg border border-line p-4">
            <div className="text-2xs uppercase tracking-[0.12em] text-muted">
              + Forderungen − Verbindlichkeiten
            </div>
            <Money
              value={eq.forderungen - eq.verbindlichkeiten}
              className="mt-2 block text-lg font-semibold"
            />
          </div>
          <div className="rounded-lg border border-line p-4 bg-accent-weak/40">
            <div className="text-2xs uppercase tracking-[0.12em] text-muted">Differenz</div>
            <Money value={eq.difference} className="mt-2 block text-lg font-semibold" />
          </div>
        </div>
      </Card>

      <Card className="mt-4" padded={false}>
        <div className="px-6 pt-6">
          <CardHeader
            title="Letzte Buchungen"
            action={
              <Link to="/buchungen">
                <Button variant="ghost" size="sm" icon={<ArrowRight size={15} />}>
                  Alle
                </Button>
              </Link>
            }
          />
        </div>
        <Table>
          <thead>
            <tr>
              <Th className="pl-6">Beleg</Th>
              <Th>Datum</Th>
              <Th>Beschreibung</Th>
              <Th>Kategorie</Th>
              <Th align="right" className="pr-6">
                Status
              </Th>
            </tr>
          </thead>
          <tbody>
            {data.recent.map((t) => (
              <tr key={t.id} className="hover:bg-bg/60">
                <Td className="pl-6 tnum text-muted">#{t.sequential_number}</Td>
                <Td className="tnum whitespace-nowrap">{formatDate(t.date)}</Td>
                <Td className="max-w-md truncate">{t.description}</Td>
                <Td>
                  <Badge>{t.category}</Badge>
                </Td>
                <Td align="right" className="pr-6">
                  {t.is_storno ? <Badge tone="neg">Storno</Badge> : <Badge tone="pos">gebucht</Badge>}
                </Td>
              </tr>
            ))}
            {data.recent.length === 0 && (
              <tr>
                <Td className="pl-6 text-muted" >Noch keine Buchungen.</Td>
                <Td /><Td /><Td /><Td />
              </tr>
            )}
          </tbody>
        </Table>
      </Card>
    </>
  );
}

function MemberView({ data }: { data: MemberDashboard }) {
  return (
    <>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          label="Mein Saldo"
          value={<Money value={data.total_balance} showSign />}
          tone={data.total_balance < 0 ? "neg" : "pos"}
          hint={data.total_balance < 0 ? "Offener Ausstand" : "Guthaben"}
        />
        {data.by_kassenbereich.map((a) => (
          <StatCard key={a.kassenbereich_id} label={a.name} value={<Money value={a.balance} showSign />} />
        ))}
      </div>

      <Card className="mt-4" padded={false}>
        <div className="px-6 pt-6">
          <CardHeader title="Meine letzten Buchungen" />
        </div>
        <Table>
          <thead>
            <tr>
              <Th className="pl-6">Beleg</Th>
              <Th>Datum</Th>
              <Th>Beschreibung</Th>
              <Th align="right" className="pr-6">Betrag</Th>
            </tr>
          </thead>
          <tbody>
            {data.recent_transactions.map((t) => (
              <tr key={t.id} className="hover:bg-bg/60">
                <Td className="pl-6 tnum text-muted">#{t.sequential_number}</Td>
                <Td className="tnum whitespace-nowrap">{formatDate(t.date)}</Td>
                <Td className="max-w-md truncate">{t.description}</Td>
                <Td align="right" className="pr-6">
                  <Money value={t.side === "HABEN" ? -t.amount : t.amount} showSign />
                </Td>
              </tr>
            ))}
            {data.recent_transactions.length === 0 && (
              <tr>
                <Td className="pl-6 text-muted">Noch keine Buchungen.</Td>
                <Td /><Td /><Td />
              </tr>
            )}
          </tbody>
        </Table>
      </Card>
    </>
  );
}

export default function DashboardPage() {
  const can = useAuth((s) => s.can);
  const isFull = can("dashboard:full");
  const summary = useApi<DashboardSummary>(isFull ? "/dashboard/summary" : null);
  const member = useApi<MemberDashboard>(!isFull ? "/users/me/dashboard" : null);

  return (
    <>
      <PageHeader
        eyebrow="Übersicht"
        title="Dashboard"
        subtitle={
          isFull
            ? "Liquidität, rechnerische Bestände und Kontrollgleichung auf einen Blick."
            : "Dein persönlicher Stand und deine letzten Buchungen."
        }
      />
      {isFull ? (
        summary.loading ? (
          <Spinner />
        ) : summary.data ? (
          <AdminDashboard data={summary.data} />
        ) : (
          <Alert tone="neg" title="Daten konnten nicht geladen werden">{summary.error}</Alert>
        )
      ) : member.loading ? (
        <Spinner />
      ) : member.data ? (
        <MemberView data={member.data} />
      ) : (
        <Alert tone="neg" title="Daten konnten nicht geladen werden">{member.error}</Alert>
      )}
    </>
  );
}
