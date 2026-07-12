// Score emphasis tiers: ≥85 full accent, 70–84 softened accent, <70 neutral gray.
export const getScoreBand = (score) => {
  if (score >= 85) return "hot";
  if (score >= 70) return "warm";
  return "cool";
};
