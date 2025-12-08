# NetPilot

[![CI Status](https://github.com/atkeppu/NetPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/atkeppu/NetPilot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**NetPilot** on monipuolinen verkonhallinta- ja diagnostiikkatyökalu Windows-käyttöjärjestelmille. Se tarjoaa graafisen käyttöliittymän yleisimpiin verkon vianmääritys- ja hallintatehtäviin, jotka vaativat normaalisti komentorivin käyttöä.

![NetPilot Screenshot](screenshot.png)

## Sisällysluettelo

- [Ominaisuudet](#ominaisuudet)
- [Asennus ja käyttö](#asennus-ja-käyttö)
- [Vaatimukset](#vaatimukset)
- [Kehitys](#kehitys)
- [Jatkuva Integraatio (CI)](#jatkuva-integraatio-ci)
- [Kehitysprosessi ja Tekoälyn Rooli](#kehitysprosessi-ja-tekoälyn-rooli)
- [Osallistuminen (Contributing)](#osallistuminen-contributing)
- [Lisenssi](#lisenssi)

## Ominaisuudet

*   **Verkkosovittimien hallinta:** Ota käyttöön (Enable) ja poista käytöstä (Disable) verkkosovittimia helposti.
*   **Yksityiskohtaiset tiedot:** Näe sovittimien tiedot, kuten IP- ja MAC-osoitteet, nopeudet ja ajuritiedot.
*   **Wi-Fi-työkalut:**
    *   Selaa ja yhdistä saatavilla oleviin Wi-Fi-verkkoihin.
    *   Tarkastele ja poista tallennettuja Wi-Fi-profiileja.
    *   Kopioi tallennettujen verkkojen salasanat leikepöydälle.
    *   Vie profiilit ja salasanat tekstitiedostoon.
*   **Diagnostiikka:**
    *   Seuraa reaaliaikaisesti lataus- ja lähetysnopeuksia.
    *   Tarkista julkinen IP-osoite, yhdyskäytävän ja ulkoisen palvelimen viiveet.
    *   Suorita `tracert` ja `netstat` graafisessa näkymässä.
*   **Verkon ylläpito:**
    *   Tyhjennä DNS-välimuisti (`ipconfig /flushdns`).
    *   Uusi IP-osoite (`ipconfig /release` & `/renew`).
    *   Nollaa verkkopino (`netsh winsock reset`).

## Asennus ja käyttö

### Valmis sovellus (.exe)

1.  Lataa uusin `NetPilot.exe` projektin Releases-sivulta (linkki lisätään myöhemmin).
2.  Käynnistä ladattu tiedosto. Asennusta ei vaadita.

> **Huom!** Ohjelma vaatii **ylläpitäjän oikeudet** toimiakseen oikein, koska se muokkaa verkkosovittimien asetuksia.

### Lähdekoodista suorittaminen

1.  Kloonaa tämä repositorio: `git clone https://github.com/atkeppu/NetPilot.git`
2.  Siirry projektihakemistoon: `cd NetPilot`
3.  Asenna ajonaikaiset riippuvuudet: `pip install -r requirements.txt`
4.  Käynnistä pääskripti ylläpitäjän oikeuksin: `python main.py`

## Vaatimukset

*   Windows 10 tai uudempi.
*   Python 3.10+ (jos suoritetaan lähdekoodista).
*   GitHub CLI (jos käytät `git_helper.py`-skriptiä).

## Kehitys

Tämä osio on tarkoitettu kehittäjille, jotka haluavat muokata koodia tai rakentaa ohjelman itse.

### Kehitysympäristön pystyttäminen

1.  Varmista, että sinulla on Python 3.10+ asennettuna.
2.  Kloonaa repositorio ja siirry sen juurihakemistoon.
3.  (Suositus) Luo ja aktivoi virtuaaliympäristö:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
4.  Asenna kehityksessä tarvittavat riippuvuudet:
    ```bash
    pip install -r requirements-dev.txt
    ```

### Sovelluksen rakentaminen (.exe)

Voit paketoida sovelluksen yhdeksi `.exe`-tiedostoksi `build.py`-skriptillä.
1.  Varmista, että olet asentanut kehitysriippuvuudet (katso yllä).
2.  Suorita build-skripti:
    ```bash
    python build.py
    ```
3.  Valmis `NetPilot.exe`-tiedosto löytyy `dist`-kansiosta.

#### Build-prosessin työkalut

`build.py`-skripti hyödyntää kahta ulkoista työkalua, jotka on asennettava erikseen:

1.  **UPX (Ultimate Packer for eXecutables)**
    *   **Mitä tekee:** Pienentää `NetPilot.exe`-tiedoston kokoa merkittävästi (yleensä ~35 MB -> ~15 MB) pakkaamalla sen.
    *   **Asennus:** Lataa UPX viralliselta sivulta, pura paketti ja lisää `upx.exe` järjestelmän `PATH`-ympäristömuuttujaan (esim. kopioimalla se `C:\Windows`-kansioon). Skripti löytää ja käyttää sitä automaattisesti, jos se on asennettu.

2.  **Inno Setup**
    *   **Mitä tekee:** Luo ammattimaisen asennusohjelman (`NetPilot-x.x.x-setup.exe`), joka osaa luoda pikakuvakkeita ja mahdollistaa sovelluksen helpon poistamisen Ohjauspaneelista.
    *   **Asennus:** Lataa ja asenna Inno Setup viralliselta sivulta. `build.py`-skripti olettaa, että se on asennettu oletussijaintiin (`C:\Program Files (x86)\Inno Setup 6`).

> **Huom:** Build-prosessi toimii, vaikka näitä työkaluja ei olisi asennettu. Tällöin `.exe`-tiedosto on suurempi, eikä asennusohjelmaa luoda.

#### Versionumeron hallinta

`build.py`-skripti tukee versionumeron automaattista päivittämistä `--increment`-valitsimella. Tämä on suositeltu tapa hallita versioita ennen uuden julkaisun tekemistä.

*   **Päivitä patch-versio** (esim. 1.4.0 -> 1.4.1):
    ```bash
    python build.py --increment patch
    ```
*   **Päivitä minor-versio** (esim. 1.4.1 -> 1.5.0):
    ```bash
    python build.py --increment minor
    ```

Jos komento ajetaan ilman `--increment`-valitsinta, skripti käyttää olemassa olevaa versiota `VERSION`-tiedostosta.

### Julkaisuprosessin logiikka

Sovelluksen julkaisuikkuna on suunniteltu joustavaksi:

1.  **Versionumeron päivitys:** Voit päivittää versionumeron `build.py`-skriptillä (`--increment patch`), muokata `VERSION`-tiedostoa käsin tai muuttaa version suoraan julkaisuikkunassa. Onnistuneen julkaisun jälkeen uusi versio tallentuu automaattisesti `VERSION`-tiedostoon.
2.  **Muutoslokin generointi:** Jos julkaisuikkunassa oleva versio ei vastaa `CHANGELOG.md`-tiedoston versiota, muutosloki generoidaan automaattisesti uudelleen oikealla versiolla.
3.  **Asennustiedoston etsintä:** Julkaisutoiminto etsii dynaamisesti `dist`-kansiosta minkä tahansa `*-setup.exe`-päätteisen tiedoston. Tämä varmistaa, että oikea asennustiedosto löytyy, vaikka olisit muuttanut versionumeroa dialogissa juuri ennen julkaisua. Jos asennustiedostoa ei löydy, se lataa pelkän `NetPilot.exe`-tiedoston.

### Arkkitehtuurikaavioiden tarkastelu

`ARCHITECTURE.md`-tiedosto sisältää Mermaid-syntaksilla luotuja kaavioita, jotka visualisoivat sovelluksen rakennetta. Nämä kaaviot eivät välttämättä näy oikein kaikissa Markdown-katseluohjelmissa.

**Suositus:** Käytä editoria, joka tukee Mermaid-laajennuksia. Esimerkiksi:

*   **Visual Studio Code:** Asenna laajennus `Markdown Preview Mermaid Support`. Tämän jälkeen kaaviot näkyvät oikein, kun avaat `.md`-tiedoston esikatselun (esim. `Ctrl+Shift+V`).
*   **GitHub:** Mermaid-kaaviot renderöityvät automaattisesti, kun ne ovat ````mermaid` koodilohkojen sisällä, kuten `ARCHITECTURE.md`-tiedostossa on tehty.

### Kehittäjän aputyökalut

`git_helper.py`-skripti on apuväline, joka automatisoi uuden GitHub-projektin luomisen ja olemassa olevan koodin lähettämisen sinne. Tämä on hyödyllistä, kun aloitat uuden projektin paikallisesti ja haluat julkaista sen GitHubiin vaivattomasti.

**Esimerkkikäyttö:**

```bash
# Luo uusi julkinen projekti nimeltä "NetPilot" GitHubiin
python git_helper.py NetPilot -d "Projektin kuvaus tähän"
```

## Kehitysprosessi ja Tekoälyn Rooli

Tämä projekti on kehitetty hyödyntäen laajasti tekoälyavusteisia työkaluja, kuten Gemini Code Assistia. Tekoälyä on käytetty monissa kehitysvaiheissa:

*   **Koodin generointi:** Rutiininomaisten funktioiden ja koodirakenteiden luominen.
*   **Refaktorointi:** Koodin laadun ja luettavuuden parantaminen.
*   **Virheenkorjaus:** Ongelmien tunnistaminen ja korjausehdotusten saaminen.
*   **Dokumentaatio:** Kommenttien, `README`-tiedoston ja muiden selittävien tekstien kirjoittaminen.
*   **Testaus:** Yksikkötestien luominen ja testauksen suunnittelu.

Tekoälyn käyttö on nopeuttanut kehitystä merkittävästi ja auttanut ylläpitämään korkeaa koodin laatua.

## Osallistuminen (Contributing)

Apu projektin kehittämisessä on tervetullutta! Jos haluat osallistua, voit tehdä sen seuraavilla tavoilla:

1.  **Ilmoita bugeista:** Jos löydät virheen, luo uusi Issue ja kuvaile ongelma mahdollisimman tarkasti.
2.  **Ehdota parannuksia:** Onko sinulla idea uudesta ominaisuudesta tai parannuksesta? Avaa Issue ja kerro siitä.
3.  **Lähetä Pull Request:** Jos olet korjannut bugin tai toteuttanut uuden ominaisuuden, voit lähettää Pull Requestin.

## Lisenssi

Tämä projekti on lisensoitu MIT-lisenssillä. Tämä tarkoittaa, että voit vapaasti käyttää, kopioida, muokata ja jakaa koodia, kunhan alkuperäinen lisenssi ja tekijänoikeusilmoitus säilytetään.
```