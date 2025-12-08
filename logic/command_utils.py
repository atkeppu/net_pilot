import subprocess
import logging
import base64
import os
import codecs

from exceptions import NetworkManagerError

logger = logging.getLogger(__name__)

def _decode_with_encoding(byte_string: bytes, encoding: str, errors: str = 'strict') -> str:
    """Wrapper for bytes.decode to make it patchable for tests."""
    return byte_string.decode(encoding, errors=errors)

def _safe_decode(byte_string: bytes | None) -> str:
    """Safely decodes a byte string using common encodings."""
    if not byte_string:
        return ""
    try:
        return _decode_with_encoding(byte_string, 'utf-8').strip()
    except UnicodeDecodeError:
        try:
            return _decode_with_encoding(byte_string, 'oem').strip()
        except UnicodeDecodeError:
            return _decode_with_encoding(byte_string, 'ascii', errors='replace').strip().replace('\ufffd', '?')

def run_system_command(command: list[str], error_message_prefix: str,
                       check: bool = True, cwd: str | None = None, timeout: int = 10):
    """
    A helper function to run a system command and handle errors consistently.
    Raises NetworkManagerError on failure.
    """
    # noqa: E501
    # To avoid logging a huge base64 string, shorten the log message for encoded commands.
    if "-EncodedCommand" in command:
        try:
            log_command = " ".join(command[:command.index("-EncodedCommand") + 1]) + " <...>"
        except (ValueError, IndexError):
            log_command = " ".join(command) # Fallback
        logger.debug("Executing system command: %s", log_command)
    else:
        logger.debug("Executing system command: %s", " ".join(command))
    try:
        # Use text=False to capture raw bytes and decode manually for robustness
        # Using Popen with communicate is more robust for handling timeouts with I/O.
        with subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=cwd
        ) as process:
            stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
            if check and process.returncode != 0:
                # Manually raise a CalledProcessError to mimic subprocess.run's behavior.
                raise subprocess.CalledProcessError(process.returncode, command, output=stdout_bytes, stderr=stderr_bytes)
            return subprocess.CompletedProcess(command, process.returncode, stdout_bytes, stderr_bytes)
    except subprocess.CalledProcessError as e: # This will now be caught from our manual raise.
        # Safely decode output for error logging
        stdout = _safe_decode(e.stdout)
        stderr = _safe_decode(e.stderr)

        # Create a detailed message for logging
        log_message = (
            f"{error_message_prefix}\n\n"
            f"Command: {' '.join(e.cmd)}\n"
            f"Return Code: {e.returncode}\n"
            f"Stderr: {stderr}\n"
            f"Stdout: {stdout}"
        )
        logger.error("System command failed: %s", log_message)
        # Raise a cleaner error for the UI, preferring stderr if available.
        user_error_message = stderr or stdout or "An unknown error occurred."
        raise NetworkManagerError(f"{error_message_prefix}: {user_error_message}") from e
    except subprocess.TimeoutExpired as e:  # noqa: E501
        logger.error("System command timed out: %s", " ".join(command))
        raise NetworkManagerError(
            f"The operation timed out after {timeout} seconds: {' '.join(command)}") from e
    except FileNotFoundError as e:
        raise NetworkManagerError(
            f"Command '{command[0]}' not found. Is it in the system's PATH?") from e

def run_ps_command(script: str, ps_args: list[str] | None = None, stream_output: bool = False):
    """
    Runs a PowerShell script safely using -EncodedCommand.
    Optional ps_args are passed as arguments to the PowerShell script.

    Args:
        script: The PowerShell script content to run.
        ps_args: Optional list of arguments for the script.
        stream_output: If True, yields output lines as a generator.
                       If False (default), returns the entire decoded stdout string.

    Raises NetworkManagerError on failure.
    """
    logger.debug("Executing PowerShell script.")
    # type: ignore
    encoded_script = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    command = ['powershell', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', encoded_script]
    if ps_args:
        command.extend(ps_args)

    if stream_output:
        return _stream_ps_command(command)
    else:
        result = run_system_command(
            command, "PowerShell script execution failed.")
        return result.stdout.decode('utf-8', errors='ignore')

def _stream_ps_command(command: list[str]):
    """Helper generator to stream output from a PowerShell command."""
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='ignore',
        shell=False, creationflags=subprocess.CREATE_NO_WINDOW
    ) as process:
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                yield line.strip()

def run_external_ps_script(script_name: str, ps_args: list[str] | None = None) -> str:
    """
    Helper to read and execute an external PowerShell script from the 'scripts' directory.
    """
    try:
        # The scripts are located in the same directory as this utility file ('logic/').
        script_dir = os.path.dirname(__file__)
        script_path = os.path.join(script_dir, script_name)

        with open(script_path, 'r', encoding='utf-8') as f:
            ps_script = f.read()

        # If arguments are provided, prepend them to the script content.
        # This is the correct way to pass variables to an EncodedCommand.
        if ps_args:
            arg_string = "; ".join(ps_args)
            ps_script = f"{arg_string};\n{ps_script}"

        return run_ps_command(ps_script)
    except FileNotFoundError as e:
        raise NetworkManagerError(
            f"PowerShell script '{script_name}' not found: {e}") from e