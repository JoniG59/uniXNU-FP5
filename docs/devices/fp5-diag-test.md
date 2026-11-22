# FP5: Diagnose „kurz Log, dann schwarzer Bildschirm“

Stand 2026-11-22. **Keines der Images ist auf Hardware getestet.** Alle nur per `fastboot boot <img>` (RAM) starten –
nie flashen, kein Slot-Wechsel. Nach jedem Versuch: Power lange drücken (ca. 10–15 s) → normaler Neustart ins Android.

## Beobachtung

`boot-unixnu.img` (Header v3): ca. 1 s laufen Logzeilen durch, danach bleibt der Bildschirm schwarz.

## Was man daraus schon ablesen kann (statische Analyse)

- **Framebuffer-Adresse stimmt sehr wahrscheinlich.** Die Logzeilen kommen aus `FrameBufferSerialPortLib`, die in
  „Display Reserved“ (0xE1000000) schreibt; laut FP5-DTB liegt dort `splash_region` (0xE1000000–0xE3300000) plus
  `dfps_data_memory` (bis 0xE3400000). Wären Adresse/Breite falsch, wäre gar nichts lesbar gewesen.
- Display-Treiber ist `SimpleFbDxe` (kein Neu-Programmieren des Panels, `USE_CUSTOM_DISPLAY_DRIVER = 0`).
- Asserts/Exceptions bleiben im DEBUG-Build stehen (`PcdDebugPropertyMask = 0x2F`, enthält DEADLOOP) und würden
  normalerweise auf dem Bildschirm sichtbar bleiben. **Schwarz heißt daher vermutlich (Hypothese):** Panel/Display
  wurde abgeschaltet, das Gerät wurde zurückgesetzt bzw. ist in einen Qualcomm-Crash-/Dump-Modus gefallen, oder ein
  späterer Schritt hat den Bildschirm gelöscht und zeichnet nichts mehr.
- Einziger struktureller Unterschied zu den funktionierenden Kodiak-Referenzen (spacewar, gleicher SoC-Familie):
  FP5 hat den **DXE Heap bei 0x9C700000** (Stock-uefiplat), spacewar bei **0xE3400000** (hinter Display Reserved).
  Ob das die Ursache ist: **offen** → Variante D.
- Weitere offene Risiken: TzDxeLA ungepatcht, Qualcomm-DXE aus VT32 bei evtl. VT31-Bootloader, Header v3 kombiniert
  ABL mit dem geflashten `vendor_boot`.

## Diagnose-Images (`out/fp5-mu/diag/`, nur lokal)

Alle mit **0,15 s Pause pro Logzeile** (`PcdFrameBufferDelay = 150000`), damit das Log lesbar bleibt.

| Datei | Inhalt | prüft |
|---|---|---|
| `diag-A-mu-v3.img` | Mu ohne UniXNU, Header v3 | Liegt es am Basis-Port oder an UniXNU? |
| `diag-B-mu-v1.img` | wie A, Header v1 (wie früheres `noot.img`) | Liegt es an Header v3 / `vendor_boot`-Kombination? |
| `diag-C-unixnu-v3.img` | wie `boot-unixnu.img`, nur mit Pause | Genau ablesen, wo es schwarz wird |
| `diag-D-mu-dxeheap-v3.img` | wie A, DXE Heap bei 0xE3400000 (wie spacewar) | Ist die DXE-Heap-Lage das Problem? |

Prüfsummen: `out/fp5-mu/diag/SHA256SUMS`, Details: `out/fp5-mu/diag/diag.json` (`hardware_tested: false`).

## Reihenfolge und worauf achten

1. **C** zuerst: Bildschirm mit einer zweiten Handy-Kamera **filmen** (am besten Zeitlupe). Die **letzten 5–10
   Zeilen vor dem Schwarzwerden** sind das Wichtigste.
2. Dann **A**, **B**, **D** – jeweils filmen.

Bei jedem Versuch notieren:

- Wird es schwarz? Nach wie vielen Sekunden / nach welcher Zeile?
- Startet das Gerät von selbst neu (Fairphone-Logo erscheint wieder)?
- Vibration, Benachrichtigungs-LED?
- Optional am **PC** (nicht am Telefon): erscheint per `lsusb` ein Gerät `05c6:900e` (Qualcomm Crash-/Dump-Modus)
  oder `05c6:9008` (EDL)? Das würde einen Absturz in TrustZone/Hypervisor statt eines reinen Anzeigeproblems nahelegen.

## Auswertung

| Ergebnis | wahrscheinliche Richtung (Hypothese) |
|---|---|
| A läuft (Mu-Menü/Logo), C nicht | Problem in UniXNU/DarwinBoot |
| A und C schwarz, B läuft | Header v3 / `vendor_boot`-Kombination → v1 verwenden |
| A schwarz, D läuft | DXE-Heap-Lage → auf 0xE3400000 umstellen |
| alle schwarz an derselben Stelle | Qualcomm-DXE-Treiber (Zeile davor nennt ihn), TzDxe, PMIC/Clock |
| alle schwarz, `05c6:900e` am PC | Zugriffsverletzung (XPU/TZ) – Speicherbereich oder Treiber |

Video/Fotos oder abgetippte letzte Zeilen zurückmelden; daraus ergibt sich der nächste Fix.
