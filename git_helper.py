import subprocess
import sys
import os
import argparse

try:
    from github_integration import check_github_cli_auth
except ImportError:
    print("❌ Virhe: Projektin moduuleja ei voitu ladata. Varmista, että suoritat skriptin projektin juurihakemistosta.", file=sys.stderr)
    sys.exit(1)

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def run_command(command: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess | None: # type: ignore
    """A helper to run a command and handle errors."""
    try:
        # Using shell=False is safer. The command should be a list of strings.
        return subprocess.run(command, check=check, capture_output=capture, text=True, encoding='utf-8', shell=False)
    except FileNotFoundError:
        print(f"{Colors.FAIL}❌ Virhe: Komentoa '{command[0]}' ei löytynyt. Onko se asennettu ja PATH-ympäristömuuttujassa?{Colors.ENDC}", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}❌ Komennon '{' '.join(command)}' suoritus epäonnistui:{Colors.ENDC}", file=sys.stderr)
        error_output = e.stderr or e.stdout
        if error_output:
            print(f"{Colors.FAIL}{error_output.strip()}{Colors.ENDC}", file=sys.stderr)
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

    print(f"{Colors.HEADER}--- Aloitetaan lähdekoodin vienti GitHubiin ---{Colors.ENDC}")
    # 1. Tarkista työkalut (Git ja GitHub CLI)
    print(f"\n{Colors.BOLD}1/5: Tarkistetaan työkalujen asennukset...{Colors.ENDC}")
    if not run_command(["git", "--version"]):
        sys.exit(1)
    print(f"{Colors.OKGREEN}✅ Git on asennettu.{Colors.ENDC}")

    is_ok, message = check_github_cli_auth()
    if not is_ok:
        print(f"{Colors.FAIL}❌ Virhe: {message}{Colors.ENDC}", file=sys.stderr)
        sys.exit(1)
    print(f"{Colors.OKGREEN}✅ GitHub CLI on asennettu ja käyttäjä on kirjautunut.{Colors.ENDC}")

    # 2. Alusta Git-repository ja tee commit
    if not os.path.isdir('.git'):
        print(f"\n{Colors.BOLD}2/5: Alustetaan uusi Git-repository...{Colors.ENDC}")
        if not run_command(["git", "init"]):
            sys.exit(1)
        # Set default branch to 'main'
        if not run_command(["git", "branch", "-M", "main"]):
            print(f"{Colors.WARNING}⚠️ Varoitus: Oletushaaran nimeäminen 'main'-haaraksi epäonnistui.{Colors.ENDC}")
        print(f"{Colors.OKGREEN}✅ Git-repository alustettu ja oletushaaraksi asetettu 'main'.{Colors.ENDC}")
    else:
        print(f"\n{Colors.BOLD}2/5: Olemassa oleva Git-repository löydetty.{Colors.ENDC}")

    print("-> Lisätään projektin tiedostot...")
    if not run_command(["git", "add", "."]):
        sys.exit(1)

    # Check if there are changes to commit
    status_result = run_command(["git", "status", "--porcelain"], capture=True)
    if status_result and status_result.stdout:
        print(f"-> Tehdään commit viestillä '{args.message}'...")
        if not run_command(["git", "commit", "-m", args.message]):
            print(f"{Colors.FAIL}❌ Commit epäonnistui odottamattomasti.{Colors.ENDC}", file=sys.stderr)
            sys.exit(1)
        print(f"{Colors.OKGREEN}✅ Commit onnistui.{Colors.ENDC}")
    else:
        print(f"{Colors.OKCYAN}ℹ️ Info: Ei uusia muutoksia committoitavaksi. Ohitetaan commit.{Colors.ENDC}")

    # 3. Tarkista, onko etärepository jo linkitetty
    remotes = run_command(["git", "remote", "-v"])
    if remotes and "origin" in remotes.stdout: # type: ignore
        print(f"\n{Colors.BOLD}3/5: Etärepository 'origin' on jo olemassa. Ohitetaan luonti.{Colors.ENDC}")
        print(f"\n{Colors.BOLD}4/5: Työnnetään muutokset olemassa olevaan repositoryyn...{Colors.ENDC}")
        
        current_branch = get_current_branch()
        if not current_branch:
            print("❌ Ei voitu tunnistaa nykyistä Git-haaraa.", file=sys.stderr)
            sys.exit(1)
            
        if not run_command(["git", "push", "origin", current_branch]):
            print(f"{Colors.FAIL}❌ Koodin työntäminen haaraan '{current_branch}' epäonnistui.{Colors.ENDC}", file=sys.stderr)
            sys.exit(1)
            
        repo_url_output = run_command(["git", "remote", "get-url", "origin"])
        repo_url = repo_url_output.stdout.strip() if repo_url_output else "N/A"

    # 4 & 5. Luo uusi repository ja työnnä koodi sinne
    else:
        print(f"\n{Colors.BOLD}3/5: Vahvistetaan GitHub-repon luonti...{Colors.ENDC}")
        visibility = "--private" if args.private else "--public"
        visibility_text = "yksityisen (private)" if args.private else "julkisen (public)"
        
        try:
            confirm = input(f"Haluatko luoda uuden {visibility_text} GitHub-repon nimellä '{args.repo_name}'? (y/N): ")
            if confirm.lower() != 'y':
                print(f"{Colors.WARNING}Peruutettu käyttäjän toimesta.{Colors.ENDC}")
                sys.exit(0)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Peruutettu käyttäjän toimesta.{Colors.ENDC}")
            sys.exit(0)

        print(f"\n{Colors.BOLD}4/5: Luodaan uutta GitHub-repositorya...{Colors.ENDC}")
        
        # If repo_name contains a '/', assume it's in 'owner/repo' format.
        # Otherwise, create it under the currently logged-in user.
        if '/' in args.repo_name:
            create_command = ["gh", "repo", "create", args.repo_name, visibility, "--source=."]
        else:
            create_command = ["gh", "repo", "create", args.repo_name, visibility, "--source=.", "--push"]
        
        if args.description:
            create_command.extend(["-d", args.description])

        result = run_command(create_command)
        if not result: # type: ignore
            print(f"{Colors.FAIL}❌ Repositorion luonti epäonnistui. Tarkista yllä oleva virheilmoitus.{Colors.ENDC}", file=sys.stderr)
            print(f"{Colors.FAIL}   (Yleinen syy on, että samanniminen repositorio on jo olemassa GitHubissa.){Colors.ENDC}", file=sys.stderr)
            sys.exit(1)
        
        # If we created the repo under an organization or another user, we need to manually set the remote and push.
        if '/' in args.repo_name:
            print("-> Asetetaan etärepository ja työnnetään koodi...")
            repo_url_for_remote = f"https://github.com/{args.repo_name}.git"
            run_command(["git", "remote", "add", "origin", repo_url_for_remote])
            run_command(["git", "push", "-u", "origin", "main"])

        # The URL can be in stdout or stderr depending on the gh version.
        # We search both to be safe.
        combined_output = result.stdout + "\n" + result.stderr # type: ignore
        repo_url = next((line for line in combined_output.splitlines() if line.startswith('https://github.com/')), "N/A")

        print(f"{Colors.OKGREEN}✅ Repositorio luotu onnistuneesti.{Colors.ENDC}")
        print(f"\n{Colors.BOLD}5/5: Koodi työnnetty GitHubiin.{Colors.ENDC}")

    print(f"\n{Colors.HEADER}--- VALMIS! ---{Colors.ENDC}")
    print(f"{Colors.OKGREEN}✅ Projektisi lähdekoodi on nyt GitHubissa osoitteessa: {Colors.OKCYAN}{repo_url.replace('.git', '')}{Colors.ENDC}")

if __name__ == "__main__":
    main()