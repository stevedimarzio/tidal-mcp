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
