#!/bin/bash
# Setup PostgreSQL Remote Access from Windows to macOS
# Run this script on macOS to allow Windows MCP Server to connect

set -e

echo "🔧 PostgreSQL Remote Access Setup for MCP Server"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Find PostgreSQL data directory
echo "📂 Finding PostgreSQL data directory..."
PGDATA=$(psql -U postgres -t -A -c "SHOW data_directory;" 2>/dev/null || echo "")

if [ -z "$PGDATA" ]; then
    echo -e "${RED}❌ Could not find PostgreSQL data directory${NC}"
    echo "Please ensure PostgreSQL is running and you can connect with: psql -U postgres"
    exit 1
fi

echo -e "${GREEN}✅ Found: $PGDATA${NC}"
echo ""

# 2. Backup current configuration
echo "💾 Backing up current pg_hba.conf..."
sudo cp "$PGDATA/pg_hba.conf" "$PGDATA/pg_hba.conf.backup.$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}✅ Backup created${NC}"
echo ""

# 3. Check if rule already exists
echo "🔍 Checking existing pg_hba.conf rules..."
if sudo grep -q "192.168.0.0/24" "$PGDATA/pg_hba.conf"; then
    echo -e "${YELLOW}⚠️  Network rule already exists${NC}"
else
    echo "➕ Adding network access rule..."
    echo "host    jumpstart_development    postgres    192.168.0.0/24    md5" | sudo tee -a "$PGDATA/pg_hba.conf" > /dev/null
    echo -e "${GREEN}✅ Rule added${NC}"
fi
echo ""

# 4. Check listen_addresses
echo "🔍 Checking postgresql.conf listen_addresses..."
LISTEN_ADDR=$(psql -U postgres -t -A -c "SHOW listen_addresses;" 2>/dev/null || echo "")

if [ "$LISTEN_ADDR" = "*" ] || [ "$LISTEN_ADDR" = "0.0.0.0" ]; then
    echo -e "${GREEN}✅ PostgreSQL is listening on all interfaces${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL is listening only on: $LISTEN_ADDR${NC}"
    echo ""
    echo "To listen on all interfaces, edit postgresql.conf:"
    echo "  sudo nano $PGDATA/postgresql.conf"
    echo "  Find: listen_addresses"
    echo "  Change to: listen_addresses = '*'"
fi
echo ""

# 5. Reload PostgreSQL
echo "🔄 Reloading PostgreSQL configuration..."
if command -v brew &> /dev/null; then
    brew services restart postgresql@14 2>/dev/null || brew services restart postgresql 2>/dev/null || sudo pg_ctl reload -D "$PGDATA"
else
    sudo pg_ctl reload -D "$PGDATA"
fi
echo -e "${GREEN}✅ PostgreSQL reloaded${NC}"
echo ""

# 6. Test connection from localhost
echo "🧪 Testing local connection..."
if psql -U postgres -d jumpstart_development -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Local connection successful${NC}"
else
    echo -e "${RED}❌ Local connection failed${NC}"
fi
echo ""

# 7. Check firewall
echo "🔥 Checking macOS firewall..."
if sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null | grep -q "enabled"; then
    echo -e "${YELLOW}⚠️  Firewall is enabled${NC}"
    echo "You may need to allow PostgreSQL through the firewall:"
    echo "  System Preferences → Security & Privacy → Firewall → Firewall Options"
    echo "  Allow incoming connections for: postgres"
else
    echo -e "${GREEN}✅ Firewall is disabled (connections allowed)${NC}"
fi
echo ""

# 8. Display connection info
echo "=" * 50
echo -e "${GREEN}✅ Configuration Complete!${NC}"
echo "=" * 50
echo ""
echo "📝 Connection Details for Windows MCP Server:"
echo "  Host: 192.168.0.235"
echo "  Port: 5432"
echo "  Database: jumpstart_development"
echo "  Username: postgres"
echo "  Password: aszx12qw"
echo ""
echo "🧪 Test connection from Windows with:"
echo "  psql -h 192.168.0.235 -U postgres -d jumpstart_development"
echo ""
echo "📋 Current pg_hba.conf rules:"
sudo grep -v "^#" "$PGDATA/pg_hba.conf" | grep -v "^$"
echo ""
echo "🔄 To restart MCP Server on Windows (from WSL):"
echo "  python restart_server.py --port 8000"
echo ""
