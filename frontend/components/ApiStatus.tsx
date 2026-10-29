"use client";

// A black banner at the top when the API can't be used, with the exact command
// to fix it. Nothing is shown when everything is fine.
//
// Asks GET /api/health once when the page opens, and again on "Check again".

import { useCallback, useEffect, useState } from "react";
import { getHealth, type Health } from "@/lib/api";

type Status = "checking" | "ok" | "down" | "no-model";

export function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [health, setHealth] = useState<Health | null>(null);

  const check = useCallback(async () => {
    const result = await getHealth();
    setHealth(result);
    setStatus(!result ? "down" : result.model_loaded ? "ok" : "no-model");
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  if (status === "checking" || status === "ok") return null;

  return (
    <div className="banner" role="status">
      {status === "down" ? (
        <>
          The API isn&apos;t running. In the project folder, run <code>uv run bgchange-api</code>, then{" "}
        </>
      ) : (
        <>
          The model <code>{health?.model}</code> isn&apos;t downloaded. Run{" "}
          <code>uv run python scripts/download_models.py</code>, restart the API, then{" "}
        </>
      )}
      <button type="button" onClick={check} style={{ background: "none", border: 0, padding: 0, textDecoration: "underline", cursor: "pointer" }}>
        check again
      </button>
      .
    </div>
  );
}
