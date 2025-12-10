# Projektin Roadmap

Nämä ovat korkean prioriteetin tehtäviä, jotka on tarkoitus toteuttaa seuraavassa versiossa.

### 1. Testikattavuuden parantaminen
*   **Tila:** Kesken.
*   **Tehtävä:** Kirjoittaa lisää yksikkötestejä erityisesti `logic`- ja `gui`-kerrosten toiminnoille.
*   **Tavoite:** Nostaa testikattavuus (`coverage`) nykyisestä (~66 %) yli 80 %:iin.
*   **Miksi:** Varmistaa koodin vakauden, ehkäisee regressioita ja helpottaa uusien ominaisuuksien lisäämistä turvallisesti.

### 2. Käyttöliittymän tilan päivitysongelmat
*   **Tila:** Tiedossa.
*   **Tehtävä:** Korjata bugi, jossa verkkosovittimen tila (esim. "käytössä" / "pois käytöstä") ei päivity luotettavasti käyttöliittymässä heti toimenpiteen jälkeen.
*   **Miksi:** Varmistaa, että käyttöliittymä näyttää aina järjestelmän todellisen tilan, mikä parantaa käyttäjäkokemusta ja luotettavuutta.

### 4. CI-prosessin tiukentaminen
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Nostaa testikattavuuden vähimmäisrajaa (`cov-fail-under`) `pytest.ini`-tiedostossa nykyisestä 60 %:sta esimerkiksi 75 %:iin.
*   **Miksi:** Varmistaa, että koodin laatu ja testikattavuus eivät pääse heikkenemään uusien muutosten myötä. Pakottaa kirjoittamaan testejä uusille ominaisuuksille.

## Tulevaisuuden tavoitteet

Nämä ovat laajempia tai matalamman prioriteetin tehtäviä, joita voidaan toteuttaa tulevissa versioissa.

### 5. Koodin refaktorointi ja laadun parantaminen
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Käydä läpi sovelluksen koodikanta ja soveltaa SOLID-periaatteita. Esimerkiksi `gui/main_window.py`-tiedoston `ActionHandler`-luokka on jo jaettu pienempiin osiin, mutta vastaavia parannuksia voidaan tehdä muuallakin.
*   **Miksi:** Parantaa koodin luettavuutta, ylläpidettävyyttä ja testattavuutta.

### 6. Dokumentaation viimeistely
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Tutkia ja ottaa käyttöön modernimpi ulkoasu sovellukselle. Tämä voi sisältää:
    *   `ttkthemes`-kirjaston tai `Sun Valley TTK Theme`:n hyödyntämisen nykyisen Tkinter-käyttöliittymän ulkoasun parantamiseksi.
    *   Käyttöliittymän elementtien ja asettelun uudelleensuunnittelun käyttäjäkokemuksen parantamiseksi.
    *   Pitkällä tähtäimellä siirtymisen harkitsemista toiseen UI-kirjastoon (esim. PyQt/PySide).
*   **Miksi:** Parantaa sovelluksen visuaalista ilmettä ja käytettävyyttä, tehden siitä miellyttävämmän ja intuitiivisemman loppukäyttäjälle.

### 9. Kehittäjäkokemuksen parantaminen (Developer Experience)
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Tutkia ja mahdollisesti ottaa käyttöön `Trunk.io`-työkalu.
*   **Miksi:** Yhtenäistää ja yksinkertaistaa lintereiden, formaattereiden ja muiden koodinlaadun työkalujen hallintaa. Nopeuttaa paikallista palautetta kehittäjälle (pre-commit hooks) ja parantaa CI-prosessin tehokkuutta.

### 10. Julkaisuprosessin refaktorointi
*   **Tila:** Suunnitteilla.
*   **Tehtävä:** Yhdistää `build.py`-skriptin ja `gui/action_handler.py`:n julkaisulogiikkaa. `ActionHandler` voisi hyödyntää `build.py`:n funktioita (esim. `generate_changelog`) sen sijaan, että se sisältää päällekkäistä logiikkaa.
*   **Miksi:** Noudattaa DRY-periaatetta (Don't Repeat Yourself), keskittää vastuita ja tekee julkaisuprosessista vankemman ja helpommin ylläpidettävän.

## Toteutetut ominaisuudet

✅ **Lokituksen parantaminen**
*   **Tila:** Valmis.
*   **Toteutus:** Lokitusformaatti sisältää nyt oletuksena moduulin, funktion ja rivinumeron. Lisäksi on lisätty tuki jäsennellylle JSON-lokitukselle `LOG_FORMAT=json`-ympäristömuuttujan kautta.

✅ **Dokumentaation viimeistely ja API-dokumentaatio**
*   **Tila:** Valmis (v1).
*   **Tehtävä:** Kirjoittaa kattavampi API-dokumentaatio koodin sisälle (docstringit) ja varmistaa, että `README.md` ja `ARCHITECTURE.md` ovat täysin ajan tasalla.
*   **Miksi:** Helpottaa uusien kehittäjien perehtymistä projektiin ja selkeyttää olemassa olevia toiminnallisuuksia.

✅ **Diagnostiikan älykkyyden parantaminen**
*   **Tila:** Valmis.
*   **Tehtävä:** Estää diagnostiikkatoimintojen (ping, julkinen IP) suorittaminen, jos aktiivista verkkoyhteyttä ei ole.
*   **Miksi:** Vähentää turhia verkkokyselyitä ja virhetilanteita, kun verkkoyhteyttä ei ole saatavilla.