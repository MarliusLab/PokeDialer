# PokeDialer — Marlius' Lab

**Versione 3.1.5 · PokeDialer Offline per Android · Modifica indipendente (non ufficiale)**

Questa repository contiene i sorgenti di manutenzione, le patch e le istruzioni dell'edizione Marlius+ di PokeDialer. La versione 3.1.5 aggiunge un effetto sonoro di aumento di livello al popup di benvenuto con Red e Green. La base Android è di PokeDialer originale, sviluppato da **Alen Ajam**: Marlius è il creatore di questa edizione modificata, non del software originale.

## Stato

- APK 3.1.5 costruito e firmato localmente con la **stessa chiave delle build Marlius 3.1.x**; versionCode `310005`.
- Requisito minimo dichiarato: Android 7.0 (API 24), targetSdk 30.
- Funzionamento offline, nessun permesso Internet.
- Catalogo di 1.025 specie Pokémon con forme e varianti incluse, 11 avatar e 105 ritratti per contatti.
- 30 tracce musicali di gioco conservate e byte-identiche alla 3.1.4.
- Profili contatto, temi, ricerca, preferiti, anteprima, backup e diagnostica.
- Popup Red/Green con titolo PokeDialer, crediti Marlius e Chiquita, pulsante Continua e nuovo jingle di level-up retro.
- Controlli statici superati (integrità ZIP e DEX, APK Signature Scheme v2, impronta del certificato, versionName/versionCode, risorse). **Manca il collaudo effettivo su dispositivi Android.**

## Distribuzione e sorgenti

La repository pubblica è mantenuta *source-only*: non contiene chiavi private di firma, ROM né l'APK con risorse grafiche e musicali dei giochi. La pubblicazione di tali risorse o delle build complete richiede una verifica autonoma dei diritti di distribuzione. Non è un prodotto ufficiale Nintendo o The Pokémon Company.

Questa repository conserva le patch e il codice di manutenzione, **non** il progetto Android originale completo. Per riprodurre l'APK bisogna possedere la build precedente, il backup di firma privato e un ambiente Python con `cryptography`, `numpy` e `ffmpeg`:

```bash
python src/scripts/generate_levelup.py --out-dir build --name pd_marlius_welcome_v3
python src/scripts/package_sign.py \
  --base /percorso/PokeDialer_3.1.4_Marlius_Final.apk \
  --signing-backup /percorso/PokeDialer_Marlius_Firma_e_Modifiche_PRIVATO.zip \
  --sound build/pd_marlius_welcome_v3.ogg \
  --output PokeDialer_3.1.5_Marlius_LevelUp.apk
```

**Non caricare mai il backup privato di firma su GitHub.** Prima di installare l'APK firmato, fare un backup delle impostazioni: il collaudo Android 17 e sui vari produttori non è ancora completato.

## Documentazione

- [`CHANGELOG.md`](CHANGELOG.md) — versioni e modifiche.
- [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) — collaudo della telefonia e del nuovo popup.
- [`docs/PUBLISH.md`](docs/PUBLISH.md) — gestione delle release.
- [`docs/SECURITY.md`](docs/SECURITY.md) — protezione chiavi e dati.

## Crediti

**Marlius** — Creatore dell'edizione modificata, aggiornamenti e fix.

**Chiquita** — Riconoscimenti e tester.

**Alen Ajam** — Autore originale di PokeDialer.
