// The 2 calls to the bgchange API, in one place.
//
//   getHealth()           GET  /api/health             is the API up, is the model loaded?
//   changeBackground()    POST /api/change-background  photo + colour -> PNG
//
// The API is the Python server started with `uv run bgchange-api`
// (docs/08b-api.md). Its address comes from NEXT_PUBLIC_API_URL so Docker can
// change it; by default it is the local one.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/** Same names as the API and the CLI (`--shadow`). */
export const SHADOW_KINDS = ["real", "fake", "mix", "none"] as const;
export type ShadowKind = (typeof SHADOW_KINDS)[number];

/** Same limit as the API's default (BGCHANGE_MAX_UPLOAD_MB), checked here first to fail fast. */
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

/** #RGB, #RGBA, #RRGGBB or #RRGGBBAA, "#" optional: the formats the API accepts. */
const HEX = /^#?([0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/i;

export function isHexColor(text: string): boolean {
  return HEX.test(text.trim());
}

export type Health = {
  status: string;
  model: string;
  model_loaded: boolean;
  device: string;
};

/** The API's answer, or null if it cannot be reached at all (not started, wrong address). */
export async function getHealth(): Promise<Health | null> {
  try {
    const response = await fetch(`${API_URL}/api/health`, { signal: AbortSignal.timeout(4000) });
    return response.ok ? ((await response.json()) as Health) : null;
  } catch {
    return null;
  }
}

export type ChangeResult = {
  /** A local URL for <img src> and the download link (revoke it when replaced). */
  url: string;
  filename: string;
  /** e.g. "1600x1200" */
  size: string;
  timeMs: number;
  model: string;
};

/** An error with the API's own sentence, ready to show to the user. */
export class ApiError extends Error {}

export async function changeBackground(
  photo: File,
  color: string,
  shadow: ShadowKind,
  shadowStrength: number,
): Promise<ChangeResult> {
  const form = new FormData();
  form.append("image", photo);
  form.append("color", color.trim());
  form.append("shadow", shadow);
  form.append("shadow_strength", String(shadowStrength));

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/change-background`, { method: "POST", body: form });
  } catch {
    throw new ApiError("The API isn't reachable. Start it with: uv run bgchange-api");
  }

  if (!response.ok) {
    // Every API error is {"error": "a sentence"} (bgchange/api/app.py).
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.error ?? `The API answered with error ${response.status}.`);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  return {
    url: URL.createObjectURL(blob),
    filename: /filename="([^"]+)"/.exec(disposition)?.[1] ?? "bgchange.png",
    size: response.headers.get("X-Image-Size") ?? "",
    timeMs: Number(response.headers.get("X-Processing-Time-Ms") ?? 0),
    model: response.headers.get("X-Model") ?? "",
  };
}
