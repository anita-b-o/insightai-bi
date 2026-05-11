import ContentCopyRoundedIcon from "@mui/icons-material/ContentCopyRounded";
import LinkRoundedIcon from "@mui/icons-material/LinkRounded";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";

import { getApiErrorMessage } from "@next/core/api/errors";
import { useCreateDashboardShareLink, useDashboardShareLinks, useRevokeDashboardShareLink } from "@next/features/share/hooks";
import { toAbsoluteShareUrl } from "@next/features/share/types";

interface ShareDialogProps {
  dashboardId: number;
  dashboardName: string;
  open: boolean;
  onClose: () => void;
}

export function ShareDialog({ dashboardId, dashboardName, open, onClose }: ShareDialogProps) {
  const [expiresAt, setExpiresAt] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const shareLinksQuery = useDashboardShareLinks(dashboardId, open);
  const createLinkMutation = useCreateDashboardShareLink(dashboardId);
  const revokeLinkMutation = useRevokeDashboardShareLink(dashboardId);

  const helperText = useMemo(() => {
    return expiresAt
      ? `This link will expire at ${new Date(expiresAt).toLocaleString()}.`
      : "Leave expiration empty to keep the link active until revoked.";
  }, [expiresAt]);

  async function handleCopy(url: string) {
    await navigator.clipboard.writeText(toAbsoluteShareUrl(url));
    setFeedback("Share link copied.");
  }

  async function handleCreate() {
    try {
      setFeedback(null);
      const response = await createLinkMutation.mutateAsync({
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      });
      await handleCopy(response.share_url);
      setFeedback("Share link created.");
    } catch {
      // surfaced below
    }
  }

  async function handleRevoke(shareId: number) {
    try {
      setFeedback(null);
      await revokeLinkMutation.mutateAsync(shareId);
      setFeedback("Share link revoked.");
    } catch {
      // surfaced below
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Share {dashboardName}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography color="text.secondary">
            Create a read-only link for this dashboard. Viewers will see the shared dashboard without authentication.
          </Typography>

          <TextField
            label="Optional expiration"
            type="datetime-local"
            value={expiresAt}
            onChange={(event) => setExpiresAt(event.target.value)}
            InputLabelProps={{ shrink: true }}
            helperText={helperText}
          />

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
            <Button variant="contained" startIcon={<LinkRoundedIcon />} onClick={() => void handleCreate()} disabled={createLinkMutation.isPending}>
              {createLinkMutation.isPending ? "Creating..." : "Create share link"}
            </Button>
          </Stack>

          {feedback ? <Alert severity="success">{feedback}</Alert> : null}
          {createLinkMutation.isError ? <Alert severity="error">{getApiErrorMessage(createLinkMutation.error, "Could not create dashboard share link")}</Alert> : null}
          {revokeLinkMutation.isError ? <Alert severity="error">{getApiErrorMessage(revokeLinkMutation.error, "Could not revoke dashboard share link")}</Alert> : null}
          {shareLinksQuery.isError ? <Alert severity="error">{getApiErrorMessage(shareLinksQuery.error, "Could not load dashboard share links")}</Alert> : null}

          <Stack spacing={1.5}>
            <Typography variant="subtitle2">Existing links</Typography>
            {shareLinksQuery.isLoading ? (
              <Typography color="text.secondary">Loading share links...</Typography>
            ) : shareLinksQuery.data && shareLinksQuery.data.length > 0 ? (
              shareLinksQuery.data.map((link) => (
                <Stack
                  key={link.id}
                  direction={{ xs: "column", md: "row" }}
                  spacing={1.5}
                  alignItems={{ xs: "stretch", md: "center" }}
                  justifyContent="space-between"
                  sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1.5, p: 1.5 }}
                >
                  <Stack spacing={0.4} sx={{ minWidth: 0 }}>
                    <Typography variant="body2" sx={{ wordBreak: "break-all" }}>
                      {toAbsoluteShareUrl(link.share_url)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Created {new Date(link.created_at).toLocaleString()}
                      {link.expires_at ? ` • Expires ${new Date(link.expires_at).toLocaleString()}` : " • No expiration"}
                      {link.revoked_at ? ` • Revoked ${new Date(link.revoked_at).toLocaleString()}` : ""}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" variant="outlined" startIcon={<ContentCopyRoundedIcon />} onClick={() => void handleCopy(link.share_url)}>
                      Copy
                    </Button>
                    <Button size="small" color="error" variant="outlined" onClick={() => void handleRevoke(link.id)} disabled={revokeLinkMutation.isPending}>
                      Revoke
                    </Button>
                  </Stack>
                </Stack>
              ))
            ) : (
              <Typography color="text.secondary">No share links created yet.</Typography>
            )}
          </Stack>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
