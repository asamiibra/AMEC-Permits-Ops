import { ReactNode } from "react";

type AmecLogoProps = {
  size?: "sm" | "md" | "lg";
  className?: string;
  children?: ReactNode;
};

/** The single rendering source for the supplied AMEC corporate identity. */
export function AmecLogo({ size = "md", className = "", children }: AmecLogoProps) {
  return <span className={`amec-logo-frame amec-logo-${size} ${className}`.trim()}>
    <img
      src="/brand/amec-logo@2x.png"
      srcSet="/brand/amec-logo@1x.png 1x, /brand/amec-logo@2x.png 2x, /brand/amec-logo@3x.png 3x"
      alt="AMEC — Art Mark Engineering Consultant"
      className="amec-logo"
      width={600}
      height={285}
      decoding="async"
    />
    {children}
  </span>;
}
