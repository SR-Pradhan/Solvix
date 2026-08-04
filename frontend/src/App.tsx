import { AuthProvider, useAuth } from "./auth";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ThemeProvider } from "./theme";

function Router() {
  const { token, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="centered">
        <p className="muted">Loading…</p>
      </div>
    );
  }
  return token && user ? <DashboardPage /> : <LoginPage />;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router />
      </AuthProvider>
    </ThemeProvider>
  );
}
