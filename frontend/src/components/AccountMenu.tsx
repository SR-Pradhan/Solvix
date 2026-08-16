import { useEffect, useRef, useState } from "react";

import type { Platform, User } from "../api/types";
import { Avatar } from "./Avatar";

/* Small UI glyphs, inline rather than from a package: four shapes do not
   justify a dependency, and drawing them with `currentColor` means they take
   the menu's hover and danger colours for free. */
function Icon({ path }: { path: string }) {
  return (
    <svg
      className="menu-icon"
      viewBox="0 0 16 16"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

const SYNC = "M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2v3h-3";
const PERSON = "M13 13.5c0-2.2-2.2-3.5-5-3.5s-5 1.3-5 3.5M8 7.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5";
const EXIT = "M6 14H3.5A1.5 1.5 0 0 1 2 12.5v-9A1.5 1.5 0 0 1 3.5 2H6M10.5 11 14 8l-3.5-3M14 8H6";

/** The avatar, and everything that used to crowd the header.
 *
 * Syncing was two top-level buttons until the morning job started importing on
 * its own. Once a thing runs by itself, giving it permanent space says it
 * still needs you — so it moved in here, where it is available without being
 * asked for.
 */
export function AccountMenu({
  user,
  syncingPlatform,
  onSync,
  onProfile,
  onLogout,
}: {
  user: User;
  syncingPlatform: Platform | null;
  onSync: (platform: Platform) => void;
  onProfile: () => void;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: MouseEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      // Escape closes without moving focus elsewhere, which is what anyone
      // reaching for it expects.
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const syncing = syncingPlatform !== null;

  return (
    <div className="account" ref={container}>
      <button
        type="button"
        className={`avatar-btn${open ? " on" : ""}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account and sync"
        onClick={() => setOpen(!open)}
      >
        <Avatar user={user} size={36} />
      </button>

      {open && (
        <div className="menu" role="menu">
          <div className="menu-head">
            <span className="menu-name">{user.display_name ?? user.email}</span>
            <span className="muted small">{user.email}</span>
          </div>

          <button
            type="button"
            role="menuitem"
            // Both rows are disabled while either runs, but only the one doing
            // the work is marked as working — a spinner on the idle row says it
            // is busy too.
            className={syncingPlatform === "codeforces" ? "is-working" : ""}
            disabled={syncing}
            onClick={() => onSync("codeforces")}
          >
            <Icon path={SYNC} />
            {syncingPlatform === "codeforces" ? "Syncing…" : "Sync Codeforces"}
          </button>

          {user.leetcode_repo && (
            <button
              type="button"
              role="menuitem"
              // Both disabled while either runs: they write to the same tables,
              // and the dashboard reloads from what they leave behind.
              className={syncingPlatform === "leetcode" ? "is-working" : ""}
              disabled={syncing}
              onClick={() => onSync("leetcode")}
            >
              <Icon path={SYNC} />
              {syncingPlatform === "leetcode" ? "Syncing…" : "Sync LeetCode"}
            </button>
          )}

          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onProfile();
            }}
          >
            <Icon path={PERSON} />
            Profile
          </button>

          {/* Separated, because logging out is the one item here you cannot
              undo by clicking again. */}
          <button
            type="button"
            role="menuitem"
            className="menu-danger"
            onClick={onLogout}
          >
            <Icon path={EXIT} />
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
