import type { PaletteId } from "./theme-prefs";

export interface PaletteMeta {
  id: PaletteId;
  name: string;
  description: string;
  /** Mini preview swatches for the settings card (bg, accent, muted). */
  preview: {
    bg: string;
    accent: string;
    muted: string;
  };
}

export const PALETTES: PaletteMeta[] = [
  {
    id: "nous",
    name: "Nous",
    description: "Soft teal light and dark — the default Nous look.",
    preview: {
      bg: "oklch(0.154 0.011 192.342)",
      accent: "oklch(0.78 0.09 193)",
      muted: "oklch(0.234 0.009 192.841)",
    },
  },
  {
    id: "ember",
    name: "Ember",
    description: "Warm crimson and bronze — forge vibes.",
    preview: {
      bg: "oklch(0.147 0.004 49.314)",
      accent: "oklch(0.645 0.194 41.078)",
      muted: "oklch(0.269 0.006 34.297)",
    },
  },
  {
    id: "mono",
    name: "Mono",
    description: "Clean grayscale — minimal and focused.",
    preview: {
      bg: "oklch(0.141 0.004 285.824)",
      accent: "oklch(0.871 0.005 286.285)",
      muted: "oklch(0.274 0.005 286.033)",
    },
  },
  {
    id: "lilac",
    name: "Lilac",
    description: "Soft magenta and plum — gentle and calm.",
    preview: {
      bg: "oklch(0 0 0)",
      accent: "oklch(0.864 0.076 323.523)",
      muted: "oklch(0.264 0.019 323.456)",
    },
  },
];

export const PALETTE_IDS = PALETTES.map((p) => p.id);

export function paletteMeta(id: PaletteId): PaletteMeta {
  return PALETTES.find((p) => p.id === id) ?? PALETTES[0];
}
