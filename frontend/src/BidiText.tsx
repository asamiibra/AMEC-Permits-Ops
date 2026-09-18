import { createElement, type HTMLAttributes, type ReactNode } from "react";

type ContentElement = "b" | "del" | "div" | "h2" | "h3" | "h4" | "h5" | "ins" | "p" | "small" | "span" | "strong";

export type BidiTextProps = HTMLAttributes<HTMLElement> & {
  as?: ContentElement;
  children: ReactNode;
};

/** Dynamic business content follows the text's own Unicode base direction. */
export function BidiText({ as = "span", className, children, ...props }: BidiTextProps) {
  return createElement(as, { ...props, dir: "auto", className: ["bidi-content", className].filter(Boolean).join(" ") }, children);
}

/** References, hashes, filenames and paths stay isolated in their logical order. */
export function BidiCode({ as = "span", className, children, ...props }: BidiTextProps) {
  return createElement(as, { ...props, dir: "ltr", className: ["bidi-code", className].filter(Boolean).join(" ") }, children);
}
