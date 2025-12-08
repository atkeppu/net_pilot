# Projektin Roadmap

Tämä dokumentti kuvaa NetPilot-projektin kehityssuunnitelmaa. Se sisältää sekä jo toteutetut virstanpylväät että tulevaisuuden tavoitteet.

## Toteutetut ominaisuudet

✅ **Jatkuvan integraation (CI) käyttöönotto**
*   **Tila:** Valmis.
*   **Toteutus:** GitHub Actions -työnkulku (`.github/workflows/ci.yml`) on luotu. Se suorittaa automaattisesti `mypy`-tyyppitarkistuksen ja `pytest`-yksikkötestit jokaisen `push`- ja `pull_request`-tapahtuman yhteydessä.

✅ **Asennuspaketin luominen**
*   **Tila:** Valmis.
*   **Toteutus:** `build.py`-skripti tukee Inno Setup -työkalua, jolla luodaan ammattimainen asennusohjelma (`.exe`). Tämä mahdollistaa pikakuvakkeiden luomisen ja sovelluksen helpon poistamisen.

✅ **Resurssien hallinta**
*   **Tila:** Valmis.
*   **Toteutus:** `build.py` lisää tarvittavat resurssit (kuten `icon.ico`) PyInstaller-pakettiin, mikä varmistaa niiden toimivuuden jaettavassa sovelluksessa.

## Tulevaisuuden kehityskohteet

### 1. Testikattavuuden parantaminen
*   **Tila:** Kesken.
*   **Tehtävä:** Kirjoittaa lisää yksikkötestejä erityisesti `logic`- ja `gui`-kerrosten toiminnoille.
*   **Tavoite:** Nostaa testikattavuus (`coverage`) nykyisestä (60 %) yli 80 %:iin.
*   **Miksi:** Varmistaa koodin vakauden, ehkäisee regressioita ja helpottaa uusien ominaisuuksien lisäämistä turvallisesti.

### 2. Koodin refaktorointi ja laadun parantaminen
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Käydä läpi sovelluksen koodikanta ja soveltaa SOLID-periaatteita. Esimerkiksi `gui/main_window.py`-tiedoston `ActionHandler`-luokka on jo jaettu pienempiin osiin, mutta vastaavia parannuksia voidaan tehdä muuallakin.
*   **Miksi:** Parantaa koodin luettavuutta, ylläpidettävyyttä ja testattavuutta.

### 3. Dokumentaation viimeistely
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Kirjoittaa kattavampi API-dokumentaatio koodin sisälle (docstringit) ja varmistaa, että `README.md` ja `ARCHITECTURE.md` ovat täysin ajan tasalla.
*   **Miksi:** Helpottaa uusien kehittäjien perehtymistä projektiin ja selkeyttää olemassa olevia toiminnallisuuksia.

### 4. Lokituksen parantaminen
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Lisätä kontekstitietoa lokiviesteihin, kuten funkti- ja moduulinimiä. Harkita jäsennellyn lokituksen (esim. JSON-formaatti) käyttöönottoa, mikä helpottaisi lokien automaattista analysointia tulevaisuudessa.
*   **Miksi:** Nopeuttaa virheiden diagnosointia ja antaa paremman kuvan sovelluksen toiminnasta ajon aikana.

### 5. Käyttöliittymän modernisointi
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Tutkia ja ottaa käyttöön modernimpi ulkoasu sovellukselle. Tämä voi sisältää:
    *   `ttkthemes`-kirjaston tai `Sun Valley TTK Theme`:n hyödyntämisen nykyisen Tkinter-käyttöliittymän ulkoasun parantamiseksi.
    *   Käyttöliittymän elementtien ja asettelun uudelleensuunnittelun käyttäjäkokemuksen parantamiseksi.
    *   Pitkällä tähtäimellä siirtymisen harkitsemista toiseen UI-kirjastoon (esim. PyQt/PySide).
*   **Miksi:** Parantaa sovelluksen visuaalista ilmettä ja käytettävyyttä, tehden siitä miellyttävämmän ja intuitiivisemman loppukäyttäjälle.
