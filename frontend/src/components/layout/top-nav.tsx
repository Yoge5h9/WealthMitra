import { NavLink } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const SURFACES = [
  { to: "/", label: "Command Center" },
  { to: "/app", label: "Customer" },
  { to: "/rm", label: "RM Desk" },
  { to: "/channels", label: "Channels" },
  { to: "/present", label: "Present" },
  { to: "/dev", label: "Dev" },
];

export function TopNav() {
  return (
    <header className="border-b border-structural-800 bg-structural-900">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-8 px-6">
        <div className="flex items-center gap-2 text-structural-50">
          <Sparkles size={20} strokeWidth={1.75} className="text-brand-500" />
          <span className="font-display text-h4 font-semibold tracking-tight">
            WealthMitra
          </span>
        </div>
        <nav className="flex items-center gap-1">
          {SURFACES.map((surface) => (
            <NavLink
              key={surface.to}
              to={surface.to}
              end={surface.to === "/"}
              className={({ isActive }) =>
                cn(
                  "rounded-sm px-3 py-2 text-body-sm font-medium text-structural-200 transition-colors duration-[var(--motion-micro)] ease-out hover:text-structural-50",
                  isActive && "bg-structural-800 text-structural-50"
                )
              }
            >
              {({ isActive }) => (
                <span className="relative">
                  {surface.label}
                  {isActive && (
                    <span className="absolute -bottom-2 left-0 right-0 h-0.5 rounded-full bg-brand-500" />
                  )}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
