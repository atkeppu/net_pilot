import os
import fnmatch
from pathlib import Path
import json

# --- Asetukset ---
# Projektin juurihakemisto (tämän skriptin sijainti)
ROOT_DIR = Path(__file__).parent
# Tiedosto, johon konteksti kirjoitetaan
OUTPUT_FILE = "project_context.txt"
# Tiedostot, joista ohitussäännöt luetaan
IGNORE_FILE = ".contextignore"
VSCODE_SETTINGS_FILE = ".vscode/settings.json"
# --- Skriptin loppuosa ---

def load_vscode_ignore_patterns(settings_path: Path) -> list[str]:
    """Lukee 'files.exclude' -säännöt VS Coden settings.json-tiedostosta."""
    patterns = []
    if not settings_path.is_file():
        return patterns

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Haetaan files.exclude-osio, oletuksena tyhjä sanakirja
        exclude_settings = data.get("files.exclude", {})
        if isinstance(exclude_settings, dict):
            # Lisätään listaan ne avaimet (säännöt), joiden arvo on true
            patterns.extend([pattern for pattern, excluded in exclude_settings.items() if excluded])
    except (json.JSONDecodeError, IOError) as e:
        print(f"Varoitus: VS Coden asetustiedoston '{settings_path.name}' lukeminen epäonnistui: {e}")
    return patterns

def load_ignore_patterns(ignore_file_path: Path) -> list[str]:
    """Lukee ohitussäännöt .contextignore-tiedostosta."""
    if not ignore_file_path.is_file():
        print(f"Varoitus: Ohitustiedostoa '{ignore_file_path.name}' ei löytynyt. Käytetään tyhjää listaa.")
        return []
    with open(ignore_file_path, "r", encoding="utf-8") as f:
        # Poistetaan tyhjät rivit ja kommentit (#-alkuiset)
        return [line for line in (line.strip() for line in f) if line and not line.startswith('#')]

def should_ignore(path: Path, root: Path, patterns: list[str]) -> bool:
    """Tarkistaa, pitäisikö tiedosto tai kansio ohittaa."""
    # Muunnetaan polku suhteelliseksi projektin juureen nähden.
    # Käytetään as_posix() varmistamaan, että polkuerottimet ovat aina '/',
    # mikä on yhteensopivaa .gitignore-tyylisten sääntöjen kanssa.
    try:
        relative_path_str = path.relative_to(root).as_posix()
    except ValueError:
        # This can happen in rare cases with os.walk, just ignore the path.
        return True

    for pattern in patterns:
        # Kansiomalli: 'build/' osuu 'build'-kansioon ja kaikkeen sen sisällä.
        if pattern.endswith('/'):
            if relative_path_str.startswith(pattern.rstrip('/')) and path.is_dir():
                return True
            elif fnmatch.fnmatch(relative_path_str, pattern.rstrip('/') + '/*'):
                return True
        # Tiedostomalli: '*.log' tai 'README.md'
        elif fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(relative_path_str, pattern):
            return True
    return False

def main():
    """Pääfunktio, joka kerää tiedostojen sisällöt."""
    print(f"Aloitetaan projektin kontekstin kerääminen tiedostoon '{OUTPUT_FILE}'...")

    # Ladataan säännöt molemmista tiedostoista
    context_ignore_patterns = load_ignore_patterns(ROOT_DIR / IGNORE_FILE)
    print(f"Ladattu {len(context_ignore_patterns)} ohitussääntöä tiedostosta '{IGNORE_FILE}'.")

    vscode_ignore_patterns = load_vscode_ignore_patterns(ROOT_DIR / VSCODE_SETTINGS_FILE)
    if vscode_ignore_patterns:
        print(f"Ladattu {len(vscode_ignore_patterns)} ohitussääntöä tiedostosta '{VSCODE_SETTINGS_FILE}'.")

    # Yhdistetään listat ja poistetaan duplikaatit
    all_ignore_patterns = list(set(context_ignore_patterns + vscode_ignore_patterns))

    try:
        with open(ROOT_DIR / OUTPUT_FILE, "w", encoding="utf-8", errors="ignore") as outfile:
            for root, dirs, files in os.walk(ROOT_DIR, topdown=True):
                current_root_path = Path(root)

                # Poistetaan ohitettavat kansiot jatkokäsittelystä (topdown=True vaaditaan)
                dirs[:] = [d for d in dirs if not should_ignore(current_root_path / d, ROOT_DIR, all_ignore_patterns)]

                for filename in files:
                    filepath = current_root_path / filename
                    if should_ignore(filepath, ROOT_DIR, all_ignore_patterns):
                        continue

                    relative_filepath = filepath.relative_to(ROOT_DIR).as_posix()
                    print(f"  Lisätään: {relative_filepath}")

                    outfile.write("=" * 80 + "\n")
                    outfile.write(f"FILE: {relative_filepath}\n")
                    outfile.write("=" * 80 + "\n\n")
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as infile:
                            content = infile.read()
                            outfile.write(content)
                            outfile.write("\n\n")
                    except Exception as e:
                        outfile.write(f"*** Tiedoston lukeminen epäonnistui: {e} ***\n\n")

        print(f"\nValmis! Koko projektin konteksti on tallennettu tiedostoon '{OUTPUT_FILE}'.")

    except IOError as e:
        print(f"\nVirhe: Tiedostoon '{OUTPUT_FILE}' kirjoittaminen epäonnistui. {e}")

if __name__ == "__main__":
    main()