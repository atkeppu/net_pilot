# NetPilot

**NetPilot** on monipuolinen verkonhallinta- ja diagnostiikkatyökalu Windows-käyttöjärjestelmille. Se tarjoaa graafisen käyttöliittymän yleisimpiin verkon vianmääritys- ja hallintatehtäviin, jotka vaativat normaalisti komentorivin käyttöä.

![NetPilot Screenshot](screenshot.png)  <!-- Sinun täytyy lisätä kuvakaappaus nimellä screenshot.png -->

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

Ohjelma ei vaadi asennusta.

1.  Lataa uusin versio `dist`-kansiosta (jos olet paketoinut sen PyInstallerilla) tai suoraan lähdekoodista.
2.  Suorita `main.py` Python-tulkilla tai käynnistä `.exe`-tiedosto.
3.  Ohjelma vaatii **ylläpitäjän oikeudet** toimiakseen oikein.

## Vaatimukset

*   Windows 10 tai uudempi.
*   Python 3.10+ (jos suoritetaan lähdekoodista).

## Kehittäjille

Tämä osio on tarkoitettu kehittäjille, jotka haluavat muokata koodia tai rakentaa ohjelman itse.

### Suoritettavan .exe-tiedoston rakentaminen

Ohjelma käyttää `icon.ico`-tiedostoa. Jos haluat luoda oman `.ico`-tiedoston `.png`-kuvasta, voit käyttää esimerkiksi FreeConvert.com-palvelua.

---

Voit paketoida sovelluksen yhdeksi `.exe`-tiedostoksi käyttämällä mukana tulevaa `build.py`-skriptiä. Tämä vaatii PyInstallerin, mutta skripti asentaa sen automaattisesti tarvittaessa.

1.  Avaa komentorivi projektin juurihakemistoon.
2.  Suorita komento:
    ```bash
    python build.py
    ```
3.  Valmis `NetPilot.exe`-tiedosto löytyy `dist`-kansiosta.

### Lähdekoodin vieminen uuteen GitHub-projektiin

`git_helper.py`-skripti on apuväline, joka automatisoi uuden GitHub-projektin luomisen ja olemassa olevan koodin lähettämisen sinne. Tämä on hyödyllistä, kun aloitat uuden projektin paikallisesti ja haluat julkaista sen GitHubiin vaivattomasti.

**Esimerkkikäyttö:**

```bash
# Luo uusi julkinen projekti nimeltä "NetPilot" GitHubiin
python git_helper.py NetPilot -d "Projektin kuvaus tähän"
```