import React from "react";
import { Loader2, X } from "lucide-react";

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ Card */
export function Card({
  className,
  children,
  padded = true,
}: {
  className?: string;
  children: React.ReactNode;
  padded?: boolean;
}) {
  return (
    <div className={cx("bg-surface border border-line rounded-lg", padded && "p-6", className)}>
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div>
        <h2 className="text-base font-semibold tracking-tight text-ink">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

/* --------------------------------------------------------------- PageHead */
export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-8">
      <div>
        {eyebrow && (
          <div className="text-2xs font-medium uppercase tracking-[0.14em] text-muted mb-2">{eyebrow}</div>
        )}
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-2 text-sm text-muted max-w-2xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- Button */
type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  icon?: React.ReactNode;
  loading?: boolean;
};

export function Button({
  variant = "secondary",
  size = "md",
  icon,
  loading,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap";
  const sizes = { sm: "h-9 px-3 text-sm", md: "h-10 px-4 text-sm" }[size];
  const variants = {
    primary: "bg-accent text-accent-ink hover:bg-accent/90",
    secondary: "bg-surface border border-line text-ink hover:bg-bg",
    ghost: "text-muted hover:text-ink hover:bg-bg",
    danger: "bg-surface border border-line text-neg hover:bg-neg/5",
  }[variant];
  return (
    <button className={cx(base, sizes, variants, className)} disabled={disabled || loading} {...rest}>
      {loading ? <Loader2 size={16} className="animate-spin" /> : icon}
      {children}
    </button>
  );
}

/* ----------------------------------------------------------------- Input */
export function Field({
  label,
  hint,
  error,
  children,
  className,
}: {
  label?: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={cx("block", className)}>
      {label && <span className="block text-sm font-medium text-ink mb-1.5">{label}</span>}
      {children}
      {hint && !error && <span className="block mt-1.5 text-xs text-muted">{hint}</span>}
      {error && <span className="block mt-1.5 text-xs text-neg">{error}</span>}
    </label>
  );
}

const controlCls =
  "w-full h-10 rounded-md border border-line bg-surface px-3 text-sm text-ink placeholder:text-muted/70 focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...rest }, ref) => <input ref={ref} className={cx(controlCls, className)} {...rest} />,
);
Input.displayName = "Input";

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...rest }, ref) => (
    <select ref={ref} className={cx(controlCls, "pr-8 appearance-none", className)} {...rest}>
      {children}
    </select>
  ),
);
Select.displayName = "Select";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...rest }, ref) => (
    <textarea ref={ref} className={cx(controlCls, "h-auto min-h-[80px] py-2", className)} {...rest} />
  ),
);
Textarea.displayName = "Textarea";

/* ----------------------------------------------------------------- Badge */
export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "accent" | "pos" | "neg" | "warn";
  className?: string;
}) {
  const tones = {
    neutral: "bg-bg text-muted border-line",
    accent: "bg-accent-weak text-accent border-transparent",
    pos: "bg-pos/10 text-pos border-transparent",
    neg: "bg-neg/10 text-neg border-transparent",
    warn: "bg-warn/10 text-warn border-transparent",
  }[tone];
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-2xs font-medium",
        tones,
        className,
      )}
    >
      {children}
    </span>
  );
}

/* --------------------------------------------------------------- StatCard */
export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = "neutral",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  icon?: React.ReactNode;
  tone?: "neutral" | "pos" | "neg" | "accent";
}) {
  const valueTone = {
    neutral: "text-ink",
    pos: "text-pos",
    neg: "text-neg",
    accent: "text-accent",
  }[tone];
  return (
    <div className="bg-surface border border-line rounded-lg p-5">
      <div className="flex items-center justify-between">
        <span className="text-2xs font-medium uppercase tracking-[0.12em] text-muted">{label}</span>
        {icon && <span className="text-muted">{icon}</span>}
      </div>
      <div className={cx("mt-3 text-2xl font-semibold tracking-tight tnum", valueTone)}>{value}</div>
      {hint && <div className="mt-1.5 text-xs text-muted">{hint}</div>}
    </div>
  );
}

/* ----------------------------------------------------------------- Table */
export function Table({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cx("w-full overflow-x-auto", className)}>
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  );
}

export function Th({ children, className, align = "left" }: { children?: React.ReactNode; className?: string; align?: "left" | "right" | "center" }) {
  return (
    <th
      className={cx(
        "px-4 py-3 text-2xs font-medium uppercase tracking-[0.1em] text-muted border-b border-line",
        align === "right" && "text-right",
        align === "center" && "text-center",
        align === "left" && "text-left",
        className,
      )}
    >
      {children}
    </th>
  );
}

export function Td({ children, className, align = "left" }: { children?: React.ReactNode; className?: string; align?: "left" | "right" | "center" }) {
  return (
    <td
      className={cx(
        "px-4 py-3.5 border-b border-line text-ink align-middle",
        align === "right" && "text-right",
        align === "center" && "text-center",
        className,
      )}
    >
      {children}
    </td>
  );
}

/* ------------------------------------------------------------ EmptyState */
export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      {icon && <div className="text-muted/70 mb-4">{icon}</div>}
      <div className="text-sm font-medium text-ink">{title}</div>
      {description && <div className="mt-1.5 text-sm text-muted max-w-sm">{description}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* --------------------------------------------------------------- Spinner */
export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-muted">
      <Loader2 size={18} className="animate-spin" />
      <span className="text-sm">{label ?? "Lädt …"}</span>
    </div>
  );
}

/* ----------------------------------------------------------------- Alert */
export function Alert({
  tone = "warn",
  title,
  children,
  icon,
}: {
  tone?: "warn" | "neg" | "pos" | "accent";
  title?: string;
  children?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  const tones = {
    warn: "border-warn/30 bg-warn/5 text-warn",
    neg: "border-neg/30 bg-neg/5 text-neg",
    pos: "border-pos/30 bg-pos/5 text-pos",
    accent: "border-accent/30 bg-accent-weak text-accent",
  }[tone];
  return (
    <div className={cx("flex gap-3 rounded-lg border p-4", tones)}>
      {icon && <div className="mt-0.5 shrink-0">{icon}</div>}
      <div className="text-sm">
        {title && <div className="font-medium">{title}</div>}
        {children && <div className={cx("text-ink/80", title && "mt-1")}>{children}</div>}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Dialog */
export function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
  width = "max-w-lg",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-6">
      <div className="absolute inset-0 bg-ink/30 backdrop-blur-[2px]" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        className={cx(
          "relative w-full bg-surface border border-line rounded-t-xl sm:rounded-xl shadow-soft",
          width,
        )}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-line">
          <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
          <button onClick={onClose} className="text-muted hover:text-ink transition-colors" aria-label="Schließen">
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-5 max-h-[70vh] overflow-y-auto">{children}</div>
        {footer && <div className="px-6 py-4 border-t border-line flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Tabs */
export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="inline-flex items-center gap-1 rounded-lg border border-line bg-surface p-1">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={cx(
            "px-3.5 h-8 rounded-md text-sm font-medium transition-colors",
            value === t.id ? "bg-accent-weak text-accent" : "text-muted hover:text-ink",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* --------------------------------------------------------------- MoneyTxt */
export function Money({
  value,
  className,
  showSign = false,
}: {
  value: number;
  className?: string;
  showSign?: boolean;
}) {
  const tone = value < 0 ? "text-neg" : value > 0 && showSign ? "text-pos" : "";
  const sign = showSign && value > 0 ? "+" : "";
  return (
    <span className={cx("tnum", tone, className)}>
      {sign}
      {new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(value)}
    </span>
  );
}
