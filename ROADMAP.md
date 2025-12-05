# Projektin Roadmap

Tämä roadmap kokoaa priorisoidut parannusehdotukset projektillesi.

## Korkea prioriteetti (tee ensin)
- Korjaa resource_path PyInstaller-tuella (getattr/sys._MEIPASS).
- Lisää turvallinen virheilmoitushelper (piilotettu Tk-root, fallback logging).
- Pre-flight checks: OS- ja admin-tarkistus, lisää lokitiedoston polku virheilmoituksiin.
- Lisää yksikkötestit business-logiikalle (esim. logic.system.is_admin).
- Lokitus: RotatingFileHandler, lokitiedoston polku konfiguroitavaksi.

## Keskitaso
- CI (GitHub Actions): lint (black/isort), flake8/mypy, pytest, build (pyinstaller).
- Lisää requirements.txt tai pyproject.toml.
- Staattinen analyysi: mypy, flake8, pre-commit.

## Matala prioriteetti
- Paketoiminen/installer (PyInstaller + Inno Setup/WiX).
- Relaunch-as-admin -käynnistysskripti Windowsille.
- Lokalisaatio (FI/EN) ja paremmat käyttäjäviestit.
- Turvallisuus: älä paljasta sisäisiä polkuja virheilmoituksissa.

## Testaus & QA
- Lisää tests/ -hakemisto ja pytest-konfiguraatio.
- Lisää testikattavuusraportti CI:hin.

## Tiedostot joita kannattaa lisätä
- ROADMAP.md
- requirements.txt / pyproject.toml
- .github/workflows/ci.yml
- tests/

## Seuraavat askeleet (ehdotus)
1. Hyväksy roadmap tai pyydä muutoksia.
2. Halutessasi lisään ROADMAP.md repoon ja teen commitin/PR:n.
3. Toteutan ensimmäisen PR:n: resource_path + turvallinen error helper.
