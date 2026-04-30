import { forwardRef, type ButtonHTMLAttributes } from "react";

type Variant = "default" | "primary" | "danger" | "ghost" | "danger-ghost";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variants: Record<Variant, string> = {
  default:
    "bg-surface-raised border-border-strong text-primary hover:border-accent/30 hover:bg-surface-raised/80",
  primary:
    "bg-gradient-to-b from-accent-strong to-accent-strong/90 text-white border-accent-strong/80 hover:brightness-110",
  danger:
    "bg-gradient-to-b from-danger to-danger/90 text-white border-danger/80 hover:brightness-110",
  ghost:
    "bg-transparent border-transparent text-secondary hover:text-primary hover:bg-surface-raised",
  "danger-ghost":
    "bg-transparent border-danger/30 text-danger hover:bg-danger-soft",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-2.5 text-xs rounded-lg gap-1.5",
  md: "h-9 px-3.5 text-sm rounded-xl gap-2",
  lg: "h-11 px-5 text-sm rounded-xl gap-2.5",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "default", size = "md", className = "", children, ...props }, ref) => (
    <button
      ref={ref}
      className={`inline-flex items-center justify-center font-semibold border transition-all duration-150 cursor-pointer select-none active:scale-[0.97] disabled:opacity-40 disabled:pointer-events-none ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  ),
);
