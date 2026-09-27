import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import DatasetRoundedIcon from "@mui/icons-material/DatasetRounded";
import SpaceDashboardRoundedIcon from "@mui/icons-material/SpaceDashboardRounded";
import UploadFileRoundedIcon from "@mui/icons-material/UploadFileRounded";
import RocketLaunchRoundedIcon from "@mui/icons-material/RocketLaunchRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import {
  Avatar,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useMemo, useState } from "react";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";

import { GeoPattern } from "@next/components/brand/geo-pattern";
import { InsightBrand } from "@next/components/brand/insight-brand";
import { useAuth } from "@next/core/auth/session";
import { tokens } from "@next/theme/tokens";

import { NextThemeBoundary } from "./theme-boundary";

const navigationItems = [
  { label: "Datasets", to: "/datasets", icon: <DatasetRoundedIcon /> },
  { label: "Upload", to: "/upload", icon: <UploadFileRoundedIcon /> },
  { label: "Dashboards", to: "/dashboards", icon: <SpaceDashboardRoundedIcon /> },
  { label: "Demo", to: "/demo", icon: <RocketLaunchRoundedIcon /> },
] as const;

function AppNavigation({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();

  return (
    <Stack spacing={1.25} sx={{ flexShrink: 0 }}>
      <InsightBrand tone="inverse" />
      <List disablePadding sx={{ display: "grid", gap: 0.5 }}>
        {navigationItems.map((item) => {
          const selected = location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
          return (
            <ListItemButton
              key={item.to}
              component={RouterLink}
              to={item.to}
              selected={selected}
              onClick={onNavigate}
              sx={{
                borderRadius: tokens.radius.xs,
                alignItems: "center",
                color: alpha(tokens.color.fg.inverse, selected ? 1 : 0.78),
                backgroundColor: selected ? alpha(tokens.color.bg.surface, 0.12) : "transparent",
                borderLeft: selected ? `3px solid ${tokens.color.accent.signal}` : "3px solid transparent",
                "&:hover": {
                  backgroundColor: alpha(tokens.color.bg.surface, 0.1),
                },
                "& .MuiListItemIcon-root": {
                  color: alpha(tokens.color.fg.inverse, selected ? 1 : 0.72),
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 38 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Stack>
  );
}

export function NextAppShell() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const initials = useMemo(() => {
    if (!user?.full_name) {
      return "IA";
    }
    return user.full_name
      .split(" ")
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("");
  }, [user?.full_name]);

  const sidebar = (
    <Stack
      sx={{
        height: "100%",
        p: 2,
        position: "relative",
        background: `linear-gradient(180deg, ${tokens.color.bg.inverse} 0%, #064232 100%)`,
        color: tokens.color.fg.inverse,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <GeoPattern inverted density="quiet" sx={{ opacity: 0.09 }} />
      <Box
        sx={{
          position: "relative",
          zIndex: 1,
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          pr: 0.5,
          mr: -0.5,
        }}
      >
        <Stack spacing={2} sx={{ flexShrink: 0 }}>
          <AppNavigation onNavigate={() => setMobileOpen(false)} />
        </Stack>
      </Box>
      <Stack spacing={2} sx={{ position: "relative", zIndex: 1, flexShrink: 0, mt: "auto" }}>
        <Divider />
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Avatar sx={{ bgcolor: alpha(tokens.color.bg.surface, 0.14), color: tokens.color.fg.inverse }}>{initials}</Avatar>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle2" noWrap>
              {user?.full_name ?? "Workspace user"}
            </Typography>
            <Typography variant="body2" sx={{ color: alpha(tokens.color.fg.inverse, 0.66) }} noWrap>
              {user?.email ?? "No email"}
            </Typography>
          </Box>
        </Stack>
        <Button
          variant="outlined"
          startIcon={<LogoutRoundedIcon />}
          onClick={logout}
          sx={{
            color: tokens.color.fg.inverse,
            borderColor: alpha(tokens.color.bg.surface, 0.18),
            backgroundColor: "transparent",
          }}
        >
          Logout
        </Button>
      </Stack>
    </Stack>
  );

  return (
    <NextThemeBoundary>
      <Box
        sx={{
          minHeight: "100dvh",
          height: "100dvh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          backgroundColor: tokens.color.bg.canvas,
        }}
      >
        <Box
          component="header"
          sx={{
            display: { xs: "flex", lg: "none" },
            flexShrink: 0,
            height: 56,
            alignItems: "center",
            px: 1.25,
            backgroundColor: tokens.color.bg.canvas,
            borderBottom: `1px solid ${tokens.color.border.subtle}`,
          }}
        >
          <IconButton aria-label="Open navigation menu" onClick={() => setMobileOpen(true)}>
            <MenuRoundedIcon />
          </IconButton>
        </Box>

        <Drawer
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          sx={{
            display: { lg: "none" },
            "& .MuiDrawer-paper": {
              width: 280,
              height: "100dvh",
              overflow: "hidden",
            },
          }}
        >
          {sidebar}
        </Drawer>

        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "280px minmax(0, 1fr)" },
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              display: { xs: "none", lg: "block" },
              borderRight: `1px solid ${tokens.color.border.subtle}`,
              height: "100%",
              overflow: "hidden",
            }}
          >
            {sidebar}
          </Box>
          <Box
            sx={{
              minWidth: 0,
              minHeight: 0,
              overflowY: "auto",
            }}
          >
            <Box sx={{ width: "100%", maxWidth: tokens.layout.appMaxWidth, mx: "auto" }}>
              <Outlet />
            </Box>
          </Box>
        </Box>
      </Box>
    </NextThemeBoundary>
  );
}
