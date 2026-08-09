import { useState } from "react";

interface Props {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  minLength?: number;
  required?: boolean;
}

/** A password field that can be revealed.
 *
 * Typing a password blind is the main reason people fail a login they
 * actually knew — and on an account with rate limiting, three blind typos now
 * cost fifteen minutes. The toggle is a button rather than a checkbox so it
 * sits inside the field, and it never leaves the field's own tab order.
 */
export function PasswordInput({
  label,
  value,
  onChange,
  autoComplete,
  minLength,
  required,
}: Props) {
  const [shown, setShown] = useState(false);

  return (
    <label>
      {label}
      <span className="password-field">
        <input
          type={shown ? "text" : "password"}
          required={required}
          minLength={minLength}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="reveal"
          onClick={() => setShown(!shown)}
          // The label describes the action, not the state, so a screen reader
          // announces what pressing it will do.
          aria-label={shown ? "Hide password" : "Show password"}
          title={shown ? "Hide password" : "Show password"}
          // Revealing is a convenience, not a step in the form: keeping it out
          // of the tab order means Tab still goes field → field → submit.
          tabIndex={-1}
        >
          {shown ? "Hide" : "Show"}
        </button>
      </span>
    </label>
  );
}
