import type { Component } from "svelte";
import { FileText, Package, Sunrise } from "@lucide/svelte";

export type WatchBlueprint = {
  id: string;
  title: string;
  blurb: string;
  icon: Component;
  name: string;
  focus: (topic: string) => string;
  include: (topic: string) => string;
};

export const WATCH_BLUEPRINTS: WatchBlueprint[] = [
  {
    id: "morning",
    title: "Morning brief",
    blurb: "What changed overnight that matters to this topic.",
    icon: Sunrise,
    name: "Morning brief",
    focus: (t) => `Significant new developments related to ${t} from the last 24 hours.`,
    include: (t) => `Papers, product changes, and eval results related to ${t}.`,
  },
  {
    id: "papers",
    title: "Papers",
    blurb: "Track arXiv and eval results without the hype cycle.",
    icon: FileText,
    name: "Papers",
    focus: (t) => `New papers and benchmarks that change what I believe about ${t}.`,
    include: (t) => `arXiv papers, shared evals, and open-weight releases related to ${t}.`,
  },
  {
    id: "product",
    title: "Product changes",
    blurb: "Shipping updates, APIs, and launches worth a brief.",
    icon: Package,
    name: "Product changes",
    focus: (t) => `Product launches and API changes related to ${t}.`,
    include: (t) => `Official blogs, release notes, and shipping announcements for ${t}.`,
  },
];

export type WatchCadence = "weekdays" | "daily";

export const WATCH_CADENCE_OPTIONS: { value: WatchCadence; label: string }[] = [
  { value: "weekdays", label: "Weekdays" },
  { value: "daily", label: "Daily" },
];

export const WATCH_HOUR_OPTIONS = [7, 8, 9, 10] as const;
