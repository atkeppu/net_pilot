import subprocess
import sys
import os
import argparse

from pathlib import Path
import re
import shutil
import json

# Define app name directly in the build script to avoid import-related file locks.
APP_NAME = "NetPilot"
ENTRY_POINT = "main.py"
ICON_FILE = "icon.ico"
MANIFEST_FILE = "admin.manifest"
VERSION_FILE = "version.txt"

def increment_version(part_to_increment: str):
    """Increments the project version in the VERSION file."""
    print(f"-> Päivitetään versionumeroa (osa: {part_to_increment})...")
    version_path = Path.cwd() / "VERSION"
    try:
        current_version = version_path.read_text(encoding="utf-8").strip()
        major, minor, patch = map(int, current_version.split('.'))

        if part_to_increment == 'major':
            major += 1
            minor = 0
            patch = 0
        elif part_to_increment == 'minor':
            minor += 1
            patch = 0
        elif part_to_increment == 'patch':
            patch += 1
        
        new_version = f"{major}.{minor}.{patch}"
        version_path.write_text(new_version, encoding="utf-8")
        print(f"   ...✅ Versio päivitetty: {current_version} -> {new_version}")

    except (FileNotFoundError, ValueError) as e:
        raise RuntimeError(f"VERSION-tiedoston lukeminen tai jäsentäminen epäonnistui: {e}")


def get_app_version() -> str:
    """Reads the app version from the VERSION file."""
    try:
        version_path = Path.cwd() / "VERSION"
        version = version_path.read_text(encoding="utf-8").strip()
        print(f"   ...Löydetty versio: {version}")
        return version
    except FileNotFoundError:
        raise RuntimeError("VERSION file not found in the project root.")

def find_iscc() -> Path | None:
    """
    Finds the Inno Setup Compiler (ISCC.exe) from common installation paths.
    Checks Program Files (x86) and Program Files directories.
    """
    program_files = os.environ.get("ProgramFiles(x86)", "")
    program_files_64 = os.environ.get("ProgramW6432", "")

    search_paths = [
        Path(program_files) / "Inno Setup 6",
        Path(program_files_64) / "Inno Setup 6",
    ]

    for path in search_paths:
        iscc_path = path / "ISCC.exe"
        if iscc_path.is_file():
            print(f"   ...Löytyi Inno Setup -kääntäjä: {iscc_path}")
            return iscc_path
    return None

def create_version_file(version: str):
    """Creates a version file for PyInstaller."""
    print("-> Luodaan versiotiedostoa...")
    version_info_template = """
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({file_version}, 0),
    prodvers=({prod_version}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'FileDescription', u'{app_name}'), StringStruct(u'FileVersion', u'{version_str}'), StringStruct(u'InternalName', u'{app_name}'), StringStruct(u'LegalCopyright', u'© Sami Turpeinen. All rights reserved.'), StringStruct(u'OriginalFilename', u'{app_name}.exe'), StringStruct(u'ProductName', u'{app_name}'), StringStruct(u'ProductVersion', u'{version_str}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    version_info = version_info_template.format(file_version=version.replace('.', ','), prod_version=version.replace('.', ','), app_name=APP_NAME, version_str=version)
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(version_info)
    print(f"   ...{VERSION_FILE} luotu.")

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
        print("   ...✅ Valmis.")
        # Print PyInstaller's final summary, it's often useful.
        if "pyinstaller" in " ".join(command).lower():
             print("\n--- PyInstaller Yhteenveto ---")
             print(process.stdout)
             print("--------------------------")

    except FileNotFoundError:
        print(f"   ...❌ VIRHE: Komentoa '{command[0]}' ei löytynyt. Onko se asennettu?", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"   ...❌ EPÄONNISTUI! Komento '{' '.join(command)}' palautti virhekoodin.", file=sys.stderr)
        print("\n--- VIRHE ---", file=sys.stderr)
        # Show the error message, which is often more useful than just the exit code.
        error_output = e.stderr.strip() or e.stdout.strip()
        print(error_output, file=sys.stderr)
        print("-------------", file=sys.stderr) # type: ignore
        sys.exit(1)

def clean_previous_builds():
    """Removes old build artifacts."""
    print("-> Siivotaan aiempia build-jäämiä...")
    project_root = Path.cwd()
    
    for path_item in [project_root / 'build', project_root / 'dist']:
        if path_item.exists():
            # ignore_errors=True helps prevent crashes from locked files (e.g., by antivirus).
            shutil.rmtree(path_item, ignore_errors=True)
            print(f"   ...ℹ️ Yritetty poistaa kansio: {path_item}")
    
    for spec_file in project_root.glob('*.spec'):
        spec_file.unlink()
        print(f"   ...ℹ️ Poistettu tiedosto: {spec_file}")
    
    if os.path.exists(VERSION_FILE):
        os.remove(VERSION_FILE)
        print(f"   ...ℹ️ Poistettu tiedosto: {VERSION_FILE}")
    print("   ...Valmis.")

def run_inno_setup(iscc_path: Path, version: str) -> str | None:
    """Runs the Inno Setup compiler if the script file exists."""
    setup_script = Path.cwd() / "setup.iss"
    if not setup_script.is_file():
        print(f"-> ⚠️ Varoitus: Inno Setup -skriptiä '{setup_script.name}' ei löytynyt. Ohitetaan asennusohjelman luonti.")
        return None

    # Read setup.iss to find the output directory and filename
    output_dir_match = re.search(r"^\s*OutputDir\s*=\s*(.*)\s*$", setup_script.read_text(), re.MULTILINE)
    output_base_filename_match = re.search(r"^\s*OutputBaseFilename\s*=\s*(.*)\s*$", setup_script.read_text(), re.MULTILINE)

    if not (output_dir_match and output_base_filename_match):
        print("-> ❌ VIRHE: Ei voitu lukea 'OutputDir' ja 'OutputBaseFilename' arvoja setup.iss-tiedostosta.", file=sys.stderr)
        return None

    # The path where Inno Setup will create the installer
    inno_output_dir = Path(output_dir_match.group(1).strip())
    inno_output_filename = f"{output_base_filename_match.group(1).strip()}.exe"
    original_installer_path = inno_output_dir / inno_output_filename

    # Define the new, versioned filename in the main dist directory
    final_installer_name = f"{APP_NAME}-v{version}-setup.exe"
    final_installer_path = Path.cwd() / "dist" / final_installer_name

    # Clean up potential old installer before building
    if final_installer_path.exists():
        final_installer_path.unlink()
    if original_installer_path.exists():
        original_installer_path.unlink()

    # Run Inno Setup
    command = [str(iscc_path), str(setup_script)]
    run_command(command, "Rakennetaan asennusohjelmaa Inno Setupilla")

    # Move and rename the created installer
    if original_installer_path.is_file():
        shutil.move(original_installer_path, final_installer_path)
        print(f"   ...✅ Asennusohjelma siirretty ja nimetty: {final_installer_path}")
        return str(final_installer_path)
    else:
        print(f"   ...❌ VIRHE: Odotettua asennustiedostoa ei löytynyt sijainnista: {original_installer_path}", file=sys.stderr)
        return None

def create_git_info_file():
    """
    Reads the git remote URL, extracts the repo name, and saves it to a JSON file
    in the dist directory. This allows the packaged app to know its repo without git.
    """
    print("-> Luodaan git_info.json-tiedostoa...")
    try:
        # This command is run in the build environment, where git is available.
        result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True)
        url = result.stdout.strip()
        match = re.search(r'github\.com[/:]([\w-]+/[\w.-]+?)(\.git)?$', url)
        if match:
            repo_name = match.group(1).replace('.git', '')
            info = {"repository": repo_name}
            (Path.cwd() / "dist" / "git_info.json").write_text(json.dumps(info), encoding='utf-8')
            print(f"   ...✅ Tallennettu repository: {repo_name}")
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        print("   ...⚠️ Varoitus: Ei voitu tunnistaa Git-repositorya. Julkaisutoiminto ei välttämättä toimi paketoidussa sovelluksessa.")

def generate_changelog(version: str):
    """
    Generates a changelog from git commits since the last tag.
    Saves the output to dist/CHANGELOG.md.
    """
    print("-> Generoidaan muutoslokia (changelog)...")
    try:
        # Find the most recent tag. If no tags, it will error out.
        latest_tag_cmd = ["git", "describe", "--tags", "--abbrev=0"]
        latest_tag = subprocess.check_output(latest_tag_cmd, text=True, encoding='utf-8', stderr=subprocess.PIPE).strip()
        print(f"   ...Löytyi edellinen tagi: {latest_tag}")
        commit_range = f"{latest_tag}..HEAD"
    except subprocess.CalledProcessError:
        # No tags found, this is likely the first release. Log all commits.
        print("   ...⚠️ Varoitus: Aiempia tageja ei löytynyt. Generoidaan loki kaikista commiteista.")
        commit_range = "HEAD"

    try:
        # Get commit subjects since the last tag in a nice bulleted list format.
        log_cmd = ["git", "log", commit_range, "--pretty=format:- %s (%h)"]
        changelog_content = subprocess.check_output(log_cmd, text=True, encoding='utf-8').strip()

        if not changelog_content:
            changelog_content = "- Ei havaittuja muutoksia edellisen version jälkeen."

        changelog_path = Path.cwd() / "CHANGELOG.md"
        changelog_path.write_text(f"# Muutokset versiossa {version}\n\n{changelog_content}\n", encoding='utf-8')
        print(f"   ...✅ Muutosloki tallennettu tiedostoon: {changelog_path}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   ...❌ VIRHE: Muutoslokin generointi epäonnistui. Varmista, että olet Git-repositoriossa.", file=sys.stderr)

def main():
    """Main function that builds the executable file."""
    parser = argparse.ArgumentParser(description=f"Build script for {APP_NAME}.")
    parser.add_argument(
        '--increment', 
        choices=['patch', 'minor', 'major'], 
        help="Increment the version number (patch, minor, or major) before building."
    )
    args = parser.parse_args()

    print(f"--- Aloitetaan {APP_NAME}.exe-tiedoston rakentaminen ---")

    # 1. Handle version increment if requested
    if args.increment:
        increment_version(args.increment)

    # 2. Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstalleria ei löytynyt. Asennetaan se nyt...")
        run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], "Asennetaan PyInstaller")
    try:
        # 2. Clean up old artifacts before building
        clean_previous_builds()

        # 3. Get version and create version file
        app_version = get_app_version()
        create_version_file(app_version)

        # 4. Define and run the PyInstaller command
        pyinstaller_command = [
            sys.executable,     # Use 'python.exe'
            "-m", "PyInstaller",# to run the PyInstaller module
            "--noconfirm",      # Ylikirjoittaa aiemmat build-kansion tiedostot ilman kysymystä
            "--onefile",        # Luo yhden suoritettavan tiedoston
            "--windowed",       # Estää konsoli-ikkunan näkymisen GUI-sovelluksessa
            f"--icon={ICON_FILE}",
            f"--manifest={MANIFEST_FILE}",
            # Varmistetaan, että dynaamisesti ladatut kirjastot tulevat mukaan.
            "--hidden-import=requests",
            # Lisätään PowerShell-skriptit ja ikoni mukaan pakettiin.
            # Muoto on "lähde;kohde", jossa '.' on juurihakemisto paketissa.
            "--add-data", f"logic{os.pathsep}logic",
            "--add-data", f"{ICON_FILE}{os.pathsep}.",
            f"--version-file={VERSION_FILE}",
            f"--name={APP_NAME}",
            ENTRY_POINT
        ]
        run_command(pyinstaller_command, "Rakennetaan .exe-tiedostoa PyInstallerilla")

        # Create the git_info.json file inside the 'dist' directory
        create_git_info_file()

        # Generate a changelog from git history
        generate_changelog(app_version)
        
        # 5. Find and run Inno Setup compiler
        iscc_path = find_iscc()
        installer_path = None
        if iscc_path:
            installer_path = run_inno_setup(iscc_path, app_version)
        else:
            print("\n-> ⚠️ Varoitus: Inno Setup -kääntäjää (ISCC.exe) ei löytynyt.")
            print("   Asenna Inno Setup (https://jrsoftware.org/isinfo.php) ja varmista, että se on asennettu oletussijaintiin, jotta asennusohjelma voidaan luoda automaattisesti.")

        print(f"\n--- VALMIS! ---")
        print(f"✅ {APP_NAME}.exe löytyy nyt kansiosta: {Path.cwd() / 'dist'}")
        print(f"✅ Muutosloki löytyy nyt tiedostosta: {Path.cwd() / 'CHANGELOG.md'}")
    finally:
        # Final cleanup: Ensure the temporary version file is always removed.
        if os.path.exists(VERSION_FILE):
            os.remove(VERSION_FILE)
            print(f"-> ℹ️ Siivottu väliaikainen tiedosto: {VERSION_FILE}")

if __name__ == "__main__":
    main()