#!/bin/bash

# Get system info
curl -X GET http://localhost:8000/api/system/info

# Send chat message
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello ARIA","context":{}}'

# List processes
curl -X GET http://localhost:8000/api/system/processes

# List files
curl -X GET "http://localhost:8000/api/files/list?path=/"

# Get ARIA config
curl -X GET http://localhost:8000/api/config/aria
