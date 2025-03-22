#!/bin/bash

set -e

echo "running infra changes"
pushd infra

echo "building ingest image"
docker buildx build --platform linux/arm64 --output=type=docker --provenance=false -f ../ingest/Dockerfile -t 110386608476.dkr.ecr.ap-southeast-2.amazonaws.com/apple_health_ingest ..
echo "pushing ingest image"
docker push 110386608476.dkr.ecr.ap-southeast-2.amazonaws.com/apple_health_ingest:latest

echo "building transforms image"
docker buildx build --platform linux/arm64 --provenance=false --output=type=docker -f ../transforms/Dockerfile -t 110386608476.dkr.ecr.ap-southeast-2.amazonaws.com/apple_health_dbt ..
echo "pushing transforms image"
docker push 110386608476.dkr.ecr.ap-southeast-2.amazonaws.com/apple_health_dbt:latest

popd
