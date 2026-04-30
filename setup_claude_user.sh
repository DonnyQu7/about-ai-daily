#!/bin/bash

# Claude Code User Configuration Script (Shell Version)
# Automatically configure user authentication and Keychain credentials based on email

# Configuration
PROXY_BASE_URL="https://claudeproxy.corp.astratech.ae"
PROXY_HOST="claudeproxy.corp.astratech.ae"
PROXY_IP="10.44.14.254"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Validate email format
validate_email() {
    local email=$1
    if [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 0
    else
        return 1
    fi
}


# Check network connectivity
check_connectivity() {
    echo "Step 2: Checking network connectivity..."
    
    # Use curl to check connectivity
    local test_url="https://${PROXY_HOST}"
    local http_code=$(curl -s -k --connect-timeout 5 --max-time 10 -o /dev/null -w "%{http_code}" "$test_url" 2>/dev/null)
    
    # Any non-000 HTTP status code indicates successful connection
    if [ -n "$http_code" ] && [ "$http_code" != "000" ]; then
        print_success "  Successfully connected to $PROXY_HOST (HTTP $http_code)"
        return 0
    fi
    
    # If first attempt fails, try other endpoints
    local test_urls=("https://${PROXY_HOST}/health" "https://${PROXY_HOST}/api/users")
    
    for url in "${test_urls[@]}"; do
        http_code=$(curl -s -k --connect-timeout 5 --max-time 10 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
        
        if [ -n "$http_code" ] && [ "$http_code" != "000" ]; then
            print_success "  Successfully connected to $PROXY_HOST (HTTP $http_code)"
            return 0
        fi
    done
    
    # All attempts failed
    print_error "  Unable to connect to $PROXY_HOST"
    echo "  ⚠️ Please check:"
    echo "     1. Company VPN is connected"
    echo "     2. Proxy service is running"
    echo "     3. Firewall settings are not blocking connection"
    echo
    echo "  Tip: Please connect to company VPN and rerun this script"
    return 1
}

# Read credentials from Keychain
get_keychain_credentials() {
    security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null
}

# Write credentials to Keychain
write_to_keychain() {
    local credentials=$1
    
    # Get current system logged-in username
    local username=$(whoami)
    
    # First delete existing password item (if exists)
    security delete-generic-password -s "Claude Code-credentials" 2>/dev/null
    
    # Add new password item using current username
    # -U parameter allows all applications to access this password item
    security add-generic-password \
        -s "Claude Code-credentials" \
        -a "$username" \
        -w "$credentials" \
        -U 2>/dev/null
    
    return $?
}

# Generate 60-digit hex string
generate_user_token() {
    # Use openssl to generate random bytes and convert to hex
    openssl rand -hex 30
}

# Add OAuth token to service
add_oauth_token() {
    local name=$1
    local token_json=$2
    
    # Build request payload
    local payload=$(cat <<EOF
{
    "name": "$name",
    "token": $token_json,
    "force": true
}
EOF
)
    
    # Send request
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "${PROXY_BASE_URL}/api/oauth/tokens")
    
    # Check response
    if echo "$response" | grep -q '"success":true'; then
        print_success "  OAuth token added successfully: $name"
        return 0
    else
        print_error "  Failed to add OAuth token"
        echo "     Response: $response"
        return 1
    fi
}

# Get user list
get_user_list() {
    curl -s "${PROXY_BASE_URL}/api/users"
}

# Check if user exists
check_user_exists() {
    local email=$1
    local users=$(get_user_list)
    
    if echo "$users" | grep -q "\"name\":\"$email\""; then
        # Extract token
        local token=$(echo "$users" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for user in data:
    if user.get('name') == '$email':
        print(user.get('token', ''))
        break
")
        echo "$token"
        return 0
    else
        return 1
    fi
}

# Add user
add_user() {
    local name=$1
    local token=$2
    
    local payload=$(cat <<EOF
{
    "name": "$name",
    "token": "$token"
}
EOF
)
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "${PROXY_BASE_URL}/api/users")
    
    if echo "$response" | grep -q '"name"'; then
        print_success "  User added successfully: $name"
        return 0
    else
        print_error "  Failed to add user"
        echo "     Response: $response"
        return 1
    fi
}

# Create Keychain credentials JSON
create_keychain_credentials() {
    local user_token=$1
    
    cat <<EOF
{"claudeAiOauth":{"accessToken":"${user_token}","refreshToken":"${user_token}","expiresAt":1856184395,"scopes":["user:inference","user:profile"],"subscriptionType":"max"}}
EOF
}

# Check and set environment variable
check_and_set_env_variable() {
    echo "Step 6: Checking environment variable configuration..."
    
    local current_value="${ANTHROPIC_BASE_URL}"
    
    if [ "$current_value" = "$PROXY_BASE_URL" ]; then
        print_success "  ANTHROPIC_BASE_URL is correctly set to: $PROXY_BASE_URL"
        return 0
    fi
    
    if [ -n "$current_value" ]; then
        print_warning "  Current ANTHROPIC_BASE_URL: $current_value"
        echo "  Need to update to: $PROXY_BASE_URL"
    else
        print_info "  ANTHROPIC_BASE_URL not set"
        echo "  Need to set to: $PROXY_BASE_URL"
    fi
    
    # Determine shell configuration file to update
    local shell_name=$(basename "$SHELL")
    local config_file=""
    
    if [[ "$shell_name" == "zsh" ]]; then
        if [ -f "$HOME/.zshrc" ]; then
            config_file="$HOME/.zshrc"
        else
            config_file="$HOME/.zprofile"
        fi
    elif [[ "$shell_name" == "bash" ]]; then
        if [ -f "$HOME/.bashrc" ]; then
            config_file="$HOME/.bashrc"
        elif [ -f "$HOME/.bash_profile" ]; then
            config_file="$HOME/.bash_profile"
        else
            config_file="$HOME/.profile"
        fi
    else
        config_file="$HOME/.profile"
    fi
    
    echo "  Updating $config_file..."
    
    # Environment variable line to add
    local export_line="export ANTHROPIC_BASE_URL=\"$PROXY_BASE_URL\""
    
    # Create file if it doesn't exist
    if [ ! -f "$config_file" ]; then
        touch "$config_file"
    fi
    
    # Check if ANTHROPIC_BASE_URL is already set
    if grep -q "ANTHROPIC_BASE_URL" "$config_file"; then
        # Replace existing setting
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS uses different sed syntax
            sed -i '' "s|^export ANTHROPIC_BASE_URL=.*|$export_line|" "$config_file"
        else
            # Linux
            sed -i "s|^export ANTHROPIC_BASE_URL=.*|$export_line|" "$config_file"
        fi
        print_success "  Environment variable setting updated"
    else
        # Add new setting
        echo "" >> "$config_file"
        echo "# Claude Code Proxy Configuration" >> "$config_file"
        echo "$export_line" >> "$config_file"
        print_success "  Environment variable setting added"
    fi
    
    print_success "  Environment variable added to $config_file"
    print_warning "  Please run the following command to activate the environment variable:"
    echo "     source $config_file"
    echo "  Or reopen the terminal"
    
    # Set environment variable for current shell
    export ANTHROPIC_BASE_URL="$PROXY_BASE_URL"
    print_success "  Environment variable set for current shell"
    
    return 0
}

# Main function
main() {
    echo "============================================================"
    echo "Claude Code User Configuration Script"
    echo "============================================================"
    
    # Step 1: Check email parameter
    if [ $# -ne 1 ]; then
        print_error "Error: Must provide email parameter"
        echo "Usage: $0 <email>"
        echo "Example: $0 user@example.com"
        exit 1
    fi
    
    local email=$1
    
    if ! validate_email "$email"; then
        print_error "Error: Invalid email format: $email"
        exit 1
    fi
    
    echo "📧 Configuring user: $email"
    echo
    
    # Step 2: Check network connectivity
    if ! check_connectivity; then
        print_error "Unable to connect to proxy server, please check VPN connection"
        exit 1
    fi
    
    echo
    
    # Step 3: Read Keychain password item
    echo "Step 3: Checking credentials in Keychain..."
    local credentials=$(get_keychain_credentials)
    
    if [ -n "$credentials" ]; then
        print_success "  Found Claude Code-credentials password item"
        
        # Check if token starts with sk-ant
        local access_token=""
        if echo "$credentials" | grep -q "sk-ant"; then
            # Try to extract access token
            access_token=$(echo "$credentials" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if 'claudeAiOauth' in data:
        token = data['claudeAiOauth'].get('accessToken', '')
    elif 'accessToken' in data:
        token = data.get('accessToken', '')
    elif 'access_token' in data:
        token = data.get('access_token', '')
    else:
        token = ''
    if token.startswith('sk-ant'):
        print(token)
except:
    pass
" 2>/dev/null)
        fi
        
        if [ -n "$access_token" ] && [[ "$access_token" == sk-ant* ]]; then
            echo "  🔑 OAuth access token detected (sk-ant...)"
            echo "  Token prefix: ${access_token:0:20}..."
            
            # Add to OAuth token service
            echo "  Adding OAuth token to service..."
            add_oauth_token "$email" "$credentials"
        else
            print_info "  Current password item content:"
            echo "     ${credentials:0:200}..."
        fi
    else
        print_warning "  Claude Code-credentials password item not found"
    fi
    
    echo
    
    # Step 4: Check and manage user list
    echo "Step 4: Managing user list..."
    
    local user_token=""
    user_token=$(check_user_exists "$email")
    
    if [ -n "$user_token" ]; then
        print_success "  User already exists: $email"
        echo "  Token: ${user_token:0:20}..."
    else
        print_info "  User does not exist, creating new user..."
        user_token=$(generate_user_token)
        echo "  Generated token: ${user_token:0:20}..."
        
        # Add user
        if ! add_user "$email" "$user_token"; then
            print_warning "  Failed to add user, but continuing with Keychain configuration..."
        fi
    fi
    
    echo
    
    # Step 5: Write to Keychain
    echo "Step 5: Updating Keychain credentials..."
    
    if [ -n "$user_token" ]; then
        local new_credentials=$(create_keychain_credentials "$user_token")
        echo "  Generating new credential structure:"
        echo "$new_credentials" | python3 -m json.tool 2>/dev/null | head -10
        
        if write_to_keychain "$new_credentials"; then
            print_success "  Successfully wrote to Keychain"
        else
            print_error "  Failed to write to Keychain"
            exit 1
        fi
    else
        print_error "  Unable to get user token"
        exit 1
    fi
    
    echo
    
    # Step 6: Check and set environment variable
    check_and_set_env_variable
    
    echo
    echo "============================================================"
    print_success "Configuration complete!"
    echo "Claude Code environment has been set up for user $email"
    echo "============================================================"
}

# Run main function
main "$@"