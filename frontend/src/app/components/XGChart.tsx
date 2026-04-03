"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { useSocket } from './SocketProvider';
import { Badge } from './ui/badge';

interface XGDataPoint {
  minute: number;
  home: number;
  away: number;
}

export function XGChart() {
  const { data } = useSocket();

  const chartData: XGDataPoint[] = (() => {
    if (data?.xg_timeline && data.xg_timeline.length > 0) {
      return data.xg_timeline.map((entry: any) => ({
        minute: entry.minute ?? 0,
        home: entry.team0_xg ?? 0,
        away: entry.team1_xg ?? 0,
      }));
    }
    return [{ minute: 0, home: 0, away: 0 }];
  })();

  const team0Name = data?.possession.team0_name ?? "Home";
  const team1Name = data?.possession.team1_name ?? "Away";

  return (
    <Card className="h-full flex flex-col border-border bg-card overflow-hidden">
      <CardHeader className="p-6 border-b border-border flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground italic">xG Momentum</CardTitle>
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Cumulative Expected Goals</p>
        </div>
        {data?.xg_timeline && data.xg_timeline.length > 0
          ? <Badge className="bg-green-500/10 text-green-500 border-green-500/20 text-[8px] font-black h-5 uppercase tracking-tighter">Live Feed</Badge>
          : <Badge variant="outline" className="border-border text-muted-foreground font-black uppercase text-[9px]">Awaiting Data</Badge>
        }
      </CardHeader>
      
      <CardContent className="flex-1 min-h-0 p-6">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
            <XAxis 
              dataKey="minute" 
              stroke="var(--muted-foreground)"
              tick={{ fill: 'var(--muted-foreground)', fontSize: 10, fontWeight: 900 }}
              axisLine={{ stroke: 'var(--border)' }}
            />
            <YAxis 
              stroke="var(--muted-foreground)"
              tick={{ fill: 'var(--muted-foreground)', fontSize: 10, fontWeight: 900 }}
              axisLine={{ stroke: 'var(--border)' }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'var(--card)', 
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: 'var(--foreground)',
                fontSize: '12px',
                fontWeight: 900,
                textTransform: 'uppercase'
              }}
              itemStyle={{ fontSize: '12px', fontWeight: 900 }}
            />
            <Legend 
              wrapperStyle={{ color: 'var(--foreground)', fontSize: '11px', fontWeight: 900, textTransform: 'uppercase', paddingTop: '20px' }}
              iconType="circle"
            />
            <Line 
              type="monotone" 
              dataKey="home" 
              stroke="var(--primary)" 
              strokeWidth={2.5}
              name={`${team0Name} (Home)`}
              dot={{ fill: 'var(--primary)', r: 3 }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
            <Line 
              type="monotone" 
              dataKey="away" 
              stroke="var(--secondary)" 
              strokeWidth={2.5}
              name={`${team1Name} (Away)`}
              dot={{ fill: 'var(--secondary)', r: 3 }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
