import { redirect } from "next/navigation";

export default function LegacyStatsPage() {
  redirect("/matches");
}
