#!/bin/bash
# Deploy Chat UI to S3 and invalidate CloudFront
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_UI_DIR="$PROJECT_ROOT/web_ui"

echo "=== Building Chat UI ==="
cd "$WEB_UI_DIR"
npm ci 2>/dev/null || npm install
npm run build

echo "=== Uploading to S3 ==="
BUCKET="${1:-}"
if [ -z "$BUCKET" ]; then
  echo "Usage: $0 <s3-bucket-name> [cloudfront-distribution-id]"
  echo "Get bucket from: terraform -chdir=$PROJECT_ROOT/terraform output chat_ui_bucket_name"
  exit 1
fi

aws s3 sync dist/ "s3://$BUCKET/" --delete

echo "=== Invalidating CloudFront ==="
DIST_ID="${2:-}"
if [ -n "$DIST_ID" ]; then
  aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*"
  echo "Invalidation submitted."
else
  echo "To invalidate cache, run:"
  echo "  aws cloudfront create-invalidation --distribution-id <cf-id> --paths '/*'"
  echo "Get distribution ID from: terraform -chdir=terraform output chat_ui_cloudfront_id"
fi

echo "=== Done ==="
echo "Chat UI URL: https://$(aws cloudfront list-distributions --query "DistributionList.Items[?Origins.Items[?DomainName=='$BUCKET.s3.${AWS_REGION:-us-east-1}.amazonaws.com']].DomainName | [0]" --output text 2>/dev/null || echo 'check CloudFront console')"
