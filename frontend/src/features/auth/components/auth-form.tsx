import { Alert, Box, Button, Stack, TextField } from "@mui/material";
import { useState, type FormEvent } from "react";

import { getApiErrorMessage } from "@next/core/api/errors";

export interface AuthFormValues {
  full_name?: string;
  email: string;
  password: string;
}

interface ValidationErrors {
  full_name?: string;
  email?: string;
  password?: string;
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function NextAuthForm({
  mode,
  onSubmit,
}: {
  mode: "login" | "register";
  onSubmit: (values: AuthFormValues) => Promise<void>;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(values: AuthFormValues): ValidationErrors {
    const errors: ValidationErrors = {};

    if (mode === "register" && (!values.full_name || values.full_name.trim().length < 2)) {
      errors.full_name = "Full name must contain at least 2 characters";
    }

    if (!isValidEmail(values.email.trim())) {
      errors.email = "Enter a valid email address";
    }

    if (values.password.length < 8) {
      errors.password = "Password must contain at least 8 characters";
    }

    return errors;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const values: AuthFormValues = {
      full_name: mode === "register" ? fullName.trim() : undefined,
      email: email.trim(),
      password,
    };
    const errors = validate(values);
    setValidationErrors(errors);
    if (Object.keys(errors).length > 0) {
      setError(Object.values(errors)[0] ?? "Invalid form");
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(values);
    } catch (submissionError: unknown) {
      setError(getApiErrorMessage(submissionError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Stack spacing={2}>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {mode === "register" ? (
          <TextField
            label="Full name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            inputProps={{ minLength: 2, maxLength: 255 }}
            error={Boolean(validationErrors.full_name)}
            helperText={validationErrors.full_name}
            required
          />
        ) : null}
        <TextField
          type="email"
          label="Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={Boolean(validationErrors.email)}
          helperText={validationErrors.email}
          required
        />
        <TextField
          type="password"
          label="Password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          inputProps={{ minLength: 8, maxLength: 128 }}
          error={Boolean(validationErrors.password)}
          helperText={validationErrors.password}
          required
        />
        <Button type="submit" variant="contained" disabled={submitting}>
          {mode === "login" ? "Sign in" : "Create account"}
        </Button>
      </Stack>
    </Box>
  );
}
