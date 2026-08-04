import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../auth";

/**
 * Initials, from a display name if there is one and the email otherwise.
 *
 * Two letters where the name has two words, one where it does not, so
 * "Sruti Ranjan" reads SR but "sruti" reads S rather than SR.
 */
function initialsFor(user: User): string {
  const source = user.display_name?.trim() || user.email.split("@")[0];
  const words = source.split(/[\s._-]+/).filter(Boolean);

  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return (words[0]?.[0] ?? "?").toUpperCase();
}

// Fixed hues rather than random: the same account keeps the same colour every
// time, which is what makes an initials avatar recognisable at all.
const HUES = [214, 152, 33, 280, 340, 190];

function hueFor(user: User): number {
  return HUES[user.id % HUES.length];
}

export function Avatar({
  user,
  size = 36,
  version = 0,
}: {
  user: User;
  size?: number;
  /** Bump to refetch after an upload; the URL alone never changes. */
  version?: number;
}) {
  const { token } = useAuth();
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !user.has_avatar) {
      setUrl(null);
      return;
    }

    let revoked: string | null = null;
    let cancelled = false;

    void api.avatarUrl(token).then((next) => {
      // Nothing holds this blob but the <img>, so an unmount between request
      // and response would leak it if it were not released here.
      if (cancelled) {
        if (next) URL.revokeObjectURL(next);
        return;
      }
      revoked = next;
      setUrl(next);
    });

    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [token, user.has_avatar, version]);

  const style = { width: size, height: size, fontSize: Math.round(size * 0.4) };

  if (url) {
    return <img className="avatar" src={url} alt="" style={style} />;
  }

  const hue = hueFor(user);

  return (
    <span
      className="avatar avatar-initials"
      aria-hidden="true"
      style={{
        ...style,
        background: `hsl(${hue} 55% 46%)`,
      }}
    >
      {initialsFor(user)}
    </span>
  );
}
