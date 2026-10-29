"use client";

// Step 02: the new background colour.
//
// Three ways, all kept in sync: a few swatches, a hex box (any format the CLI
// accepts, e.g. #FF0066 or #00000000 for a transparent cut-out), and the
// browser's own colour picker (6-digit colours only).

import { isHexColor } from "@/lib/api";

const SWATCHES = [
  { hex: "#FFFFFF", name: "White" },
  { hex: "#E4E0D8", name: "Sand" },
  { hex: "#FF0066", name: "Pink" },
  { hex: "#2A78D6", name: "Blue" },
  { hex: "#0A0A0A", name: "Black" },
  { hex: "#00000000", name: "Transparent" },
];

type Props = {
  color: string;
  onChange: (color: string) => void;
};

/** "#f06" -> "#FF0066": the 6-digit form the native picker needs, or null. */
function toSixDigits(text: string): string | null {
  let digits = text.trim().replace(/^#/, "");
  if (digits.length === 3 || digits.length === 4) digits = [...digits].map((c) => c + c).join("");
  return digits.length >= 6 ? `#${digits.slice(0, 6)}` : null;
}

export function ColorPicker({ color, onChange }: Props) {
  const valid = isHexColor(color);
  const nativeValue = (valid && toSixDigits(color)) || "#ffffff";

  return (
    <fieldset className="step">
      <legend className="step-label">02 Colour</legend>
      <div className="swatches">
        {SWATCHES.map((s) => (
          <button
            key={s.hex}
            type="button"
            className={`swatch${s.hex === "#00000000" ? " checker" : ""}`}
            style={s.hex === "#00000000" ? undefined : { background: s.hex }}
            aria-pressed={color.toUpperCase() === s.hex}
            aria-label={`${s.name} ${s.hex}`}
            title={`${s.name} ${s.hex}`}
            onClick={() => onChange(s.hex)}
          />
        ))}
      </div>
      <div className="hex-row">
        <label htmlFor="hex" className="sr-only">
          Hex colour
        </label>
        <input
          id="hex"
          className="hex-input"
          value={color}
          onChange={(e) => onChange(e.target.value)}
          spellCheck={false}
          autoComplete="off"
          placeholder="#FF0066"
          aria-invalid={!valid}
          aria-describedby="hex-help"
        />
        <input
          className="native-picker"
          type="color"
          value={nativeValue.toLowerCase()}
          onChange={(e) => onChange(e.target.value.toUpperCase())}
          aria-label="Pick a colour"
        />
      </div>
      {valid ? (
        <p id="hex-help" className="hint">
          #RGB, #RRGGBB or #RRGGBBAA. #00000000 gives a transparent cut-out.
        </p>
      ) : (
        <p id="hex-help" className="field-error">
          Use a hex colour such as #FF0066.
        </p>
      )}
    </fieldset>
  );
}
