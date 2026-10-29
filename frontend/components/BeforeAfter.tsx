"use client";

// The result: the original and the new image on top of each other, cut at the
// slider. Drag anywhere on the image, or focus it and use the arrow keys.
//
// A transparent result (#00000000) is shown on a checkerboard so the cut-out
// is visible.

import { useState, type CSSProperties } from "react";

type Props = {
  before: string;
  after: string;
  transparent: boolean;
};

export function BeforeAfter({ before, after, transparent }: Props) {
  const [split, setSplit] = useState(50); // % from the left where "after" starts

  return (
    <div className="stage" style={{ "--split": `${split}%` } as CSSProperties}>
      <img src={before} alt="Original photo" />
      <div className={`compare-after${transparent ? " checker" : ""}`} style={{ position: "absolute", inset: 0 }}>
        <img src={after} alt="Photo with the new background" />
      </div>
      <input
        className="compare-range"
        type="range"
        min={0}
        max={100}
        value={split}
        onChange={(e) => setSplit(Number(e.target.value))}
        aria-label="Compare before and after"
        aria-valuetext={`${split}% original, ${100 - split}% result`}
      />
      <span className="compare-line" aria-hidden="true" />
      <span className="compare-handle" aria-hidden="true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="m8 7-5 5 5 5M16 7l5 5-5 5" />
        </svg>
      </span>
      <span className="tag tag-before" aria-hidden="true">
        BEFORE
      </span>
      <span className="tag tag-after" aria-hidden="true">
        AFTER
      </span>
    </div>
  );
}
