#!/bin/bash

# Default to production
ENV=${1:-prod}
BASE_URL="https://ifi.events"

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check for API key in environment
if [ -z "$API_KEY" ]; then
    echo "Error: API_KEY environment variable not set"
    echo "Please set it in your .env file or export it in your shell"
    exit 1
fi

if [ "$ENV" = "local" ]; then
    BASE_URL="http://localhost:5001"
fi

# Function to show usage information
show_usage() {
    echo "Usage: $0 [env] command [options]"
    echo ""
    echo "Environments:"
    echo "  local    Use local development server (localhost:5001)"
    echo "  prod     Use production server (ifi.events) [default]"
    echo ""
    echo "Commands:"
    echo "  fetch [source] [--live] [--detailed]    Fetch events from source (default: all)"
    echo "  list [source] [--detailed]              List events from database"
    echo "  clear [source]                          Clear events from database"
    echo "  show <id|r|n>                          Show specific event (id, random, or next)"
    echo "  deduplicate [source]                    Deduplicate events in database"
    echo ""
    echo "Examples:"
    echo "  $0 local fetch peoply --live            Fetch Peoply events locally"
    echo "  $0 prod list navet --detailed           List Navet events in production"
    echo "  $0 local clear all                      Clear all events locally"
    echo "  $0 prod show n                          Show next event in production"
    echo ""
    echo "Note: Make sure to set the API_KEY environment variable or have it in your .env file"
    exit 1
}

# Check if we have at least a command
if [ -z "$2" ]; then
    show_usage
fi

COMMAND=$2
shift 2  # Remove env and command from arguments

# Common headers for all requests
HEADERS=(
    -H "Content-Type: application/json"
    -H "X-API-Key: $API_KEY"
)

case $COMMAND in
    "fetch")
        SOURCE=${1:-all}
        shift || true
        
        # Parse additional options
        LIVE=false
        DETAILED=false
        while [[ $# -gt 0 ]]; do
            case $1 in
                --live) LIVE=true ;;
                --detailed) DETAILED=true ;;
            esac
            shift
        done
        
        curl -X POST "$BASE_URL/api/events/fetch" \
            "${HEADERS[@]}" \
            -d "{\"source\": \"$SOURCE\", \"live\": $LIVE, \"detailed\": $DETAILED}"
        ;;
        
    "list")
        SOURCE=${1:-all}
        shift || true
        
        # Parse additional options
        DETAILED=false
        while [[ $# -gt 0 ]]; do
            case $1 in
                --detailed) DETAILED=true ;;
            esac
            shift
        done
        
        curl "$BASE_URL/api/events/list?source=$SOURCE&detailed=$DETAILED" \
            "${HEADERS[@]}"
        ;;
        
    "clear")
        SOURCE=${1:-all}
        curl -X POST "$BASE_URL/api/events/clear" \
            "${HEADERS[@]}" \
            -d "{\"source\": \"$SOURCE\"}"
        ;;
        
    "show")
        if [ -z "$1" ]; then
            echo "Error: Event ID required (use number, 'r' for random, or 'n' for next)"
            exit 1
        fi
        curl "$BASE_URL/api/events/show/$1" \
            "${HEADERS[@]}"
        ;;
        
    "deduplicate")
        SOURCE=${1:-all}
        curl -X POST "$BASE_URL/api/events/deduplicate" \
            "${HEADERS[@]}" \
            -d "{\"source\": \"$SOURCE\"}"
        ;;
        
    *)
        echo "Error: Unknown command '$COMMAND'"
        show_usage
        ;;
esac

echo  # Add newline after curl output 