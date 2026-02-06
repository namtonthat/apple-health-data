#!/bin/bash
# Strava OAuth helper script

# Load .env
export $(cat .env | grep -v '^#' | grep STRAVA | xargs)

if [ -z "$STRAVA_CLIENT_ID" ] || [ -z "$STRAVA_CLIENT_SECRET" ]; then
    echo "❌ Missing STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET in .env"
    exit 1
fi

AUTH_URL="https://www.strava.com/oauth/authorize?client_id=${STRAVA_CLIENT_ID}&response_type=code&redirect_uri=http://localhost&scope=read,activity:read_all&approval_prompt=force"

echo "🔐 Strava Authorization"
echo "======================="
echo ""
echo "Opening browser to authorize Strava..."
echo ""
echo "If browser doesn't open, visit this URL:"
echo "$AUTH_URL"
echo ""

# Try to open browser
if command -v open &> /dev/null; then
    open "$AUTH_URL"
elif command -v xdg-open &> /dev/null; then
    xdg-open "$AUTH_URL"
fi

echo "After authorizing, you'll be redirected to a URL like:"
echo "  http://localhost/?state=&code=XXXXXXXX&scope=..."
echo ""
read -p "Paste the 'code' value from the URL: " AUTH_CODE

if [ -z "$AUTH_CODE" ]; then
    echo "❌ No code provided"
    exit 1
fi

echo ""
echo "Exchanging code for tokens..."

RESPONSE=$(curl -s -X POST https://www.strava.com/oauth/token \
    -d client_id="$STRAVA_CLIENT_ID" \
    -d client_secret="$STRAVA_CLIENT_SECRET" \
    -d code="$AUTH_CODE" \
    -d grant_type=authorization_code)

echo ""
echo "Response: $RESPONSE"

# Extract refresh token
REFRESH_TOKEN=$(echo "$RESPONSE" | grep -o '"refresh_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$REFRESH_TOKEN" ]; then
    echo ""
    echo "✅ Success! Update your .env with:"
    echo ""
    echo "STRAVA_REFRESH_TOKEN=$REFRESH_TOKEN"
    echo ""
else
    echo ""
    echo "❌ Failed to get refresh token. Check the response above."
fi
