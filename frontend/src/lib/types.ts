export type Kassenbereich = {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  is_active: boolean;
  sort_order: number;
};

export type KassenbereichBalance = {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
  balance: number;
};

export type Tag = {
  id: string;
  name: string;
  color: string;
  description?: string | null;
};

export type Account = {
  id: string;
  name: string;
  type: string;
  user_id?: string | null;
  is_active: boolean;
};

export type AccountBalance = {
  account: Account;
  balance: number;
};

export type TransactionLine = {
  id: string;
  account_id: string;
  kassenbereich_id: string;
  member_id?: string | null;
  side: "SOLL" | "HABEN";
  amount: number;
  description?: string | null;
};

export type Transaction = {
  id: string;
  sequential_number: number;
  date: string;
  description: string;
  category: string;
  receipt_status?: string | null;
  is_storno: boolean;
  is_locked: boolean;
  is_internal_transfer: boolean;
  notes?: string | null;
  storno_reference_id?: string | null;
  created_at: string;
  lines: TransactionLine[];
  tags: Tag[];
};

export type MoneyRow = { id: string; name: string; type: string; balance: number };
export type AreaRow = { id: string; name: string; code: string; is_active: boolean; balance: number };

export type DashboardSummary = {
  liquidity: { items: MoneyRow[]; total: number };
  kassenbereiche: { items: AreaRow[]; total: number };
  control_equation: {
    sum_kassenbereiche: number;
    liquiditaet: number;
    forderungen: number;
    verbindlichkeiten: number;
    expected: number;
    difference: number;
    balanced: boolean;
  };
  overdrawn: { id: string; name: string; balance: number; overdraft: number }[];
  forderungen: number;
  verbindlichkeiten: number;
  recent: {
    id: string;
    sequential_number: number;
    date: string;
    description: string;
    category: string;
    is_storno: boolean;
  }[];
};

export type Semester = {
  id: string;
  name: string;
  type: "winter" | "summer";
  start_date: string;
  end_date: string;
  status: "active" | "closed" | "reopened";
};

export type Member = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  membership_status: string;
  system_role: string;
  phone?: string | null;
  iban?: string | null;
  is_active: boolean;
  last_login?: string | null;
  created_at: string;
};

export type Beverage = {
  id: string;
  name: string;
  ring_color: "red" | "yellow";
  ring_price: number;
  bottles_per_crate: number;
  category: string;
  deposit_per_bottle: number;
  is_active: boolean;
};

export type RingbrettSession = {
  id: string;
  date: string;
  kassenbereich_id: string;
  zaehlungsnummer: number;
  status: string;
  notes?: string | null;
  transaction_id?: string | null;
  entries: { id: string; user_id: string; red_rings: number; yellow_rings: number }[];
};

export type EventItem = {
  id: string;
  date: string;
  name: string;
  type: "public" | "private";
  payer_type: "cc_cash" | "member";
  payer_user_id?: string | null;
  red_glasses: number;
  yellow_glasses: number;
  donation: number;
  kassenbereich_id: string;
  is_posted: boolean;
  transaction_id?: string | null;
  tags: Tag[];
};

export type Delivery = {
  id: string;
  date: string;
  supplier: string;
  invoice_number?: string | null;
  kassenbereich_id?: string | null;
  is_posted: boolean;
  transaction_id?: string | null;
};

export type Inventory = {
  id: string;
  date: string;
  status: string;
  notes?: string | null;
  items: { id: string; beverage_id: string; crates: number; single_bottles: number }[];
};

export type Refund = {
  id: string;
  date: string;
  amount: number;
  description: string;
  kassenbereich_id: string;
  status: "pending" | "approved" | "rejected" | "paid";
  transaction_id?: string | null;
};

export type AuditLog = {
  id: string;
  user_id?: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  description?: string | null;
  created_at: string;
};

export type MemberDashboard = {
  user: Member;
  total_balance: number;
  by_kassenbereich: { kassenbereich_id: string; name: string; balance: number }[];
  recent_transactions: {
    id: string;
    sequential_number: number;
    date: string;
    description: string;
    amount: number;
    side: string;
  }[];
};
