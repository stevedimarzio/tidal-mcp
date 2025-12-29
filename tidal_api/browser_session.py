import concurrent.futures
import webbrowser
from collections.abc import Callable
from pathlib import Path

import tidalapi

# Configure SSL certificates before importing tidalapi
# This fixes issues with uv environments where certifi path might be invalid
try:
    from .utils import configure_ssl_certificates
except ImportError:
    from utils import configure_ssl_certificates

# Configure SSL before importing tidalapi
configure_ssl_certificates()


class BrowserSession(tidalapi.Session):
    """
    Extended tidalapi.Session that automatically opens the login URL in a browser
    """

    def login_oauth_simple(self, fn_print: Callable[[str], None] = print) -> None:
        """
        Login to TIDAL with a remote link, automatically opening the URL in a browser.

        :param fn_print: The function to display additional information
        :raises: TimeoutError: If the login takes too long
        """
        login, future = self.login_oauth()

        # Display information about the login
        text = "Opening browser for TIDAL login. The code will expire in {0} seconds"
        fn_print(text.format(login.expires_in))

        # Open the URL in the default browser
        auth_url = login.verification_uri_complete
        if not auth_url.startswith("http"):
            auth_url = "https://" + auth_url

        # Try to open browser, but continue even if it fails
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            fn_print(f"Warning: Could not open browser automatically: {e}")
            fn_print(f"Please visit this URL manually: {auth_url}")

        # Wait for the authentication to complete with timeout
        # Use expires_in + small buffer (10 seconds) as timeout
        timeout = login.expires_in + 10
        try:
            future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as e:
            raise TimeoutError(
                f"Login timed out after {timeout} seconds. Please try again."
            ) from e

    def start_oauth_login(self) -> tuple[str, int, concurrent.futures.Future]:
        """
        Start OAuth login process and return the auth URL immediately without blocking.

        Returns:
            Tuple of (auth_url, expires_in, future) where:
            - auth_url: The URL the user needs to visit
            - expires_in: Seconds until the code expires
            - future: Future object to check login completion
        """
        login, future = self.login_oauth()

        auth_url = login.verification_uri_complete
        if not auth_url.startswith("http"):
            auth_url = "https://" + auth_url

        return auth_url, login.expires_in, future

    def login_session_file_auto(
        self,
        session_file: Path,
        do_pkce: bool | None = False,
        fn_print: Callable[[str], None] = print,
    ) -> bool:
        """
        Logs in to the TIDAL api using an existing OAuth/PKCE session file,
        automatically opening the browser for authentication if needed.

        :param session_file: The session json file
        :param do_pkce: Perform PKCE login. Default: Use OAuth logon
        :param fn_print: A function to display information
        :return: Returns true if the login was successful
        """
        # Try to load existing session file, but handle errors gracefully
        if session_file.exists():
            try:
                self.load_session_from_file(session_file)
            except (FileNotFoundError, ValueError, KeyError, Exception) as e:
                fn_print(f"Could not load existing session file: {e}")
                fn_print("Will create a new session...")

        # Session could not be loaded, attempt to create a new session
        if not self.check_login():
            try:
                if do_pkce:
                    fn_print("Creating new session (PKCE)...")
                    self.login_pkce(fn_print=fn_print)
                else:
                    fn_print("Creating new session (OAuth)...")
                    self.login_oauth_simple(fn_print=fn_print)
            except TimeoutError as e:
                fn_print(f"Login timed out: {e}")
                return False
            except Exception as e:
                fn_print(f"Login failed: {e}")
                return False

        if self.check_login():
            # Ensure session file directory exists
            session_file.parent.mkdir(parents=True, exist_ok=True)
            fn_print(f"TIDAL Login OK, creds saved in {str(session_file)}")
            self.save_session_to_file(session_file)
            return True
        else:
            fn_print("TIDAL Login KO")
            return False

    def get_session_data(self) -> dict:
        """
        Extract session token data from BrowserSession.

        Returns:
            Dictionary with session token data ready for storage

        Raises:
            RuntimeError: If session is not authenticated
        """
        if not self.check_login():
            raise RuntimeError("Session is not authenticated")

        return {
            "token_type": self.token_type,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "session_id": self.session_id,
            "is_pkce": self.is_pkce,
        }

    def load_from_data(self, data: dict) -> bool:
        """
        Load session from dictionary data.

        Args:
            data: Dictionary with session token data

        Returns:
            True if load was successful
        """
        try:
            return self.load_oauth_session(
                token_type=data.get("token_type", ""),
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token"),
                is_pkce=data.get("is_pkce", False),
            )
        except Exception as e:
            try:
                from .logger import logger
            except ImportError:
                from logger import logger
            logger.error(f"Failed to load session from data: {e}")
            return False
