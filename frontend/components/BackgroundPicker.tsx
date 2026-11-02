"use client";

// Step 02: the new background, a colour or a picture.
//
//   Colour   swatches + hex box (ColorPicker), like the CLI's --color
//   Image    a picture to put behind the subject, like the CLI's --background;
//            the API scales and crops it to the photo's size
//
// The two choices are real radio buttons drawn as one bar (like 03 Shadow).

import { ColorPicker } from "@/components/ColorPicker";
import { ImageDrop } from "@/components/ImageDrop";

export type BackgroundMode = "colour" | "image";

type Props = {
  mode: BackgroundMode;
  onModeChange: (mode: BackgroundMode) => void;
  color: string;
  onColorChange: (color: string) => void;
  picture: File | null;
  onPictureChange: (picture: File) => void;
};

export function BackgroundPicker({ mode, onModeChange, color, onColorChange, picture, onPictureChange }: Props) {
  return (
    <fieldset className="step">
      <legend className="step-label">02 Background</legend>
      <div className="segmented">
        {(["colour", "image"] as const).map((m) => (
          <label key={m}>
            <input type="radio" name="background" value={m} checked={mode === m} onChange={() => onModeChange(m)} />
            {m}
          </label>
        ))}
      </div>
      {mode === "colour" ? (
        <ColorPicker color={color} onChange={onColorChange} />
      ) : (
        <>
          <ImageDrop
            file={picture}
            onChange={onPictureChange}
            title="Drop a background picture"
            subtitle="Scaled and cropped to fill the photo"
            noun="picture"
          />
          <p className="hint">Best with a simple scene lit like the photo (a wall, a table, a floor).</p>
        </>
      )}
    </fieldset>
  );
}
