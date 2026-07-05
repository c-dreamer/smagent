"""
YouTube OAuth handler with per-channel token management.
"""
import os
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# OAuth scopes for YouTube API
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

# Configuration
CONFIG_DIR = Path.home() / ".config" / "social-media"
TOKEN_DIR = CONFIG_DIR
KEY_FILE = CONFIG_DIR / ".token_key"


def _get_encryption_key() -> bytes:
    """Get or create encryption key for token storage."""
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Try to get key from environment variable first
    key_env = os.environ.get("SOCIAL_MEDIA_TOKEN_KEY")
    if key_env:
        # Ensure it's 32 url-safe base64-encoded bytes
        key = base64.urlsafe_b64encode(key_env.encode()[:32].ljust(32, b'\0'))
        return key
    
    # Try to load existing key
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    
    # Generate new key
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    return key


def _encrypt_data(data: str) -> bytes:
    """Encrypt data using Fernet symmetric encryption."""
    f = Fernet(_get_encryption_key())
    return f.encrypt(data.encode())


def _decrypt_data(encrypted_data: bytes) -> str:
    """Decrypt data using Fernet symmetric encryption."""
    f = Fernet(_get_encryption_key())
    return f.decrypt(encrypted_data).decode()


def _get_token_path(channel_name: str) -> Path:
    """Get the token file path for a channel."""
    return TOKEN_DIR / f"{channel_name}_token.json"


def store_credentials(channel_name: str, credentials: Dict[str, Any]) -> None:
    """
    Store encrypted credentials for a channel.
    
    Args:
        channel_name: Name of the channel
        credentials: Dictionary containing token information
    """
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    token_path = _get_token_path(channel_name)
    
    # Encrypt the credentials JSON
    credentials_json = json.dumps(credentials)
    encrypted_data = _encrypt_data(credentials_json)
    
    # Write encrypted data to file
    token_path.write_bytes(encrypted_data)
    # Set restrictive permissions (owner read/write only)
    token_path.chmod(0o600)


def get_credentials(channel_name: str) -> Optional[Credentials]:
    """
    Load and decrypt credentials for a channel.
    
    Args:
        channel_name: Name of the channel
        
    Returns:
        Credentials object if token exists and is valid, None otherwise
    """
    token_path = _get_token_path(channel_name)
    if not token_path.exists():
        return None
    
    try:
        encrypted_data = token_path.read_bytes()
        credentials_json = _decrypt_data(encrypted_data)
        credentials_dict = json.loads(credentials_json)
        
        # Create Credentials object
        credentials = Credentials.from_authorized_user_info(credentials_dict, SCOPES)
        
        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            # Save refreshed credentials
            store_credentials(channel_name, {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes
            })
        
        return credentials
    except Exception as e:
        # If any error occurs (decryption, validation, etc.), return None
        return None


def refresh_if_expired(credentials: Credentials) -> Credentials:
    """
    Refresh credentials if expired.
    
    Args:
        credentials: Credentials object to check and refresh
        
    Returns:
        Refreshed credentials
    """
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    return credentials


def get_authenticated_service(channel_name: str) -> Any:
    """
    Get an authenticated YouTube API service object for a channel.
    
    Args:
        channel_name: Name of the channel
        
    Returns:
        YouTube API service object
        
    Raises:
        ValueError: If credentials cannot be loaded for the channel
    """
    credentials = get_credentials(channel_name)
    if not credentials:
        raise ValueError(f"No valid credentials found for channel: {channel_name}")
    
    return build("youtube", "v3", credentials=credentials)


def _generate_auth_url(channel_name: str) -> tuple[str, str, str]:
    """
    Generate the authorization URL and save the flow state for later code exchange.
    Returns (auth_url, state, code_verifier).
    """
    import json as _json
    import base64 as _b64
    import secrets as _secrets
    
    client_secrets_path = Path(__file__).parent / "client_secrets.json"
    if not client_secrets_path.exists():
        raise FileNotFoundError(
            f"client_secrets.json not found at {client_secrets_path}. "
            "Please download it from Google Cloud Console and place it in the youtube directory."
        )
    
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path),
        SCOPES,
        redirect_uri="http://localhost:4200/oauth2/callback/youtube",
    )
    
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    
    # Save flow state to file for later use
    flow_state = {
        "channel": channel_name,
        "state": state,
        "client_id": flow.client_config["client_id"],
        "client_secret": flow.client_config["client_secret"],
        "scopes": flow.oauth2session.scope,
        "redirect_uri": "http://localhost:4200/oauth2/callback/youtube",
        "code_verifier": getattr(flow, "code_verifier", None),
    }
    state_file = CONFIG_DIR / f"{channel_name}_oauth_state.json"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    state_file.write_text(_json.dumps(flow_state, indent=2))
    state_file.chmod(0o600)
    
    return auth_url, state


def exchange_code(channel_name: str, authorization_code: str) -> Dict[str, Any]:
    """
    Exchange an authorization code for credentials and store them.
    
    Args:
        channel_name: Name of the channel
        authorization_code: The OAuth authorization code
        
    Returns:
        Dictionary containing the credentials information
    """
    import json as _json
    
    state_file = CONFIG_DIR / f"{channel_name}_oauth_state.json"
    if not state_file.exists():
        raise FileNotFoundError(
            f"No OAuth state found for channel {channel_name}. "
            "Run 'authorize' first to generate the authorization URL."
        )
    
    flow_state = _json.loads(state_file.read_text())
    
    from google.oauth2.credentials import Credentials as _Creds
    from google.auth.transport.requests import Request as _Req
    import requests as _requests
    
    # Exchange code manually (including PKCE code_verifier)
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": authorization_code,
        "client_id": flow_state["client_id"],
        "client_secret": flow_state["client_secret"],
        "redirect_uri": flow_state["redirect_uri"],
        "grant_type": "authorization_code",
    }
    if flow_state.get("code_verifier"):
        data["code_verifier"] = flow_state["code_verifier"]
    
    resp = _requests.post(token_url, data=data)
    if resp.status_code != 200:
        raise RuntimeError(f"Token exchange failed: {resp.status_code} {resp.text}")
    
    token_data = resp.json()
    credentials_dict = {
        "token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": token_url,
        "client_id": flow_state["client_id"],
        "client_secret": flow_state["client_secret"],
        "scopes": flow_state["scopes"],
    }
    
    store_credentials(channel_name, credentials_dict)
    
    # Clean up state file
    state_file.unlink(missing_ok=True)
    
    print(f"Token stored for channel: {channel_name}")
    return credentials_dict


def authorize_channel(channel_name: str) -> Dict[str, Any]:
    """
    Step 1: Generate the OAuth authorization URL for the user to visit.
    Returns dict with auth_url.
    """
    auth_url, state = _generate_auth_url(channel_name)
    
    print(f"\n{'='*70}")
    print("OPEN THIS URL IN YOUR BROWSER (log in as calebka20@gmail.com):")
    print(f"{'='*70}")
    print(auth_url)
    print(f"\n{'='*70}")
    print("After authorizing, you'll be redirected to localhost:4200.")
    print("The page will fail to load — THAT'S EXPECTED.")
    print("Copy the FAILED URL from your browser's address bar,")
    print("then run:")
    print(f"  python3 -m youtube.auth exchange --channel {channel_name} --code <CODE>")
    print(f"{'='*70}\n")
    
    return {"auth_url": auth_url, "status": "awaiting_code"}


def check_token_validity(channel_name: str) -> Dict[str, Any]:
    """
    Check the validity of a channel's token and return info.
    
    Args:
        channel_name: Name of the channel
        
    Returns:
        Dictionary with token validity information
    """
    credentials = get_credentials(channel_name)
    if not credentials:
        return {
            "valid": False,
            "error": "No token found",
            "expired": True
        }
    
    # Check if expired
    expired = credentials.expired
    
    # Try to refresh if expired (but don't store the refresh here for check)
    if expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            expired = False
        except Exception:
            pass  # Keep expired as True if refresh fails
    
    return {
        "valid": credentials.valid and not expired,
        "expired": expired,
        "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
        "has_refresh_token": bool(credentials.refresh_token)
    }


if __name__ == "__main__":
    # Allow running as a module for CLI testing
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube OAuth token management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check token validity")
    check_parser.add_argument("--channel", required=True, help="Channel name")
    
    # Authorize command (step 1: get URL)
    auth_parser = subparsers.add_parser("authorize", help="Step 1: Generate OAuth authorization URL")
    auth_parser.add_argument("--channel", required=True, help="Channel name")
    
    # Exchange command (step 2: exchange code for token)
    exchange_parser = subparsers.add_parser("exchange", help="Step 2: Exchange authorization code for token")
    exchange_parser.add_argument("--channel", required=True, help="Channel name")
    exchange_parser.add_argument("--code", required=True, help="Authorization code from redirect URL")
    
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
            result = authorize_channel(args.channel)
        except Exception as e:
            print(f"Authorization failed: {e}")
            exit(1)
    
    elif args.command == "exchange":
        try:
            credentials = exchange_code(args.channel, args.code)
            print(f"Successfully authorized channel: {args.channel}")
            print("Credentials stored securely.")
        except Exception as e:
            print(f"Token exchange failed: {e}")
            exit(1)
    
    else:
        parser.print_help()