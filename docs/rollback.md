# Emergency Rollback Procedure

## Quick Rollback (Previous Version)

```bash
# 1. Stop current version
docker-compose -f docker-compose.production.yml down

# 2. Checkout previous commit
git checkout HEAD~1

# 3. Rebuild and deploy
./scripts/deploy.sh
```

## Rollback to Specific Version

```bash
# 1. Stop current
docker-compose -f docker-compose.production.yml down

# 2. Checkout specific commit
git checkout <commit-hash>

# 3. Deploy
./scripts/deploy.sh
```

## Restore Database Backup

```bash
# 1. Stop container
docker-compose -f docker-compose.production.yml down

# 2. Restore database
cp /opt/backups/camel-discussion/discussions_TIMESTAMP.db \
   /var/lib/docker/volumes/camel_data/_data/discussions.db

# 3. Start container
docker-compose -f docker-compose.production.yml up -d
```
