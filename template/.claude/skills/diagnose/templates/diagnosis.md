# Diagnosis: <work-id>
violates: working/spec/<member>.md#<anchor> | constraints.md#<id>

## Reproduction
command: <exact>
observed: <output, attached or linked>
attempts (if unreproduced): <list>
status: reproduced | unreproduced

## Evidence
- E1: <what> <link>

## Cause claims
- K1: <statement>
  provenance: observed(E1) | inferred(E1,E2) | hypothesized
  discriminating-test: expected-if-true <..>; expected-if-false <..>; result <..>
  status: confirmed | open | rejected
location: <file>:<function>

## Confirmation test
path: <test file>
commit: <sha>
names-mechanism: <the assertion text or message>

## Rejected hypotheses
- H1: <hypothesis>; ruled out by <evidence>; scope: local | durable; promote-to: area-doc
