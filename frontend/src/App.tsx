import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth";
import { Logo } from "./components/Logo";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ThemeProvider } from "./theme";

/** The screens, as URLs.
 *
 * Every view used to be a piece of React state, which meant the address bar
 * always said "/": refreshing lost your place, the back button did nothing,
 * and there was no way to link somebody to an interview. Real routes fix all
 * three at once. The dashboard keeps ownership of its loaded data and reads
 * the URL to decide what to show, so moving between screens does not refetch.
 */
function Router() {
  const { token, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="centered">
        {/* The mark rather than the word "Loading": this is the first paint,
            before we know whether anyone is signed in, and a brand held for a
            moment reads better than a status for a state nobody chose. */}
        <div className="boot" role="status" aria-label="Loading Solvix">
          {/* Sized in CSS against the viewport; see .boot .logo. */}
          <Logo />
          <span className="boot-bar" />
        </div>
      </div>
    );
  }

  const signedIn = Boolean(token && user);
  return (
    <Routes>
      <Route
        path="/login"
        element={signedIn ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/*"
        element={signedIn ? <DashboardPage /> : <Navigate to="/login" replace />}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Router />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
