"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Cloud,
  TrendingUp,
  BarChart3,
  AlertCircle,
  BookOpen,
  Target,
  FileText,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Weather", href: "/weather", icon: Cloud },
  { name: "Markets", href: "/markets", icon: TrendingUp },
  { name: "Forecast", href: "/forecast", icon: BarChart3 },
  { name: "Signals & Risk", href: "/signals", icon: AlertCircle },
  { name: "Paper Ledger", href: "/ledger", icon: BookOpen },
  { name: "Calibration", href: "/calibration", icon: Target },
  { name: "Logs", href: "/logs", icon: FileText },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-64 flex-col border-r border-border bg-card">
      {/* Logo / Brand */}
      <div className="flex h-16 items-center border-b border-border px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <TrendingUp className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <div className="text-sm font-semibold text-foreground">Kalshi</div>
            <div className="text-xs text-muted-foreground">KMIA Dashboard</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer Disclaimer */}
      <div className="border-t border-border p-4">
        <div className="rounded-lg bg-destructive/10 p-3">
          <p className="text-xs font-medium text-destructive">
            NO REAL TRADING EXECUTION
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            This dashboard is for paper evaluation only. No orders are placed.
          </p>
        </div>
      </div>
    </aside>
  );
}
