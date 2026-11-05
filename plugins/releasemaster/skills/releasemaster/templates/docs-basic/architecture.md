# Architecture

## Overview
{{2–3 paragraphs.}}

```mermaid
flowchart LR
  web[Web app] -->|HTTPS/REST| api[API]
  mobile[Mobile app] -->|HTTPS/REST| api
  api --> db[(Database)]
```

## Components
| Component | Responsibility | Tech | Repo |
|---|---|---|---|

## Key flows
### {{Flow name}}

## Data
## Cross-cutting concerns
Authentication · logging · error handling · localization

## Key decisions
{{Or link to adr/ at full level.}}
