"use client";

// Step 01: choose the photo, by dropping it on the box or browsing.
// The box itself is ImageDrop, shared with the background picture (02).

import { ImageDrop } from "@/components/ImageDrop";

type Props = {
  photo: File | null;
  onChange: (photo: File) => void;
};

export function PhotoDrop({ photo, onChange }: Props) {
  return (
    <fieldset className="step">
      <legend className="step-label">01 Photo</legend>
      <ImageDrop file={photo} onChange={onChange} title="Drop a photo or browse" subtitle="A person or a product" noun="photo" />
    </fieldset>
  );
}
