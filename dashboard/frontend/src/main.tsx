import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { initTheme } from "./lib/theme";
import "./styles.css";

// Applied before the first paint so the page never flashes dark-then-light
// (or vice versa) on load.
initTheme();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
