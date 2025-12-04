import subprocess
import sys
import os
import argparse

try:
    from github_integration import check_github_cli_auth
except ImportError:
    print("❌ Virhe: Projektin moduuleja ei voitu ladata. Varmista, että suoritat skriptin projektin juurihakemistosta.", file=sys.stderr)
    sys.exit(1)

def run_command(command: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess | None: # type: ignore
    """A helper to run a command and handle errors."""
    try:
        # Using shell=False is safer. The command should be a list of strings.
        return subprocess.run(command, check=check, capture_output=capture, text=True, encoding='utf-8', shell=False)
    except FileNotFoundError:
        print(f"❌ Virhe: Komentoa '{command[0]}' ei löytynyt. Onko se asennettu ja PATH-ympäristömuuttujassa?", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ Komennon '{' '.join(command)}' suoritus epäonnistui:", file=sys.stderr)
        print(e.stderr or e.stdout, file=sys.stderr)
        return None

def get_current_branch() -> str | None:
    """Gets the current git branch name."""
    result = run_command(["git", "branch", "--show-current"])
    if result:
        return result.stdout.strip()
    return None

def main():
    """A command-line helper to initialize a Git repository and push it to GitHub."""
    epilog_text = """
Mitä tämä skripti tekee:
  1. Tarkistaa, että Git ja GitHub CLI (gh) on asennettu ja toimivat.
  2. Alustaa paikallisen Git-repon, jos sitä ei ole olemassa.
  3. Lisää kaikki projektin tiedostot ja tekee 'commit'-paketin.
  4. Luo uuden julkisen (tai yksityisen) repon GitHub-tilillesi.
  5. Työntää (push) paikallisen koodin uuteen etärepoon.

Jos paikallinen repo on jo linkitetty etärepoon ('origin'), skripti vain
työntää olemassa olevat muutokset sinne.
"""
    parser = argparse.ArgumentParser(
        description="Luo uuden GitHub-repon ja vie olemassa olevan koodin sinne.",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("repo_name", help="Uuden GitHub-repositorion nimi (esim. 'NetPilot').")
    parser.add_argument("-m", "--message", default="Initial commit", help="Commit-viesti, jota käytetään (oletus: 'Initial commit').")
    parser.add_argument("--private", action="store_true", help="Luo yksityisen (private) repositorion. Oletus on julkinen (public).")
    parser.add_argument("-d", "--description", type=str, help="Repositorion kuvaus (asetetaan lainausmerkkien sisään).")

    args = parser.parse_args()

    print("--- Aloitetaan lähdekoodin vienti GitHubiin ---")
    # 1. Tarkista työkalut (Git ja GitHub CLI)
    print("1/4: Tarkistetaan työkalujen asennukset...")
    if not run_command(["git", "--version"]):
        sys.exit(1)
    print("✅ Git on asennettu.")

    is_ok, message = check_github_cli_auth()
    if not is_ok:
        print(f"❌ Virhe: {message}", file=sys.stderr)
        sys.exit(1)
    print("✅ GitHub CLI on asennettu ja käyttäjä on kirjautunut.")

    # 2. Alusta Git-repository ja tee commit
    if not os.path.isdir('.git'):
        print("\n2/4: Alustetaan uusi Git-repository...")
        if not run_command(["git", "init"]):
            sys.exit(1)
        print("✅ Git-repository alustettu.")
    else:
        print("\n2/4: Olemassa oleva Git-repository löydetty.")

    print("-> Lisätään projektin tiedostot...")
    if not run_command(["git", "add", "."]):
        sys.exit(1)

    # Check if there are changes to commit
    status_result = run_command(["git", "status", "--porcelain"])
    if status_result and status_result.stdout:
        print(f"-> Tehdään commit viestillä '{args.message}'...")
        if not run_command(["git", "commit", "-m", args.message]):
            print("❌ Commit epäonnistui odottamattomasti.", file=sys.stderr)
            sys.exit(1)
        print("✅ Commit onnistui.")
    else:
        print("ℹ️ Info: Ei uusia muutoksia committoitavaksi. Ohitetaan commit.")

    # 3. Tarkista, onko etärepository jo linkitetty
    remotes = run_command(["git", "remote", "-v"])
    if remotes and "origin" in remotes.stdout:
        print("\n3/4: Etärepository 'origin' on jo olemassa. Ohitetaan luonti ja yritetään työntää (push).")
        print("\n4/4: Työnnetään muutokset olemassa olevaan repositoryyn...")
        
        current_branch = get_current_branch()
        if not current_branch:
            print("❌ Ei voitu tunnistaa nykyistä Git-haaraa.", file=sys.stderr)
            sys.exit(1)
            
        if not run_command(["git", "push", "origin", current_branch]):
            print(f"❌ Koodin työntäminen haaraan '{current_branch}' epäonnistui.", file=sys.stderr)
            sys.exit(1)
            
        repo_url_output = run_command(["git", "remote", "get-url", "origin"])
        repo_url = repo_url_output.stdout.strip() if repo_url_output else "N/A"

    # 4. Luo uusi repository ja työnnä koodi sinne
    else:
        print("\n3/4: Luodaan uutta GitHub-repositorya...")
        visibility = "--private" if args.private else "--public"
        
        create_command = ["gh", "repo", "create", args.repo_name, visibility, "--source=.", "--push"]
        
        if args.description:
            # Lainausmerkkejä ei tarvita, kun shell=False
            create_command.extend(["-d", args.description])

        result = run_command(create_command)
        if not result:
            print("❌ Repositorion luonti epäonnistui. Tarkista yllä oleva virheilmoitus.", file=sys.stderr)
            print("   (Yleinen syy on, että samanniminen repositorio on jo olemassa GitHubissa.)", file=sys.stderr)
            sys.exit(1)
        
        # The URL can be in stdout or stderr depending on the gh version.
        # We search both to be safe.
        combined_output = result.stdout + "\n" + result.stderr
        repo_url = next((line for line in combined_output.splitlines() if line.startswith('https://github.com/')), "N/A")

        print(f"✅ Repositorio luotu onnistuneesti.")
        print("\n4/4: Koodi työnnetty GitHubiin.")

    print("\n--- VALMIS! ---")
    print(f"✅ Projektisi lähdekoodi on nyt GitHubissa osoitteessa: {repo_url.replace('.git', '')}")

if __name__ == "__main__":
    main()