"use client";

// A box to drop a picture on, or click to browse. Used twice: for the photo
// (01) and for a background picture (02).
//
// The whole box is the <label> of a real (visually hidden) file input, so it
// works with a mouse, a finger and the keyboard (Tab, then Enter or Space).

import { useEffect, useId, useState } from "react";
import { MAX_UPLOAD_BYTES } from "@/lib/api";

type Props = {
  file: File | null;
  onChange: (file: File) => void;
  /** Shown before a file is chosen, e.g. "Drop a photo or browse". */
  title: string;
  /** The line under it, e.g. "A person or a product". */
  subtitle: string;
  /** Used in the error messages, e.g. "photo" or "picture". */
  noun: string;
};

export function ImageDrop({ file, onChange, title, subtitle, noun }: Props) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thumb, setThumb] = useState<string | null>(null);
  const hintId = useId();

  // A small preview of the chosen file; the URL is freed when it changes.
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setThumb(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function accept(chosen: File | undefined) {
    if (!chosen) return;
    if (!chosen.type.startsWith("image/")) {
      setError("That file isn't an image. Use JPEG, PNG or WebP.");
      return;
    }
    if (chosen.size > MAX_UPLOAD_BYTES) {
      setError(`That ${noun} is larger than 20 MB.`);
      return;
    }
    setError(null);
    onChange(chosen);
  }

  return (
    <>
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
          aria-describedby={hintId}
        />
        {file && thumb ? (
          <img src={thumb} alt="" />
        ) : (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
            <path d="M12 16V4m0 0-5 5m5-5 5 5M4 16v4h16v-4" />
          </svg>
        )}
        <span className="dropzone-text">
          <strong>{file ? file.name : title}</strong>
          <span>{file ? "Choose another" : subtitle}</span>
        </span>
      </label>
      <p id={hintId} className="hint">
        JPEG, PNG or WebP, up to 20 MB.
      </p>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
