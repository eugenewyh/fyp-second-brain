import { Browse } from "./Browse";
import { Panel } from "./Panel";

function viewName(): "panel" | "browse" {
  const view = new URLSearchParams(window.location.search).get("view");
  return view === "panel" ? "panel" : "browse";
}

export function App() {
  return viewName() === "panel" ? <Panel /> : <Browse />;
}
