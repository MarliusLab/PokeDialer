# Sicurezza del progetto

- La chiave di firma è privata, conservata esclusivamente nell'archivio `PokeDialer_Marlius_Firma_e_Modifiche_PRIVATO.zip` fuori dalla repository. Mai caricarla su GitHub.
- Per verificare l'aggiornabilità, confrontare SHA-256 del certificato di firma, non solo il nome del file APK.
- La patch 3.1.5 conserva l'assenza del permesso Internet. I report di diagnostica possono contenere dati sul dispositivo; rivederli prima di condividerli.
- Il backup JSON può includere numeri dei contatti e altre preferenze private: conservarlo in un luogo protetto.
- APK verificato staticamente, ma il collaudo dinamico dell'interfaccia telefonica è ancora necessario.
