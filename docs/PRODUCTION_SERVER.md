# Production Server Setup

## Recommended Target

- 1 VPS
- Ubuntu 24.04 LTS
- Docker + Docker Compose plugin
- Caddy as reverse proxy
- copy `deploy/compose.prod.env.example` to `deploy/compose.prod.env`
- copy `deploy/backend.prod.env.example` to `deploy/backend.prod.env`

## Recommended Layout

```text
/srv/insightai-bi
  docker-compose.prod.yml
  deploy/
  backend/
  frontend/
  scripts/
  backups/
    db/
    storage/
```

## Recommended Linux User

- create a dedicated user: `deploy`
- add it to the `docker` group
- keep app files under `/srv/insightai-bi`

## Packages

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin curl ufw
sudo systemctl enable --now docker
```

## Firewall

Minimum:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Do not expose PostgreSQL publicly.

## Directories

```bash
sudo mkdir -p /srv/insightai-bi/backups/db
sudo mkdir -p /srv/insightai-bi/backups/storage
sudo chown -R deploy:deploy /srv/insightai-bi
```
