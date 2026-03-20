interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
}

export function KPICard({ title, value, subtitle }: KPICardProps) {
  return (
    <div className="bg-[#1a1a1a] rounded-xl md:rounded-2xl p-4 md:p-6 border border-[#2a2a2a] flex flex-col justify-center h-full">
      <div className="text-gray-400 text-xs md:text-sm mb-1 md:mb-2">{title}</div>
      <div className="text-white text-3xl md:text-4xl font-bold mb-0.5 md:mb-1">{value}</div>
      {subtitle && <div className="text-[#0B6A41] text-xs md:text-sm font-medium">{subtitle}</div>}
    </div>
  );
}
