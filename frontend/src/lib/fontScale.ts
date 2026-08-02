export type FontScale = "sm" | "base" | "lg";

// CSS zoom applied to a section's content area for the CBT font-size control.
export const FONT_SCALE_ZOOM: Record<FontScale, number> = {
  sm: 0.9,
  base: 1,
  lg: 1.15,
};

export const SCALE_ORDER: FontScale[] = ["sm", "base", "lg"];
