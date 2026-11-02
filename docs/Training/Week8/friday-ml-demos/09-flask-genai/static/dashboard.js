"use strict";

// Keep one explanation request active at a time, even if polling replaces rows.
let explaining = false;
const byId = (id) => document.getElementById(id);

// Both routes return JSON; show a server message for unsuccessful HTTP statuses.
async function readJson(response) {
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Request failed.");
  return body;
}

// This explicit click action is the only browser code that can call OpenAI.
// Polling below reads local records and never invokes this action.
async function explain(event) {
  if (explaining) return;
  explaining = true;
  document.querySelectorAll("button[data-explain]").forEach((button) => { button.disabled = true; });
  byId("selected-transaction").textContent = `Transaction ${event.transaction_id} · Model ${event.model_version}`;
  byId("explanation").textContent = "Requesting an explanation…";
  try {
    const result = await readJson(await fetch(`/api/predictions/${event.id}/explain`, { method: "POST" }));
    byId("explanation").textContent = result.explanation;
  } catch (error) {
    byId("explanation").textContent = error.message;
  } finally {
    explaining = false;
    await refresh();
  }
}

// Summary numbers cover the full database; the response table is limited to 100.
async function refresh() {
  try {
    const data = await readJson(await fetch("/api/predictions", { cache: "no-store" }));
    byId("processed").textContent = data.stats.processed.toLocaleString();
    byId("flagged").textContent = data.stats.flagged.toLocaleString();
    byId("accuracy").textContent = data.stats.accuracy === null ? "—" : `${(data.stats.accuracy * 100).toFixed(1)}%`;
    const rows = data.predictions.map((event) => {
      const row = document.createElement("tr");
      const amount = event.features.amount;
      const values = [
        event.transaction_id.slice(0, 16),
        typeof amount === "number" ? `$${amount.toFixed(2)}` : "—",
        event.predicted_fraud ? "Flagged" : "Legitimate",
        event.actual_fraud ? "Fraud" : "Legitimate",
        event.correct ? "Yes" : "No",
        event.model_version
      ];
      values.forEach((value, index) => {
        const cell = document.createElement("td");
        // Treat event data as text, never as executable HTML.
        cell.textContent = value;
        if (index === 0) cell.title = event.transaction_id;
        if (index === 2) cell.className = event.predicted_fraud ? "flagged" : "ordinary";
        row.append(cell);
      });
      const action = document.createElement("td");
      if (event.can_explain) {
        const button = document.createElement("button");
        button.textContent = "Explain";
        button.dataset.explain = "true";
        button.disabled = explaining;
        button.addEventListener("click", () => explain(event));
        action.append(button);
      } else {
        action.textContent = "Missing features";
      }
      row.append(action);
      return row;
    });
    byId("predictions").replaceChildren(...rows);
    byId("empty-state").hidden = rows.length !== 0;
    byId("refresh-status").textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    byId("refresh-status").textContent = `Refresh failed: ${error.message}`;
  }
}

// Schedule after refresh completes so a slow refresh cannot pile up poll loops.
async function poll() {
  await refresh();
  setTimeout(poll, 3000);
}
poll();
