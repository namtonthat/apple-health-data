#!/bin/bash

set -e

echo "running infra changes"
pushd infra

echo "building ingest image"
docker buildx build --platform linux/arm64 --output=type=docker --provenance=false -f ../ingest/Dockerfile -t 110386608476.dkr.ecr.ap-southeast-2.amazonaws.com/lambda_ingest_repo ..
echo "pushing ingest image"
docker push 110386608476.dkr.ecr.ap-southeast-2.amazonaws.com/lambda_ingest_repo:latest

echo "building transforms image"
docker buildx build --platform linux/arm64 --provenance=false --output=type=docker -f ../transforms/Dockerfile -t 110386608476.dkr.ecr.ap-southeast-2.amazonaws.com/lambda_dbt_repo ..
echo "pushing transforms image"
docker push 110386608476.dkr.ecr.ap-southeast-2.amazonaws.com/lambda_dbt_repo:latest

popd
