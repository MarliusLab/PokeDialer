# Patch del popup v3.1.5

La patch effettiva dei metodi DEX è prodotta da `src/scripts/patch_dex_levelup.py`.

Il metodo `WelcomeCredits.showOnce(Activity)` nella classe `classes3.dex` viene modificato in modo da:

1. Conservare il popup e le preferenze di visualizzazione una sola volta.
2. Usare il nuovo identificatore di preferenze `pd_marlius_welcome_v3` per riproporre il popup dopo l'aggiornamento.
3. Estrarre il piccolo OGG `assets/pd_marlius_welcome_v3` in cache privata e riprodurlo tramite MediaPlayer.
4. Avviare il file solo dopo la visualizzazione del popup e dopo il salvataggio del flag.
5. Catturare le eccezioni di riproduzione senza compromettere il funzionamento del dialer.
6. Rilasciare il MediaPlayer al completamento tramite il callback già presente nell'app, mantenendo il suo comportamento precedente se invocato da altri moduli.

Il DEX viene modificato senza alterare gli altri metodi, le 30 musiche preesistenti o le immagini.
