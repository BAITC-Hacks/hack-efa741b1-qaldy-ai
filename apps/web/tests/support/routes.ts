export const productRoutes = [
  { path: "/", name: "home" },
  { path: "/career-map", name: "career-map" },
  { path: "/quests", name: "quests" },
  { path: "/skills", name: "skills" },
  { path: "/learning", name: "learning" },
  { path: "/opportunities", name: "opportunities" },
  { path: "/team", name: "team" },
  { path: "/library", name: "library" },
  { path: "/ai-navigator", name: "ai-navigator" },
  { path: "/profile", name: "profile" },
] as const;

export type ProductRoute = (typeof productRoutes)[number];
