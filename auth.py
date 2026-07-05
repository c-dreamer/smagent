"""
Top-level CLI for social media authentication.
"""
import argparse
import sys
from youtube.auth import (
    check_token_validity,
    authorize_channel
)


def main():
    parser = argparse.ArgumentParser(description="Social media authentication")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check token validity")
    check_parser.add_argument("--channel", required=True, help="Channel name")
    
    # Authorize command
    auth_parser = subparsers.add_parser("authorize", help="Authorize a new channel")
    auth_parser.add_argument("--channel", required=True, help="Channel name")
    
    args = parser.parse_args()
    
    if args.command == "check":
        result = check_token_validity(args.channel)
        print(f"Channel: {args.channel}")
        print(f"Valid: {result['valid']}")
        print(f"Expired: {result['expired']}")
        if result.get("expires_at"):
            print(f"Expires at: {result['expires_at']}")
        if result.get("has_refresh_token") is not None:
            print(f"Has refresh token: {result['has_refresh_token']}")
        if "error" in result:
            print(f"Error: {result['error']}")
    
    elif args.command == "authorize":
        try:
            credentials = authorize_channel(args.channel)
            print(f"Successfully authorized channel: {args.channel}")
            print("Credentials stored securely.")
        except Exception as e:
            print(f"Authorization failed: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()