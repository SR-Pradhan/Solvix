import { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth";
import { Logo } from "./components/Logo";
import { MotionConfig } from "framer-motion";

import { LoginPage } from "./pages/LoginPage";

/* Everything except the login form arrives when it is asked for. The login
   page is what an unknown visitor sees first and what a returning one sees on
   an expired session, so it stays in the first download; the dashboard and
   its chart library do not need to be there for either. */
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const LandingPage = lazy(() =>
  import("./pages/LandingPage").then((m) => ({ default: m.LandingPage })),
);
const SetupPage = lazy(() =>
  import("./pages/SetupPage").then((m) => ({ default: m.SetupPage })),
);
import { ThemeProvider } from "./theme";
import { ToastProvider } from "./toast";

/** The screens, as URLs.
 *
 * Every view used to be a piece of React state, which meant the address bar
 * always said "/": refreshing lost your place, the back button did nothing,
 * and there was no way to link somebody to an interview. Real routes fix all
 * three at once. The dashboard keeps ownership of its loaded data and reads
 * the URL to decide what to show, so moving between screens does not refetch.
 */
function Boot() {
  return (
    <div className="centered">
      <div className="boot" role="status" aria-label="Loading Solvix">
        <Logo />
        <span className="boot-bar" />
      </div>
    </div>
  );
}

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
      {/* Signed out, the root is the pitch; signed in, it is the dashboard.
          Any other signed-out path goes to the pitch too, not the form. */}
      <Route path="/" element={signedIn ? <DashboardPage /> : <LandingPage />} />
      {/* Declared before the catch-all so the dashboard never sees /setup and
          treats it as an unknown path. */}
      <Route
        path="/setup"
        element={signedIn ? <SetupPage /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/*"
        element={signedIn ? <DashboardPage /> : <Navigate to="/" replace />}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <MotionConfig reducedMotion="user">
            <ToastProvider>
              <Suspense fallback={<Boot />}>
                <Router />
              </Suspense>
            </ToastProvider>
          </MotionConfig>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
