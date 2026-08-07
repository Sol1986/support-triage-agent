# Azure Deployment

## Architecture

The support triage application is deployed using:

- Azure Container Apps
- Azure Container Registry
- Azure Database for PostgreSQL Flexible Server
- Azure Virtual Network
- Azure Private DNS
- User-assigned managed identity
- Azure Container Apps secrets

## Environment

- Region: Canada Central
- Application port: 8000
- Minimum replicas: 0
- Maximum replicas: 2
- Database tier: Burstable Standard_B1ms
- Registry tier: Basic

## Deployment flow

1. Application source is packaged as a Docker image.
2. Azure Container Registry stores the versioned image.
3. Managed identity authorizes Container Apps to pull the image.
4. Azure Container Apps runs the FastAPI and LangGraph application.
5. The application reaches PostgreSQL through the private virtual network.
6. External users reach the API through an Azure-managed HTTPS endpoint.

## Validation

- `/health` confirms application liveness.
- `/ready` confirms database connectivity.
- `POST /tickets` confirms end-to-end ticket processing and storage.
- `GET /tickets/{id}` confirms persistence.

## Security controls

- PostgreSQL uses private networking.
- PostgreSQL public access is disabled.
- Database connections require TLS.
- Credentials are stored as Container Apps secrets.
- Managed identity provides access to ACR.
- Secrets are not committed to Git.
- External application ingress uses HTTPS.

## Current limitations

- Database schema creation still uses SQLAlchemy `create_all`.
- Alembic migrations are not implemented.
- Deployment is currently manual.
- Application authentication is not implemented.
- Centralized metrics and tracing are not implemented.