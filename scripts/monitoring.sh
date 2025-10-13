#!/bin/bash

# Check API health
curl -s https://camel.noreika.lt/health | jq .

# Check container status
docker ps --filter name=camel-discussion-api

# Check logs (last 50 lines)
docker logs camel-discussion-api --tail=50

# Check resource usage
docker stats camel-discussion-api --no-stream

# Test WebSocket connection
wscat -c wss://camel.noreika.lt/ws/discussions/test

# Check database size
du -sh /var/lib/docker/volumes/camel_data/_data/
