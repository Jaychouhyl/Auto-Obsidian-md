export type AppEdition = "community" | "commercial" | "personal";

function normalizeEdition(value: unknown): AppEdition {
  const text = String(value ?? "community").toLowerCase();
  if (text === "commercial" || text === "personal") return text;
  return "community";
}

export const APP_EDITION: AppEdition = normalizeEdition(import.meta.env.VITE_APP_EDITION);
export const isCommercialEdition = APP_EDITION === "commercial";
export const isPersonalEdition = APP_EDITION === "personal";
export const isPrivateEdition = isCommercialEdition || isPersonalEdition;

export const appBrandName = isPrivateEdition ? "Knowledge Studio" : "Ingest Studio";
export const appBrandSubtitle = isPrivateEdition ? "personal knowledge workspace" : "local knowledge pipeline";

export function editionShellClass(): string {
  if (isCommercialEdition) return "commercial-edition";
  if (isPersonalEdition) return "personal-edition";
  return "community-edition";
}

export function editionDisplayName(): string {
  if (isCommercialEdition) return "商业版";
  if (isPersonalEdition) return "个人版";
  return "开源完整版";
}

export function editionInstallShape(): string {
  if (isCommercialEdition) return "商业分发版";
  if (isPersonalEdition) return "本机个人版";
  return "开源完整版";
}

export function editionVersionStrategy(): string {
  return isPrivateEdition ? "固定交付，本机使用" : "走 GitHub Release";
}
