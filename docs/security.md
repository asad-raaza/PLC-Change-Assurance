# Security of the framework

- Passwords stored with bcrypt; never committed in plaintext
- JWT sessions; RBAC on every mutating route
- Demo secrets are lab fixtures and documented as such
- `.env` is gitignored
- Policy activation requires validation and stores a content hash
- Audit trail is append-oriented with correlation IDs
- CSRF is not applicable to the bearer-token API; cookie sessions are not used
- Enforcement cannot be enabled by operating mode alone
- Learned baselines are not enforceable until a trusted window is approved
- Plugins/adapters are explicit; unsupported vendors are labeled `planned`

Do not deploy the default `SECRET_KEY` outside the lab.
