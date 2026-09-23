# Change approval

An approved-change manifest binds ticket, requester, PLC, object, old/new values, time window, allowed states, and optionally hosts/identities.

The provenance engine detects:

- no approved change
- expired approval
- wrong PLC / variable / value / user / workstation / time / process state
- replay / already consumed approval

A successful `ALLOW` consumes the matching approval so the same ticket cannot be replayed.
