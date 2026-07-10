import type { PropsWithChildren } from "react";

import { PageSurface } from "@next/components/ui/page-surface";

import { NextThemeBoundary } from "./theme-boundary";

export function NextPublicLayout({ children, framed = true }: PropsWithChildren<{ framed?: boolean }>) {
  return (
    <NextThemeBoundary>
      {framed ? <PageSurface>{children}</PageSurface> : children}
    </NextThemeBoundary>
  );
}
