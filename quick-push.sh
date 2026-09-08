#!/bin/bash

# Quick push to GitHub (if already configured)

echo "📤 Quick Push to GitHub"
echo "====================="

# Check if remote is configured
if ! git remote | grep -q origin; then
    echo "❌ No remote configured!"
    echo "Run: ./setup-github.sh first"
    exit 1
fi

echo "Remote URL: $(git remote get-url origin)"
echo ""

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Uncommitted changes detected:"
    git status --short
    echo ""
    read -p "Stage all changes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        read -p "Commit message: " message
        if [ -z "$message" ]; then
            message="chore: update"
        fi
        git commit -m "$message"
    fi
fi

echo ""
echo "📤 Pushing to GitHub..."
git push

if [ $? -eq 0 ]; then
    echo "✅ Push successful!"
    echo ""
    remote_url=$(git remote get-url origin)
    repo=$(echo $remote_url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')
    echo "View at: https://github.com/$repo"
else
    echo "❌ Push failed!"
    exit 1
fi
