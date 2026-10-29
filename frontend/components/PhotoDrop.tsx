"use client";

// Step 01: choose the photo, by dropping it on the box or browsing.
//
// The whole box is the <label> of a real (visually hidden) file input, so it
// works with a mouse, a finger and the keyboard (Tab, then Enter or Space).

import { useEffect, useState } from "react";
import { MAX_UPLOAD_BYTES } from "@/lib/api";

type Props = {
  photo: File | null;
  onChange: (photo: File) => void;
};

export function PhotoDrop({ photo, onChange }: Props) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thumb, setThumb] = useState<string | null>(null);

  // A small preview of the chosen photo; the URL is freed when it changes.
  useEffect(() => {
    if (!photo) return;
    const url = URL.createObjectURL(photo);
    setThumb(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  function accept(file: File | undefined) {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("That file isn't an image. Use JPEG, PNG or WebP.");
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError("That photo is larger than 20 MB.");
      return;
    }
    setError(null);
    onChange(file);
  }

  return (
    <fieldset className="step">
      <legend className="step-label">01 Photo</legend>
      <label
        className={`dropzone${dragging ? " is-dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          accept(e.dataTransfer.files[0]);
        }}
      >
        <input
          className="sr-only"
          type="file"
          accept="image/*"
          onChange={(e) => accept(e.target.files?.[0])}
          aria-describedby="photo-hint"
        />
        {photo && thumb ? (
          <img src={thumb} alt="" />
        ) : (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
            <path d="M12 16V4m0 0-5 5m5-5 5 5M4 16v4h16v-4" />
          </svg>
        )}
        <span className="dropzone-text">
          <strong>{photo ? photo.name : "Drop a photo or browse"}</strong>
          <span>{photo ? "Choose another" : "A person or a product"}</span>
        </span>
      </label>
      <p id="photo-hint" className="hint">
        JPEG, PNG or WebP, up to 20 MB.
      </p>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
