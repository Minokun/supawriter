#!/bin/bash
cd "$(dirname "$0")"
docker-compose up -d
echo "✅ Redis started at localhost:6379"
