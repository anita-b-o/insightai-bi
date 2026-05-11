import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import PushPinIcon from "@mui/icons-material/PushPin";
import PushPinOutlinedIcon from "@mui/icons-material/PushPinOutlined";
import {
  Alert,
  CircularProgress,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useEffect, useState } from "react";

import { getApiErrorMessage } from "@next/core/api/errors";
import { tokens } from "@next/theme/tokens";

import type { AIQueryHistorySummary } from "../types";
import { formatQueryTitle } from "../types";

function formatTimestamp(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function QueryHistoryPanel({
  entries,
  selectedQueryId,
  isLoading,
  error,
  onSelect,
  onToggleFavorite,
  onRename,
  onDelete,
}: {
  entries: AIQueryHistorySummary[];
  selectedQueryId: number | null;
  isLoading: boolean;
  error: string | null;
  onSelect: (queryId: number) => void;
  onToggleFavorite: (entry: AIQueryHistorySummary) => Promise<void>;
  onRename: (entry: AIQueryHistorySummary, title: string | null) => Promise<void>;
  onDelete: (entry: AIQueryHistorySummary) => Promise<void>;
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (editingId && !entries.some((entry) => entry.id === editingId)) {
      setEditingId(null);
      setDraftTitle("");
    }
  }, [editingId, entries]);

  return (
    <Stack spacing={1.5} sx={{ minWidth: 0 }}>
      <Stack spacing={0.65}>
        <Typography variant="overline" color="text.secondary">
          Query history
        </Typography>
        <Typography variant="h6">Saved analysis rail</Typography>
        <Typography variant="body2" color="text.secondary">
          Reopen prior answers, mark favorites, rename saved questions, and keep context close to the composer.
        </Typography>
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {actionError ? <Alert severity="error">{actionError}</Alert> : null}

      {isLoading ? (
        <Stack alignItems="center" py={4}>
          <CircularProgress size={24} />
        </Stack>
      ) : null}

      {!isLoading && !entries.length ? (
        <Typography color="text.secondary">No saved AI queries yet for this dataset.</Typography>
      ) : null}

      {!isLoading && entries.length ? (
        <List
          disablePadding
          sx={{
            display: "grid",
            gap: 0,
            borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.38)}`,
          }}
        >
          {entries.map((entry, index) => {
            const selected = selectedQueryId === entry.id;
            return (
              <Stack key={entry.id} spacing={0.75}>
                <Stack direction="row" spacing={0.75} alignItems="flex-start">
                  <ListItemButton
                    selected={selected}
                    onClick={() => onSelect(entry.id)}
                    sx={{
                      flex: 1,
                      minWidth: 0,
                      alignItems: "flex-start",
                      px: 1.25,
                      py: 1,
                      borderRadius: 0,
                      borderLeft: selected ? `2px solid ${tokens.color.accent.blue}` : "2px solid transparent",
                      backgroundColor: selected ? alpha(tokens.color.bg.accentWash, 0.34) : "transparent",
                    }}
                  >
                    {editingId === entry.id ? (
                      <Stack spacing={0.75} width="100%">
                        <TextField
                          size="small"
                          value={draftTitle}
                          onChange={(event) => setDraftTitle(event.target.value.slice(0, 120))}
                          placeholder="Custom title"
                          autoFocus
                          onClick={(event) => event.stopPropagation()}
                        />
                        <Stack direction="row" spacing={0.25}>
                          <IconButton
                            size="small"
                            aria-label="Save title"
                            onClick={async (event) => {
                              event.stopPropagation();
                              try {
                                setActionError(null);
                                await onRename(entry, draftTitle.trim() || null);
                                setEditingId(null);
                                setDraftTitle("");
                              } catch (renameError: unknown) {
                                setActionError(getApiErrorMessage(renameError, "Could not rename query"));
                              }
                            }}
                          >
                            <CheckIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            aria-label="Cancel rename"
                            onClick={(event) => {
                              event.stopPropagation();
                              setEditingId(null);
                              setDraftTitle("");
                            }}
                          >
                            <CloseIcon fontSize="small" />
                          </IconButton>
                        </Stack>
                      </Stack>
                    ) : (
                      <ListItemText
                        primary={formatQueryTitle(entry)}
                        secondary={`${formatTimestamp(entry.created_at)}${entry.execution_time_ms ? ` • ${entry.execution_time_ms} ms` : ""}`}
                        primaryTypographyProps={{
                          sx: {
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                            color: tokens.color.fg.primary,
                            fontWeight: selected ? 700 : 500,
                          },
                        }}
                      />
                    )}
                  </ListItemButton>

                  {editingId !== entry.id ? (
                    <Stack direction="row" spacing={0.15} mt={0.15}>
                      <Tooltip title={entry.is_favorite ? "Remove favorite" : "Mark favorite"}>
                        <IconButton
                          size="small"
                          aria-label={entry.is_favorite ? "Remove favorite" : "Mark favorite"}
                          onClick={async (event) => {
                            event.stopPropagation();
                            try {
                              setActionError(null);
                              await onToggleFavorite(entry);
                            } catch (favoriteError: unknown) {
                              setActionError(getApiErrorMessage(favoriteError, "Could not update favorite"));
                            }
                          }}
                        >
                          {entry.is_favorite ? <PushPinIcon fontSize="small" /> : <PushPinOutlinedIcon fontSize="small" />}
                        </IconButton>
                      </Tooltip>

                      <Tooltip title="Rename">
                        <IconButton
                          size="small"
                          aria-label="Rename"
                          onClick={(event) => {
                            event.stopPropagation();
                            setActionError(null);
                            setEditingId(entry.id);
                            setDraftTitle(entry.title ?? "");
                          }}
                        >
                          <EditOutlinedIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>

                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          aria-label="Delete"
                          onClick={async (event) => {
                            event.stopPropagation();
                            try {
                              setActionError(null);
                              await onDelete(entry);
                            } catch (deleteError: unknown) {
                              setActionError(getApiErrorMessage(deleteError, "Could not delete query"));
                            }
                          }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  ) : null}
                </Stack>

                {index < entries.length - 1 ? <Divider /> : null}
              </Stack>
            );
          })}
        </List>
      ) : null}
    </Stack>
  );
}
