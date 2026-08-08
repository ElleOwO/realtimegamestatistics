import { redirect } from "next/navigation";

export default function LegacyPlayersPage() {
  redirect("/matches");
}
