"use client";

// The whole page. It only holds the user's choices and the result; each part
// is its own component, and the API call is in lib/api.ts.
//
//   header        name + links (CLI, API docs, GitHub)
//   ApiStatus     banner if the API isn't running
//   controls      01 PhotoDrop, 02 ColorPicker, 03 ShadowControls, the button
//   result        empty / working / BeforeAfter + download
//   footer        the CLI command: the main way to use the project

import { useEffect, useState } from "react";
import { ApiStatus } from "@/components/ApiStatus";
import { BeforeAfter } from "@/components/BeforeAfter";
import { ColorPicker } from "@/components/ColorPicker";
import { PhotoDrop } from "@/components/PhotoDrop";
import { ShadowControls } from "@/components/ShadowControls";
import { API_URL, ApiError, changeBackground, isHexColor, type ChangeResult, type ShadowKind } from "@/lib/api";

const GITHUB_URL = "https://github.com/Maher-bouchrara/bg-changer-MODELIA";

/** True for #RGBA / #RRGGBBAA colours that are not fully opaque (the result has transparency). */
function hasTransparency(hex: string): boolean {
  const d = hex.trim().replace(/^#/, "");
  return (d.length === 4 && d[3].toLowerCase() !== "f") || (d.length === 8 && d.slice(6).toLowerCase() !== "ff");
}

export default function Page() {
  // The user's choices.
  const [photo, setPhoto] = useState<File | null>(null);
  const [color, setColor] = useState("#FF0066");
  const [shadow, setShadow] = useState<ShadowKind>("real");
  const [strength, setStrength] = useState(1);

  // The result and what is happening.
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [result, setResult] = useState<ChangeResult | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Local URL of the chosen photo, for the "before" side.
  useEffect(() => {
    if (!photo) return;
    const url = URL.createObjectURL(photo);
    setPhotoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  // Free the previous result's URL when a new one replaces it.
  useEffect(() => () => void (result && URL.revokeObjectURL(result.url)), [result]);

  function choosePhoto(file: File) {
    setPhoto(file);
    setResult(null);
    setError(null);
  }

  async function run() {
    if (!photo) {
      setError("Choose a photo first.");
      return;
    }
    if (!isHexColor(color)) {
      setError("Use a hex colour such as #FF0066.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      setResult(await changeBackground(photo, color, shadow, strength));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Try again.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <>
      <header className="header">
        <a className="wordmark" href="/">
          BGCHANGE
        </a>
        <nav className="nav" aria-label="Links">
          <a href="#cli">CLI</a>
          <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer">
            API docs
          </a>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </header>

      <ApiStatus />

      <main>
        <section className="intro">
          <h1>
            Change the background.
            <br />
            Keep the shadow.
          </h1>
          <p>A person or product photo, any hex colour. The AI cuts out the subject, cleans the edges and keeps its shadow.</p>
        </section>

        <div className="workspace">
          <form
            className="controls"
            onSubmit={(e) => {
              e.preventDefault();
              void run();
            }}
          >
            <PhotoDrop photo={photo} onChange={choosePhoto} />
            <ColorPicker color={color} onChange={setColor} />
            <ShadowControls shadow={shadow} strength={strength} onShadowChange={setShadow} onStrengthChange={setStrength} />
            <div>
              <button type="submit" className="button button-primary" aria-busy={working}>
                {working ? "Working…" : "Change background"}
              </button>
              {error && (
                <p className="alert" role="alert" style={{ marginTop: 12 }}>
                  {error}
                </p>
              )}
            </div>
          </form>

          <section className="result" aria-label="Result" aria-busy={working}>
            {result && photoUrl ? (
              <BeforeAfter before={photoUrl} after={result.url} transparent={hasTransparency(color)} />
            ) : (
              <div className="stage">
                {photoUrl ? (
                  <img src={photoUrl} alt="Chosen photo" />
                ) : (
                  <div className="stage-empty">
                    <strong>Your result appears here</strong>
                    <span>Choose a photo, a colour and a shadow, then change the background.</span>
                  </div>
                )}
                {working && <span className="working-veil" aria-hidden="true" />}
                {working && <span className="progress" aria-hidden="true" />}
              </div>
            )}

            <div className="result-bar" aria-live="polite">
              <span>
                {working
                  ? "Working: about 3 seconds…"
                  : result
                    ? `${result.size.replace("x", " × ")} · ${(result.timeMs / 1000).toFixed(1)} s · ${result.model}`
                    : "PNG, same size as your photo"}
              </span>
              {result && (
                <a className="button button-outline" href={result.url} download={result.filename}>
                  Download PNG
                </a>
              )}
            </div>
          </section>
        </div>
      </main>

      <footer className="footer" id="cli">
        <span>Prefer the terminal? The command does the same:</span>
        <code>
          uv run bgchange photo.jpg --color &quot;{color.trim() || "#FF0066"}&quot; --shadow {shadow}
          {strength !== 1 && shadow !== "none" ? ` --shadow-strength ${strength}` : ""}
        </code>
      </footer>
    </>
  );
}
