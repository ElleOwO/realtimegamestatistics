"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';

export function XGChart() {
  // Mock xG data over 90 minutes
  const data = [
    { id: 'min-0', minute: 0, home: 0, away: 0 },
    { id: 'min-10', minute: 10, home: 0.15, away: 0.08 },
    { id: 'min-20', minute: 20, home: 0.32, away: 0.21 },
    { id: 'min-30', minute: 30, home: 0.55, away: 0.35 },
    { id: 'min-40', minute: 40, home: 0.78, away: 0.52 },
    { id: 'min-45', minute: 45, home: 0.95, away: 0.64 },
    { id: 'min-50', minute: 50, home: 1.05, away: 0.71 },
    { id: 'min-60', minute: 60, home: 1.28, away: 0.89 },
    { id: 'min-70', minute: 70, home: 1.52, away: 1.12 },
    { id: 'min-80', minute: 80, home: 1.72, away: 1.38 },
    { id: 'min-90', minute: 90, home: 1.84, away: 1.51 },
  ];

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="p-4 md:p-6 pb-2 md:pb-2">
        <CardTitle className="text-base md:text-lg font-semibold">xG Timeline</CardTitle>
      </CardHeader>
      
      <CardContent className="flex-1 min-h-0 p-4 md:p-6 pt-2 md:pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis 
              dataKey="minute" 
              stroke="var(--muted-foreground)"
              tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
            />
            <YAxis 
              stroke="var(--muted-foreground)"
              tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'var(--card)', 
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: 'var(--card-foreground)',
                fontSize: '14px'
              }}
              itemStyle={{ color: 'var(--card-foreground)' }}
            />
            <Legend 
              wrapperStyle={{ color: 'var(--foreground)', fontSize: '13px' }}
              iconType="line"
            />
            <Line 
              key="home-line"
              type="monotone" 
              dataKey="home" 
              stroke="var(--primary)" 
              strokeWidth={2.5}
              name="U of S (Home)"
              dot={{ fill: 'var(--primary)', r: 3 }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
            <Line 
              key="away-line"
              type="monotone" 
              dataKey="away" 
              stroke="var(--destructive)" 
              strokeWidth={2.5}
              name="Calgary (Away)"
              dot={{ fill: 'var(--destructive)', r: 3 }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
