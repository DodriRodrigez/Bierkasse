import { useEffect } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import AppShell from "./layout/AppShell";
import { useAuth } from "./stores/auth";
import { getToken } from "./lib/api";
import LoginPage from "./features/auth/LoginPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import TransactionsPage from "./features/accounting/TransactionsPage";
import NewTransactionPage from "./features/accounting/NewTransactionPage";
import KassenbereichePage from "./features/kassenbereiche/KassenbereichePage";
import RingbrettPage from "./features/ringbrett/RingbrettPage";
import EventsPage from "./features/events/EventsPage";
import BeveragesPage from "./features/beverages/BeveragesPage";
import InventoryPage from "./features/inventory/InventoryPage";
import RefundsPage from "./features/refunds/RefundsPage";
import MembersPage from "./features/members/MembersPage";
import SemestersPage from "./features/semesters/SemestersPage";
import ProfilePage from "./features/profile/ProfilePage";

function RequireAuth() {
  const { user, ready, loadMe } = useAuth();

  useEffect(() => {
    if (!user && getToken()) loadMe();
    else if (!user && !getToken()) useAuth.setState({ ready: true });
  }, [user, loadMe]);

  if (!ready && !user && getToken()) {
    return <div className="min-h-screen grid place-items-center text-sm text-muted">Lädt …</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/buchungen" element={<TransactionsPage />} />
          <Route path="/buchungen/neu" element={<NewTransactionPage />} />
          <Route path="/kassenbereiche" element={<KassenbereichePage />} />
          <Route path="/ringbrett" element={<RingbrettPage />} />
          <Route path="/veranstaltungen" element={<EventsPage />} />
          <Route path="/getraenke" element={<BeveragesPage />} />
          <Route path="/inventur" element={<InventoryPage />} />
          <Route path="/erstattungen" element={<RefundsPage />} />
          <Route path="/mitglieder" element={<MembersPage />} />
          <Route path="/semester" element={<SemestersPage />} />
          <Route path="/profil" element={<ProfilePage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
