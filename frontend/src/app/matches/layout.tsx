import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default function MatchesLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const configuredMode = process.env.RTGS_MODE;
  const mode = configuredMode === "test" || configuredMode === "replay"
    ? configuredMode
    : process.env.NODE_ENV === "development" ? "test" : "live";
  if (mode === "live") redirect("/");
  return children;
}
