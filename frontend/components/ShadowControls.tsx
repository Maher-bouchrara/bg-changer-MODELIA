"use client";

// Step 03: which shadow, and how dark.
//
// The same 4 choices as the CLI's --shadow (docs/06c-shadows.md). They are real
// radio buttons drawn as one bar, so arrow keys move between them.

import { SHADOW_KINDS, type ShadowKind } from "@/lib/api";

const HELP: Record<ShadowKind, string> = {
  real: "The photo's own shadow. Best on studio photos.",
  fake: "A soft shadow computed under the subject.",
  mix: "Both together: the most grounded look.",
  none: "No shadow.",
};

type Props = {
  shadow: ShadowKind;
  strength: number;
  onShadowChange: (shadow: ShadowKind) => void;
  onStrengthChange: (strength: number) => void;
};

export function ShadowControls({ shadow, strength, onShadowChange, onStrengthChange }: Props) {
  return (
    <fieldset className="step">
      <legend className="step-label">03 Shadow</legend>
      <div className="segmented">
        {SHADOW_KINDS.map((kind) => (
          <label key={kind}>
            <input
              type="radio"
              name="shadow"
              value={kind}
              checked={shadow === kind}
              onChange={() => onShadowChange(kind)}
            />
            {kind}
          </label>
        ))}
      </div>
      <p className="hint">{HELP[shadow]}</p>
      <div className="strength">
        <label htmlFor="strength">Strength</label>
        <input
          id="strength"
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={strength}
          disabled={shadow === "none"}
          onChange={(e) => onStrengthChange(Number(e.target.value))}
        />
        <output htmlFor="strength">{strength.toFixed(2)}</output>
      </div>
    </fieldset>
  );
}
