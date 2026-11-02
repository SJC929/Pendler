"""Lädt die Velo- und Fussgängerzählungen von Basel-Stadt herunter."""
from pathlib import Path
import requests

JAHR = 2025
URL = f"https://data-bs.ch/mobilitaet/{JAHR}_Velo_Fuss_Count.csv"
ZIEL = Path(__file__).parent / "data" / "raw" / f"{JAHR}_Velo_Fuss_Count.csv"


def herunterladen(url, ziel):
    ziel.parent.mkdir(parents=True, exist_ok=True)
    print(f"Lade {url} …")

    with requests.get(url, stream=True, timeout=60) as antwort:
        antwort.raise_for_status()
        with open(ziel, "wb") as datei:
            for stueck in antwort.iter_content(chunk_size=1024 * 1024):
                datei.write(stueck)
                print(".", end="", flush=True)  # ein Punkt pro MB

    groesse_mb = ziel.stat().st_size / 1024 / 1024
    print(f"\nFertig: {ziel} ({groesse_mb:.1f} MB)")


if __name__ == "__main__":
    herunterladen(URL, ZIEL)