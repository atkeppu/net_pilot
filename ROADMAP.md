# Projektin Roadmap

Tämä on päivitetty roadmap, joka sisältää jäljellä olevat priorisoidut parannusehdotukset projektille.

## Seuraavat askeleet

### 1. Yksikkötestien laajentaminen
Vaikka testausympäristö on pystyssä, itse testien kattavuutta tulee parantaa.

*   **Tehtävä:** Kirjoita lisää yksikkötestejä `logic`-kansion funktioille. Tavoitteena on nostaa testikattavuus (`coverage`) yli 80 %:iin.
*   **Miksi:** Varmistaa koodin vakauden ja helpottaa tulevia muutoksia.

### 2. Jatkuvan integraation (CI) käyttöönotto
Automatisoidaan koodin laadun tarkistus ja testien ajaminen.

*   **Tehtävä:** Luo GitHub Actions -työnkulku (`.github/workflows/ci.yml`), joka suorittaa automaattisesti:
    *   Staattisen analyysin (esim. `flake8`, `mypy`).
    *   Yksikkötestit (`pytest`).
    *   Testikattavuusraportin generoinnin.
*   **Miksi:** Varmistaa, että uudet muutokset eivät riko olemassa olevaa toiminnallisuutta ja ylläpitävät koodin laatustandardeja.

### 3. Asennuspaketin luominen
Vaikka `.exe`-tiedosto on kätevä, ammattimainen asennusohjelma parantaa käyttökokemusta.

*   **Tehtävä:** Tutki ja ota käyttöön työkalu (esim. Inno Setup tai WiX Toolset) asennuspaketin luomiseksi `build.py`:n tuottamasta `.exe`-tiedostosta.
*   **Miksi:** Mahdollistaa mm. Käynnistä-valikon pikakuvakkeiden ja ohjelman helpon poistamisen.

### 4. Resurssien hallinnan parantaminen
*   **Tehtävä:** Luo yleiskäyttöinen `resource_path`-funktio, joka osaa hakea resurssitiedostoja (kuten kuvakkeet) sekä lähdekoodista ajettaessa että PyInstallerin luomasta paketista (`sys._MEIPASS`).
*   **Miksi:** Tekee sovelluksesta robustimman ja helpottaa uusien resurssien lisäämistä tulevaisuudessa.
