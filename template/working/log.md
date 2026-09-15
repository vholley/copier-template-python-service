# Issue log

Append-only. One entry per thing that went wrong: a block that fired wrongly, a
bounce, an escalation, a defect that escaped, a check that found a design
defect, a test amendment. Each entry says what happened, which written
definition was missing or wrong, and the fix. Status moves from open to closed
only. `make log` adds an entry; the weekly audit reports open ones.

An entry closes when its fix has landed and nothing remains, with
`make log-close ID=L-3`. Recording a fix does not close it: a fix written at the
moment the issue is raised has not been reviewed, merged, or shown to work.
Follow-up work is its own entry, not a reason to hold this one open.
