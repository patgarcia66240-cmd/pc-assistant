#!/bin/bash

echo "Initializing Git repository..."
git init
git add .
git commit -m "chore: Initial commit - PC Assistant MVP"
git branch -M main
echo "✓ Git repository initialized"
echo ""
echo "Next steps:"
echo "1. Add remote: git remote add origin <your-repo-url>"
echo "2. Push: git push -u origin main"
