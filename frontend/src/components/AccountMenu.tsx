import { useEffect, useRef, useState } from "react";

import type { Platform, User } from "../api/types";
import { Avatar } from "./Avatar";

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
        className="avatar-btn"
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
            disabled={syncing}
            onClick={() => onSync("codeforces")}
          >
            {syncingPlatform === "codeforces" ? "Syncing…" : "Sync Codeforces"}
          </button>

          {user.leetcode_repo && (
            <button
              type="button"
              role="menuitem"
              // Both disabled while either runs: they write to the same tables,
              // and the dashboard reloads from what they leave behind.
              disabled={syncing}
              onClick={() => onSync("leetcode")}
            >
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
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
