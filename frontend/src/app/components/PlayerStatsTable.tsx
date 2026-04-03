"use client";

import { useMemo, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "./ui/table";
import { ScrollArea } from "./ui/scroll-area";
import { useSocket } from "./SocketProvider";
import { MOCK_PAYLOAD } from "../data/mock";
import { ArrowUpDown, ArrowUp, ArrowDown, Users } from "lucide-react";

type SortKey = "id" | "distance_km" | "top_speed_kmh" | "sprint_count" | "sprint_distance_km" | "pass_accuracy" | "total_xg" | "time_in_attack_zone_s";
type SortDir = "asc" | "desc";

export function PlayerStatsTable() {
  const { data } = useSocket();
  const d = data ?? MOCK_PAYLOAD;
  const [teamFilter, setTeamFilter] = useState<"all" | 0 | 1>("all");
  const [sortKey, setSortKey] = useState<SortKey>("distance_km");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return <ArrowUpDown className="w-3 h-3 inline ml-1 opacity-40" />;
    return sortDir === "asc" ? <ArrowUp className="w-3 h-3 inline ml-1" /> : <ArrowDown className="w-3 h-3 inline ml-1" />;
  };

  const rows = useMemo(() => {
    if (!d?.players) return [];
    let filtered = d.players;
    if (teamFilter !== "all") {
      filtered = filtered.filter((p) => p.team === teamFilter);
    }
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey] ?? 0;
      const bVal = b[sortKey] ?? 0;
      return sortDir === "asc" ? aVal - bVal : bVal - aVal;
    });
  }, [d?.players, teamFilter, sortKey, sortDir]);

  const team0Name = d.possession.team0_name;
  const team1Name = d.possession.team1_name;

  return (
    <Card className="h-full border-border bg-card overflow-hidden flex flex-col">
      <CardHeader className="p-4 md:p-6 border-b border-border flex flex-row items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground italic">Player Stats</CardTitle>
            {data && <Badge className="bg-green-500/10 text-green-500 border-green-500/20 text-[8px] font-black h-5 uppercase tracking-tighter">Live Feed</Badge>}
            {!data && <Badge variant="outline" className="border-border text-muted-foreground font-black uppercase text-[9px]">Mock Data</Badge>}
          </div>
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
            Per-Player Match Statistics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setTeamFilter("all")}
            className={`px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded-full border transition-colors ${
              teamFilter === "all"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-transparent text-muted-foreground border-border hover:text-foreground"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setTeamFilter(0)}
            className={`px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded-full border transition-colors ${
              teamFilter === 0
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-transparent text-muted-foreground border-border hover:text-foreground"
            }`}
          >
            {team0Name}
          </button>
          <button
            onClick={() => setTeamFilter(1)}
            className={`px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded-full border transition-colors ${
              teamFilter === 1
                ? "bg-secondary text-secondary-foreground border-secondary"
                : "bg-transparent text-muted-foreground border-border hover:text-foreground"
            }`}
          >
            {team1Name}
          </button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 overflow-hidden">
        <ScrollArea className="h-full w-full">
          {rows.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-muted-foreground text-sm font-bold uppercase tracking-widest">
              No player data available
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[10px] font-black uppercase tracking-widest">#</TableHead>
                  <TableHead className="text-[10px] font-black uppercase tracking-widest">Team</TableHead>
                  <TableHead
                    className="text-[10px] font-black uppercase tracking-widest cursor-pointer select-none"
                    onClick={() => handleSort("distance_km")}
                  >
                    Dist (km)<SortIcon column="distance_km" />
                  </TableHead>
                  <TableHead
                    className="text-[10px] font-black uppercase tracking-widest cursor-pointer select-none"
                    onClick={() => handleSort("top_speed_kmh")}
                  >
                    Top Speed (km/h)<SortIcon column="top_speed_kmh" />
                  </TableHead>
                  <TableHead
                    className="text-[10px] font-black uppercase tracking-widest cursor-pointer select-none"
                    onClick={() => handleSort("sprint_count")}
                  >
                    Sprints<SortIcon column="sprint_count" />
                  </TableHead>
                  <TableHead
                    className="text-[10px] font-black uppercase tracking-widest cursor-pointer select-none"
                    onClick={() => handleSort("sprint_distance_km")}
                  >
                    Sprint Dist (km)<SortIcon column="sprint_distance_km" />
                  </TableHead>
                  <TableHead
                    className="text-[10px] font-black uppercase tracking-widest cursor-pointer select-none"
                    onClick={() => handleSort("pass_accuracy")}
                  >
                    Pass Acc %<SortIcon column="pass_accuracy" />
                  </TableHead>
                  <TableHead
                    className="text-[10px] font-black uppercase tracking-widest cursor-pointer select-none"
                    onClick={() => handleSort("total_xg")}
                  >
                    xG<SortIcon column="total_xg" />
                  </TableHead>
                  <TableHead
                    className="text-[10px] font-black uppercase tracking-widest cursor-pointer select-none"
                    onClick={() => handleSort("time_in_attack_zone_s")}
                  >
                    Atk Zone (s)<SortIcon column="time_in_attack_zone_s" />
                  </TableHead>
                  <TableHead className="text-[10px] font-black uppercase tracking-widest">Dominant Zone</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((player) => (
                  <TableRow key={`t${player.team}-p${player.id}`}>
                    <TableCell className="font-mono text-xs font-black">{player.id}</TableCell>
                    <TableCell>
                      <span className={`text-[10px] font-black uppercase tracking-widest ${player.team === 0 ? "text-primary" : "text-secondary"}`}>
                        {player.team === 0 ? team0Name : team1Name}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs font-bold">{player.distance_km?.toFixed(2) ?? "—"}</TableCell>
                    <TableCell className="text-xs font-bold">{player.top_speed_kmh?.toFixed(1) ?? "—"}</TableCell>
                    <TableCell className="text-xs font-bold">{player.sprint_count ?? "—"}</TableCell>
                    <TableCell className="text-xs font-bold">{player.sprint_distance_km?.toFixed(2) ?? "—"}</TableCell>
                    <TableCell className="text-xs font-bold">{player.pass_accuracy != null ? `${player.pass_accuracy}%` : "—"}</TableCell>
                    <TableCell className="text-xs font-bold">{player.total_xg?.toFixed(2) ?? "—"}</TableCell>
                    <TableCell className="text-xs font-bold">{player.time_in_attack_zone_s?.toFixed(0) ?? "—"}</TableCell>
                    <TableCell className="text-[10px] font-bold text-muted-foreground uppercase">{player.dominant_zone ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
