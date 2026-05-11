import React from "react";

import { initClientMonitoring, installGlobalClientErrorHandlers } from "./client-error-reporting";
import { AppProviders } from "./providers/app-providers";
import { AppRouter } from "./router";

initClientMonitoring();
installGlobalClientErrorHandlers();

export function NextAppRoot() {
  return (
    <React.StrictMode>
      <AppProviders>
        <AppRouter />
      </AppProviders>
    </React.StrictMode>
  );
}
