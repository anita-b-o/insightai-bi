import type { PropsWithChildren } from "react";

import { PageSurface } from "@next/components/ui/page-surface";

import { NextThemeBoundary } from "./theme-boundary";

export function NextPublicLayout({ children }: PropsWithChildren) {
  return (
    <NextThemeBoundary>
      <PageSurface>{children}</PageSurface>
    </NextThemeBoundary>
  );
}
