# NetPilot - Sovelluksen Arkkitehtuuri

Tämä dokumentti kuvaa NetPilot-sovelluksen arkkitehtuurin, sen pääkomponentit ja niiden väliset tietovirrat. Arkkitehtuuri on suunniteltu modulaariseksi ja vankaksi, erottaen selkeästi käyttöliittymän, tilanhallinnan ja järjestelmätason toiminnot.

## Yleiskatsaus

NetPilot noudattaa modernia työpöytäsovelluksen arkkitehtuuria, jossa on seuraavat pääperiaatteet:

1.  **Yksisuuntainen tietovirta:** Taustalla suoritettavat toiminnot eivät koskaan muokkaa käyttöliittymää suoraan. Sen sijaan ne lähettävät viestejä keskitettyyn jonoon, josta käyttöliittymä ne käsittelee turvallisesti.
2.  **Vastuun eriyttäminen (Separation of Concerns):**
    *   **GUI-kerros (`gui/`)**: Vastaa vain siitä, miltä sovellus näyttää ja käyttäjän syötteiden vastaanottamisesta.
    *   **Ohjain- ja hallintakerros (`gui/`):** Sisältää luokkia, jotka orkestroivat toimintoja ja hallinnoivat sovelluksen tilaa (`AppContext`, `MainController`, `ActionHandler`, `PollingManager`).
    *   **Logiikkakerros (`logic/`)**: Sisältää kaiken "likaisen työn", kuten järjestelmäkomentojen ja PowerShell-skriptien ajamisen.
3.  **Asynkroninen suoritus:** Hitaat verkkotoiminnot suoritetaan aina taustasäikeissä, jotta käyttöliittymä pysyy jatkuvasti reagoivana.

## Arkkitehtuurikaavio (Mermaid)

```
NetPilot/
├── gui/
│   └── main_window.py      # Pääikkuna ja kaikki UI-komponentit
├── logic/
│   ├── system.py           # Järjestelmätason tarkistukset (esim. admin-oikeudet)
│   └── ...                 # Muu sovelluslogiikka (tulevaisuudessa network_utils.py)
├── logs/                   # (luodaan ajon aikana)
│   └── debug.log           # Oletuslokitiedosto
├── main.py                 # Sovelluksen käynnistystiedosto (entry point)
├── logger_setup.py         # Lokituksen alustus ja konfigurointi
├── build.py                # Skripti .exe-paketin rakentamiseen
├── README.md               # Projektin päädokumentaatio
└── ARCHITECTURE.md         # Tämä tiedosto
```

## Tärkeimmät Komponentit

1.  **`main.py` (Käynnistyspiste)**
    *   Vastaa sovelluksen käynnistämisestä.
    *   Alustaa lokituksen kutsumalla `logger_setup.py`:tä.
    *   Suorittaa esitarkastukset (ns. "pre-flight checks"):
        *   Varmistaa, että sovellus ajetaan Windows-ympäristössä.
        *   Tarkistaa ylläpitäjän oikeudet (`logic/system.py`).
    *   Jos tarkistukset menevät läpi, luo ja käynnistää pääikkunan (`gui/main_window.py`).
    *   Käsittelee ylimmän tason poikkeukset ja kirjaa kriittiset virheet.

2.  **`gui/main_window.py` (Käyttöliittymä)**
    *   Sisältää `NetworkManagerApp`-luokan, joka periytyy `tk.Tk`:sta.
    *   Rakentaa koko graafisen käyttöliittymän: välilehdet, painikkeet, tekstikentät ja muut elementit.
    *   Käsittelee käyttäjän syötteitä (esim. napin painallukset).
    *   Kutsuu `logic`-kerroksen funktioita suorittamaan varsinaiset toiminnot (esim. verkkosovittimen poistaminen käytöstä).
    *   Päivittää käyttöliittymää `logic`-kerroksesta saatujen tulosten perusteella.

3.  **`logic/` (Sovelluslogiikka)**
    *   **`system.py`**: Sisältää käyttöjärjestelmästä riippuvia apufunktioita, kuten `is_admin()`, joka tarkistaa ylläpitäjän oikeudet.
    *   **`network_utils.py` (oletettu)**: Tänne on keskitetty kaikki verkkotoiminnot, jotka suoritetaan komentorivikomennoilla (esim. `netsh`, `ipconfig`, `wmic`). Funktiot palauttavat jäsenneltyä dataa, jonka GUI-kerros voi näyttää käyttäjälle. Tämä eriyttäminen tekee koodista testattavamman ja helpommin ylläpidettävän.

4.  **`logger_setup.py` (Lokitus)**
    *   Konfiguroi keskitetyn `logging`-moduulin, joka kirjoittaa tapahtumat sekä konsoliin että `logs/debug.log`-tiedostoon. Tämä on tärkeää vianjäljityksen kannalta.

## Toimintalogiikka (Data Flow)

1.  Käyttäjä käynnistää `main.py`:n.
2.  Esitarkastukset suoritetaan. Virhetilanteessa näytetään `messagebox` ja sovellus suljetaan.
3.  `NetworkManagerApp`-olio luodaan, ja se rakentaa käyttöliittymän.
4.  Käyttäjä tekee toiminnon, esim. painaa "Disable Adapter" -nappia.
5.  `main_window.py`:n tapahtumankäsittelijä kutsuu vastaavaa funktiota `logic/network_utils.py`:ssä.
6.  `network_utils`-funktio suorittaa tarvittavan järjestelmäkomennon (`subprocess.run`).
7.  Tulos (onnistuminen/virhe ja mahdollinen data) palautetaan `main_window.py`:lle.
8.  Käyttöliittymä päivitetään näyttämään tulos (esim. tilaviesti tai päivitetty sovitinlista).

## Arkkitehtuurikaavio (Mermaid)

```mermaid
graph LR
    subgraph "Käyttöliittymä (GUI)"
        direction TB
        subgraph "Pääikkuna (NetworkManagerApp)"
            MW[main_window.py]
            ALF[AdapterListFrame]
            ADF[AdapterDetailsFrame]
            WSF[WifiStatusFrame]
            DF[DiagnosticsFrame]
            MW --> ALF & ADF & WSF & DF
        end
        subgraph "Erilliset ikkunat (Toplevel)"
            WW[WifiConnectWindow]
            TW[TracerouteWindow]
            NW[NetstatWindow]
            PW[PublishWindow]
        end
        MW -- "Avaa" --> WW & TW & NW & PW
    end

    subgraph "Sovelluslogiikka (Logic)"
        direction TB
        LA[adapters.py]
        LW[wifi.py]
        LD[diagnostics.py]
        LS[system.py]
    end

    subgraph "Tietovirta"
        GUI -- "1. Käynnistää taustatehtävän" --> Thread[Worker-säie]
        Thread -- "2. Kutsuu logiikkaa" --> Logic
        Logic -- "3. Suorittaa komennon" --> CMD[Järjestelmäkomennot <br/>(netsh, ipconfig, wmic)]
        CMD -- "4. Tulos" --> Logic
        Logic -- "5. Tulos" --> Thread
        Thread -- "6. Lähettää viestin" --> Queue(Task Queue)
        Queue -- "7. Käsittelee viestin" --> GUI
        GUI -- "8. Päivittää UI:n" --> GUI
    end

```