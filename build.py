import subprocess
import sys
import os

from pathlib import Path
import shutil

# Define app name directly in the build script to avoid import-related file locks.
APP_NAME = "NetPilot"
ENTRY_POINT = "main.py"
ICON_FILE = "icon.ico"
MANIFEST_FILE = "admin.manifest"

def run_command(command: list[str], description: str):
    """Runs a command line command, shows its status, and handles errors."""
    print(f"-> {description}...")
    try:
        # Komennon suorittaminen ilman shell=True on turvallisempaa.
        process = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        print("   ...Valmis.")
        # Print PyInstaller's final summary, it's often useful.
        if "pyinstaller" in command[0].lower():
             print("\n--- PyInstaller Yhteenveto ---")
             print(process.stdout)
             print("--------------------------")

    except FileNotFoundError:
        print(f"   ...VIRHE: Komentoa '{command[0]}' ei löytynyt. Onko se asennettu?", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"   ...EPÄONNISTUI! Komento '{' '.join(command)}' palautti virhekoodin.", file=sys.stderr)
        print("\n--- VIRHE ---", file=sys.stderr)
        # Show the error message, which is often more useful than just the exit code.
        error_output = e.stderr.strip() or e.stdout.strip()
        print(error_output, file=sys.stderr)
        print("-------------", file=sys.stderr)
        sys.exit(1)

def clean_previous_builds():
    """Removes old build artifacts."""
    print("-> Siivotaan aiempia build-jäämiä...")
    project_root = Path.cwd()
    
    for path_item in [project_root / 'build', project_root / 'dist']:
        if path_item.exists():
            shutil.rmtree(path_item)
            print(f"   ...Poistettu kansio: {path_item}")
    
    for spec_file in project_root.glob('*.spec'):
        spec_file.unlink()
        print(f"   ...Poistettu tiedosto: {spec_file}")
    print("   ...Valmis.")

def main():
    """Main function that builds the executable file."""
    print(f"--- Aloitetaan {APP_NAME}.exe-tiedoston rakentaminen ---")

    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstalleria ei löytynyt. Asennetaan se nyt...")
        run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], "Asennetaan PyInstaller")

    # 2. Clean up old artifacts before building
    clean_previous_builds()

    # 3. Define and run the PyInstaller command
    pyinstaller_command = [
        sys.executable,     # Use 'python.exe'
        "-m", "PyInstaller",# to run the PyInstaller module
        "--noconfirm",      # Ylikirjoittaa aiemmat build-kansion tiedostot ilman kysymystä
        "--onefile",        # Luo yhden suoritettavan tiedoston
        "--windowed",       # Estää konsoli-ikkunan näkymisen GUI-sovelluksessa
        f"--icon={ICON_FILE}",
        f"--manifest={MANIFEST_FILE}",
        f"--name={APP_NAME}",
        ENTRY_POINT
    ]
    run_command(pyinstaller_command, "Rakennetaan .exe-tiedostoa PyInstallerilla")

    print(f"\n--- VALMIS! ---")
    print(f"✅ {APP_NAME}.exe löytyy nyt kansiosta: {Path.cwd() / 'dist'}")

if __name__ == "__main__":
    main()