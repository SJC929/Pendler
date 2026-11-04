"""
Trainiert EIN Modell für alle Basler Trams und Busse (BVB + BLT) und schreibt
das Verspätungsrisiko für die nächsten 7 Tage in die Datenbank (Tabelle basel_prognose).
"""
import importlib

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sqlalchemy import text

from datenbank import verbinden

prognose48 = importlib.import_module("09_prognose")      # Wetterprognose, Ferien, heute()
aufbereiten = importlib.import_module("11_aufbereiten")  # MeteoSchweiz-Adresse

GLAETTUNG = 20      # wenige Abfahrten → Quote Richtung Durchschnitt ziehen
TAGE = 7
MERKMALE = ["stunde", "wochentag", "wochenende", "schulferien", "temp", "regen_mm",
            "quote_halt", "quote_stunde"]

PROGNOSE_TABELLE = """
CREATE TABLE IF NOT EXISTS basel_prognose (
    datum        DATE NOT NULL,
    betreiber    TEXT NOT NULL,
    linie        TEXT NOT NULL,
    haltestelle  TEXT NOT NULL,
    ziel         TEXT NOT NULL,
    stunde       SMALLINT NOT NULL,
    risiko       SMALLINT NOT NULL,
    PRIMARY KEY (datum, betreiber, linie, haltestelle, ziel, stunde)
)
"""


# ---------- Daten ----------

def laden(engine):
    daten = pd.read_sql("SELECT * FROM basel_stunden", engine, parse_dates=["datum"])
    print(f"✅ Geladen: {len(daten)} Zeilen, {daten['datum'].nunique()} Tage, "
          f"{daten['linie'].nunique()} Linien, {daten['abfahrten'].sum()} Abfahrten")
    return daten


def wetter_vergangenheit():
    roh = pd.read_csv(aufbereiten.WETTER_URL, sep=";")
    roh["zeit"] = (
        pd.to_datetime(roh["reference_timestamp"], format="%d.%m.%Y %H:%M")
        .dt.tz_localize("UTC").dt.tz_convert("Europe/Zurich").dt.tz_localize(None)
    )
    codes = aufbereiten.WETTER_CODES
    return roh[["zeit", *codes]].rename(columns=codes).drop_duplicates("zeit")


def zeit_merkmale(df, wetter, ferien):
    df = df.copy()
    df["wochentag"] = df["datum"].dt.day_of_week
    df["wochenende"] = (df["wochentag"] >= 5).astype(int)
    df["schulferien"] = df["datum"].isin(ferien).astype(int)
    df["zeit"] = df["datum"] + pd.to_timedelta(df["stunde"], unit="h")
    return df.merge(wetter, on="zeit", how="left")


# ---------- «Wie oft war es hier früher zu spät?» ----------

def quoten(train):
    gesamt = train["zu_spaet"].sum() / train["abfahrten"].sum()

    def quote(spalten, name):
        g = train.groupby(spalten)[["zu_spaet", "abfahrten"]].sum()
        g[name] = (g["zu_spaet"] + GLAETTUNG * gesamt) / (g["abfahrten"] + GLAETTUNG)
        return g[[name]].reset_index()

    tabellen = [
        quote(["linie", "haltestelle", "ziel"], "quote_halt"),     # diese Haltestelle
        quote(["linie", "ziel", "stunde"], "quote_stunde"),        # diese Linie zu dieser Stunde
    ]
    return gesamt, tabellen


def quoten_dazu(df, gesamt, tabellen):
    for t in tabellen:
        schluessel = [c for c in t.columns if not c.startswith("quote")]
        df = df.merge(t, on=schluessel, how="left")
    df[["quote_halt", "quote_stunde"]] = df[["quote_halt", "quote_stunde"]].fillna(gesamt)
    return df


# ---------- Modell ----------

def als_einzelne(df):
    """«2 von 9 zu spät» → Zeile «zu spät» mit Gewicht 2 + Zeile «pünktlich» mit Gewicht 7."""
    ja = df[df["zu_spaet"] > 0].assign(y=1, gewicht=lambda d: d["zu_spaet"])
    nein = df[df["abfahrten"] > df["zu_spaet"]].assign(y=0, gewicht=lambda d: d["abfahrten"] - d["zu_spaet"])
    return pd.concat([ja, nein], ignore_index=True)


def trainieren(df):
    e = als_einzelne(df)
    modell = HistGradientBoostingClassifier(random_state=42, max_iter=200)
    modell.fit(e[MERKMALE], e["y"], sample_weight=e["gewicht"])
    return modell


def bewerten(daten):
    """Letzte 7 Tage als Test: ist das Modell besser als die einfache Quote?"""
    grenze = daten["datum"].max() - pd.Timedelta(days=6)
    train, test = daten[daten["datum"] < grenze], daten[daten["datum"] >= grenze]
    if train["datum"].nunique() < 7:
        print("ℹ️ Noch zu wenige Tage für eine Bewertung (mind. 14 nötig)")
        return

    gesamt, tabellen = quoten(train)
    modell = trainieren(quoten_dazu(train, gesamt, tabellen))
    e = als_einzelne(quoten_dazu(test, gesamt, tabellen))

    auc_modell = roc_auc_score(e["y"], modell.predict_proba(e[MERKMALE])[:, 1], sample_weight=e["gewicht"])
    auc_basis = roc_auc_score(e["y"], e["quote_stunde"], sample_weight=e["gewicht"])
    print(f"📊 Test-Woche: Baseline AUC {auc_basis:.3f} · Modell AUC {auc_modell:.3f}")


# ---------- Prognose ----------

def zukunft(daten, gesamt, tabellen):
    """Alle Fahrten der letzten 4 Wochen (getrennt Werktag/Wochenende) für die nächsten 7 Tage."""
    letzte = daten[daten["datum"] > daten["datum"].max() - pd.Timedelta(days=28)].copy()
    letzte["tagtyp"] = letzte["datum"].dt.day_of_week >= 5
    kombis = letzte[["betreiber", "linie", "haltestelle", "ziel", "stunde", "tagtyp"]].drop_duplicates()

    start = prognose48.heute()
    tage = pd.DataFrame({"datum": pd.date_range(start, periods=TAGE)})
    tage["tagtyp"] = tage["datum"].dt.day_of_week >= 5

    ferien = prognose48.ferientage_holen(start, start + pd.Timedelta(days=TAGE))
    zeilen = tage.merge(kombis, on="tagtyp")
    zeilen = zeit_merkmale(zeilen, prognose48.wetter_holen(), ferien)
    return quoten_dazu(zeilen, gesamt, tabellen)


def speichern(engine, zeilen):
    aus = zeilen[["datum", "betreiber", "linie", "haltestelle", "ziel", "stunde", "risiko"]].copy()
    aus["datum"] = aus["datum"].dt.date
    with engine.begin() as conn:                     # alles in einem Schritt → App sieht nie eine leere Tabelle
        conn.execute(text(PROGNOSE_TABELLE))
        conn.execute(text("CREATE INDEX IF NOT EXISTS prognose_halt ON basel_prognose (haltestelle, datum)"))
        conn.execute(text("DELETE FROM basel_prognose"))
        aus.to_sql("basel_prognose", conn, if_exists="append", index=False, method="multi", chunksize=2000)
    print(f"✅ Gespeichert: {len(aus)} Prognosen in basel_prognose")


def main():
    engine = verbinden()
    if engine is None:
        raise SystemExit("❌ DATABASE_URL nicht gefunden")

    daten = laden(engine)
    ferien = prognose48.ferientage_holen(daten["datum"].min().date(), daten["datum"].max().date())
    daten = zeit_merkmale(daten, wetter_vergangenheit(), ferien)

    bewerten(daten)

    gesamt, tabellen = quoten(daten)
    modell = trainieren(quoten_dazu(daten, gesamt, tabellen))
    print("✅ Modell trainiert (alle Tage)")

    zeilen = zukunft(daten, gesamt, tabellen)
    zeilen["risiko"] = (modell.predict_proba(zeilen[MERKMALE])[:, 1] * 100).round().astype(int)
    speichern(engine, zeilen)

    print("\n🔴 Höchstes Risiko in den nächsten 7 Tagen:")
    for z in zeilen.nlargest(5, "risiko").itertuples():
        print(f"   {z.datum:%a %d.%m.} {z.stunde:02d} Uhr  Linie {z.linie:4s} {z.haltestelle[:22]:22s} → {z.ziel[:18]:18s} {z.risiko} %")


if __name__ == "__main__":
    main()