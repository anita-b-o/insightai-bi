import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import AutoGraphRoundedIcon from "@mui/icons-material/AutoGraphRounded";
import DatasetRoundedIcon from "@mui/icons-material/DatasetRounded";
import SpaceDashboardRoundedIcon from "@mui/icons-material/SpaceDashboardRounded";
import UploadFileRoundedIcon from "@mui/icons-material/UploadFileRounded";
import RocketLaunchRoundedIcon from "@mui/icons-material/RocketLaunchRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import {
  AppBar,
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
  Toolbar,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useMemo, useState } from "react";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@next/core/auth/session";
import { tokens } from "@next/theme/tokens";

import { NextThemeBoundary } from "./theme-boundary";

const navigationItems = [
  { label: "Datasets", to: "/datasets", icon: <DatasetRoundedIcon /> },
  { label: "Upload", to: "/upload", icon: <UploadFileRoundedIcon /> },
  { label: "Dashboards", to: "/dashboards", icon: <SpaceDashboardRoundedIcon /> },
  { label: "Demo", to: "/demo", icon: <RocketLaunchRoundedIcon /> },
] as const;

const APP_BAR_HEIGHT = 72;

function AppNavigation({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();

  return (
    <Stack spacing={1.25} sx={{ flexShrink: 0 }}>
      <Stack spacing={0.75}>
        <Typography variant="overline" sx={{ color: alpha(tokens.color.fg.inverse, 0.58) }}>
          Workspace
        </Typography>
        <Typography variant="h6" sx={{ color: tokens.color.fg.inverse }}>
          InsightAI BI
        </Typography>
      </Stack>
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
                borderRadius: tokens.radius.sm,
                alignItems: "center",
                color: alpha(tokens.color.fg.inverse, selected ? 1 : 0.78),
                backgroundColor: selected ? alpha(tokens.color.bg.surface, 0.1) : "transparent",
                borderLeft: selected ? `2px solid ${tokens.color.accent.cyan}` : "2px solid transparent",
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
        background: `linear-gradient(180deg, ${tokens.color.bg.inverse} 0%, #122236 100%)`,
        color: tokens.color.fg.inverse,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
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
      <Stack spacing={2} sx={{ flexShrink: 0, mt: "auto" }}>
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
            backgroundColor: alpha(tokens.color.bg.surface, 0.04),
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
        <AppBar position="sticky" color="inherit">
          <Toolbar sx={{ minHeight: APP_BAR_HEIGHT, flexShrink: 0 }}>
            <Stack direction="row" spacing={1.5} alignItems="center" sx={{ flexGrow: 1 }}>
              <IconButton aria-label="Open navigation menu" sx={{ display: { lg: "none" } }} onClick={() => setMobileOpen(true)}>
                <MenuRoundedIcon />
              </IconButton>
              <Box
                sx={{
                  width: 42,
                  height: 42,
                  borderRadius: tokens.radius.sm,
                  background: `linear-gradient(135deg, ${tokens.color.accent.blue} 0%, ${tokens.color.accent.cyan} 100%)`,
                  display: "grid",
                  placeItems: "center",
                  color: tokens.color.fg.inverse,
                }}
              >
                <AutoGraphRoundedIcon fontSize="small" />
              </Box>
              <Box>
                <Typography variant="subtitle1" sx={{ color: tokens.color.fg.inverse }}>
                  InsightAI BI
                </Typography>
                <Typography variant="body2" sx={{ color: alpha(tokens.color.fg.inverse, 0.66) }}>
                  Editorial analytics workspace
                </Typography>
              </Box>
            </Stack>
            <Stack direction="row" spacing={1.25} alignItems="center">
              <Button
                component={RouterLink}
                to="/demo"
                variant="outlined"
                sx={{
                  color: tokens.color.fg.inverse,
                  borderColor: alpha(tokens.color.bg.surface, 0.18),
                  backgroundColor: alpha(tokens.color.bg.surface, 0.04),
                }}
              >
                Open demo
              </Button>
              <Box
                sx={{
                  display: { xs: "none", md: "flex" },
                  alignItems: "center",
                  gap: 1.25,
                  px: 1.25,
                  py: 0.75,
                  borderRadius: tokens.radius.sm,
                  backgroundColor: alpha(tokens.color.bg.surface, 0.08),
                  border: `1px solid ${alpha(tokens.color.bg.surface, 0.08)}`,
                }}
              >
                <Avatar sx={{ width: 30, height: 30, bgcolor: alpha(tokens.color.bg.surface, 0.14), color: tokens.color.fg.inverse }}>
                  {initials}
                </Avatar>
                <Typography variant="body2" sx={{ color: alpha(tokens.color.fg.inverse, 0.76) }}>
                  {user?.full_name}
                </Typography>
              </Box>
            </Stack>
          </Toolbar>
        </AppBar>

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
