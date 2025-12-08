import pytest
import tkinter as tk

@pytest.fixture(scope="session")
def tk_root():
    """
    Provides a single, shared, hidden Tkinter root window for the entire
    test session.

    This avoids creating a new root window for every test that needs one,
    which is slow and can cause issues in some environments. It also prevents
    TclErrors in CI/CD pipelines by keeping the window withdrawn.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the window
    yield root
    root.destroy()