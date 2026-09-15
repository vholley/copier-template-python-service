# shared

Living specification for `libs/shared`, the library every app imports. Each
statement below is backed by a test in `libs/shared/tests/` marked
`spec("shared.md#<anchor>")`.

## Settings come from the environment

A settings field reads the environment variable of the same name, matched
without regard to case, and an explicit value there overrides the field's
default. A variable naming no field is ignored rather than rejected, so an
application's environment may carry more than one app's configuration.

## Settings fall back to their declared defaults

A field with a default needs no environment variable. A field without one is
required, and constructing the settings object without it fails.

## Logging is configured for its destination

In Cloud Run, detected by the `K_SERVICE` environment variable, logs are JSON on
stdout, which is what Cloud Logging ingests. Everywhere else they are
human-readable on stderr, which keeps them out of a program's own output.

## The log level is a threshold

`configure_logging(level=...)` drops every message below the level it names and
keeps every message at or above it.
