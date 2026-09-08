#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PC Assistant - GitHub Setup Script${NC}\n"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Not in pc-assistant directory with git repo${NC}"
    echo "Run this script from the pc-assistant root directory"
    exit 1
fi

# Step 1: Check Git is installed
echo -e "${YELLOW}Step 1: Checking Git installation...${NC}"
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Git is installed${NC}\n"

# Step 2: Check current git status
echo -e "${YELLOW}Step 2: Checking repository status...${NC}"
git_status=$(git status --porcelain)
if [ -z "$git_status" ]; then
    echo -e "${GREEN}✓ Working tree is clean${NC}"
else
    echo -e "${YELLOW}⚠ Uncommitted changes detected:${NC}"
    git status --short
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Step 3: Get GitHub username
echo -e "${YELLOW}Step 3: Configure GitHub credentials${NC}"
read -p "Enter your GitHub username: " github_username

if [ -z "$github_username" ]; then
    echo -e "${RED}❌ Username cannot be empty${NC}"
    exit 1
fi

read -p "Enter your GitHub token (leave empty to use SSH): " github_token
echo ""

# Step 4: Choose authentication method
echo -e "${YELLOW}Step 4: Choose authentication method${NC}"
echo "1. HTTPS (GitHub token)"
echo "2. SSH"
read -p "Choose (1 or 2): " auth_method

if [ "$auth_method" == "1" ]; then
    # HTTPS method
    if [ -z "$github_token" ]; then
        echo -e "${RED}❌ GitHub token is required for HTTPS method${NC}"
        echo "Get a token from: https://github.com/settings/tokens"
        exit 1
    fi
    remote_url="https://${github_username}:${github_token}@github.com/${github_username}/pc-assistant.git"
    auth_type="HTTPS"
elif [ "$auth_method" == "2" ]; then
    # SSH method
    if ! command -v ssh &> /dev/null; then
        echo -e "${RED}❌ SSH is not installed${NC}"
        exit 1
    fi
    
    # Check for SSH key
    if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
        echo -e "${YELLOW}⚠ No SSH key found. Creating one...${NC}"
        ssh-keygen -t ed25519 -C "$github_username@github.com" -f ~/.ssh/id_github -N ""
        eval "$(ssh-agent -s)"
        ssh-add ~/.ssh/id_github
        echo -e "${YELLOW}⚠ Add this public key to GitHub: https://github.com/settings/keys${NC}"
        cat ~/.ssh/id_github.pub
        read -p "Press Enter after adding the key to GitHub..."
    fi
    
    remote_url="git@github.com:${github_username}/pc-assistant.git"
    auth_type="SSH"
else
    echo -e "${RED}❌ Invalid choice${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Using $auth_type authentication${NC}\n"

# Step 5: Set branch to main
echo -e "${YELLOW}Step 5: Configuring branch...${NC}"
git branch -M main
echo -e "${GREEN}✓ Branch set to main${NC}\n"

# Step 6: Check if remote already exists
echo -e "${YELLOW}Step 6: Configuring remote...${NC}"
if git remote | grep -q origin; then
    echo "Removing existing remote..."
    git remote remove origin
fi

git remote add origin "$remote_url"
echo -e "${GREEN}✓ Remote configured${NC}\n"

# Step 7: Test connection
echo -e "${YELLOW}Step 7: Testing connection...${NC}"
if [ "$auth_type" == "SSH" ]; then
    if ssh -T git@github.com 2>&1 | grep -q "$github_username"; then
        echo -e "${GREEN}✓ SSH connection successful${NC}"
    else
        echo -e "${YELLOW}⚠ Could not verify SSH connection${NC}"
        echo "Make sure you've added the key to GitHub"
    fi
else
    # For HTTPS, just try to access the remote
    if git ls-remote --heads "$remote_url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ HTTPS connection successful${NC}"
    else
        echo -e "${RED}❌ Connection failed${NC}"
        echo "Check your credentials and try again"
        exit 1
    fi
fi
echo ""

# Step 8: Summary
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}Configuration Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo "GitHub Username: $github_username"
echo "Authentication: $auth_type"
echo "Remote URL: $(git remote get-url origin | sed 's/https:\/\/.*@/https:\/\//')"
echo -e "${BLUE}═══════════════════════════════════════${NC}\n"

# Step 9: Push to GitHub
read -p "Ready to push to GitHub? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup complete, but not pushed"
    exit 0
fi

echo -e "${YELLOW}Pushing to GitHub...${NC}"
git push -u origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Successfully pushed to GitHub!${NC}\n"
    echo "Your repository is available at:"
    echo -e "${BLUE}https://github.com/${github_username}/pc-assistant${NC}\n"
    echo "Next steps:"
    echo "1. Add a GitHub Actions workflow (optional)"
    echo "2. Set up branch protection rules"
    echo "3. Configure repository settings"
else
    echo -e "${RED}❌ Push failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All done!${NC}"
