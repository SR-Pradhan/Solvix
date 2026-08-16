import { AuthProvider, useAuth } from "./auth";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ThemeProvider } from "./theme";

function Router() {
  const { token, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="centered">
        {/* The mark rather than the word "Loading": this is the first paint,
            before we know whether anyone is signed in, and a brand held for a
            moment reads better than a status for a state nobody chose. */}
        <div className="boot" role="status" aria-label="Loading Solvix">
          <span className="brand">Solvix</span>
          <span className="boot-bar" />
        </div>
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
