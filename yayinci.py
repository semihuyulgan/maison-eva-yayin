#!/usr/bin/env python3
"""Maison Eva yayıncı: zamanı gelen hazır içeriği Instagram'a bir kez yayımlar.

Çalışma ortamı GitHub Actions. Token yalnızca IG_TOKEN ortam değişkeninden gelir,
hiçbir yere yazılmaz. Durum takvim.json içinde tutulur ve her adımda commit edilir:
    hazir -> isleniyor -> yayinda / hata / belirsiz
'isleniyor' veya 'belirsiz' kalan içerik otomatik yeniden denenmez; çift paylaşımı
önlemek için elle kontrol gerekir.

Kullanım:
    yayinci.py --deneme   Yalnızca neyin yayımlanacağını gösterir, API'ye yazmaz.
    yayinci.py            Zamanı gelenleri yayımlar.
"""
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IG_ID = "17841426632497650"
API = "https://graph.instagram.com"
KOK = pathlib.Path(__file__).resolve().parent
TAKVIM = KOK / "takvim.json"
GECIKME_SINIRI = dt.timedelta(hours=6)


class ApiHatasi(Exception):
    pass


def istek(yol, veri=None, token="", sorgu=None):
    """veri verilirse POST, verilmezse sorgu alanlarıyla GET yapar."""
    alanlar = dict(veri or sorgu or {}, access_token=token)
    kodlu = urllib.parse.urlencode(alanlar)
    if veri is None:
        talep = urllib.request.Request(f"{API}/{yol}?{kodlu}")
    else:
        talep = urllib.request.Request(f"{API}/{yol}", data=kodlu.encode())
    try:
        with urllib.request.urlopen(talep, timeout=60) as yanit:
            return json.load(yanit)
    except urllib.error.HTTPError as hata:
        ayrinti = json.load(hata).get("error", {})
        raise ApiHatasi(f"{hata.code}: {ayrinti.get('message')} (kod {ayrinti.get('code')})") from None


def hazir_bekle(kap, token):
    for _ in range(30):
        durum = istek(kap, token=token, sorgu={"fields": "status_code"})
        kod = durum.get("status_code")
        if kod == "FINISHED":
            return
        if kod in ("ERROR", "EXPIRED"):
            raise ApiHatasi(f"Medya işlenemedi: {kod}")
        time.sleep(10)
    raise ApiHatasi("Medya zamanında hazır olmadı")


def kap_olustur(k, taban, token):
    adresler = [f"{taban}/{g}" for g in k["gorseller"]]
    if k["tur"] == "hikaye":
        kap = istek(f"{IG_ID}/media", {"media_type": "STORIES", "image_url": adresler[0]}, token)["id"]
        hazir_bekle(kap, token)
        return kap
    if k["tur"] == "reels":
        kap = istek(f"{IG_ID}/media", {"media_type": "REELS", "video_url": adresler[0], "caption": k.get("aciklama", ""), "share_to_feed": "true"}, token)["id"]
        hazir_bekle(kap, token)
        return kap
    if k["tur"] == "gorsel":
        kap = istek(f"{IG_ID}/media", {"image_url": adresler[0], "caption": k.get("aciklama", "")}, token)["id"]
        hazir_bekle(kap, token)
        return kap
    cocuklar = []
    for adres in adresler:
        c = istek(f"{IG_ID}/media", {"image_url": adres, "is_carousel_item": "true"}, token)["id"]
        hazir_bekle(c, token)
        cocuklar.append(c)
    kap = istek(f"{IG_ID}/media", {"media_type": "CAROUSEL", "children": ",".join(cocuklar), "caption": k.get("aciklama", "")}, token)["id"]
    hazir_bekle(kap, token)
    return kap


def kaydet(takvim, mesaj, gonder):
    TAKVIM.write_text(json.dumps(takvim, ensure_ascii=False, indent=1), encoding="utf-8")
    if gonder:
        subprocess.run(["git", "add", TAKVIM.name], cwd=KOK, check=True)
        subprocess.run(["git", "commit", "-m", mesaj], cwd=KOK, check=True)
        subprocess.run(["git", "push"], cwd=KOK, check=True)


def main():
    deneme = "--deneme" in sys.argv
    takvim = json.loads(TAKVIM.read_text(encoding="utf-8"))
    simdi = dt.datetime.now(dt.timezone.utc)
    zamani_gelen = [k for k in takvim if k["durum"] == "hazir" and dt.datetime.fromisoformat(k["zaman"]) <= simdi]
    kacirilan = [k for k in zamani_gelen if simdi - dt.datetime.fromisoformat(k["zaman"]) > GECIKME_SINIRI]
    siradakiler = [k for k in zamani_gelen if k not in kacirilan]
    eksik = [k["id"] for k in takvim if k["durum"].endswith("-bekliyor") and dt.datetime.fromisoformat(k["zaman"]) <= simdi]
    print(f"Zamanı gelen: {len(siradakiler)}, kaçırılan: {len(kacirilan)}, görseli olmadığı için atlanan: {len(eksik)}")
    if deneme:
        for k in siradakiler:
            print("YAYIMLANACAK", k["id"], k["gorseller"])
        ileride = [k for k in takvim if k["durum"] == "hazir"][:5]
        for k in ileride:
            print("SIRADA", k["id"], k["zaman"])
        return

    token = os.environ["IG_TOKEN"]
    taban = os.environ["MEDYA_TABAN"].rstrip("/")
    hata_var = False
    for k in kacirilan:
        k["durum"] = "kacirildi"
    if kacirilan:
        kaydet(takvim, "Kaçırılan içerikler işaretlendi", True)
        hata_var = True
    for k in siradakiler:
        k["durum"] = "isleniyor"
        kaydet(takvim, f"{k['id']} işleniyor", True)
        try:
            kap = kap_olustur(k, taban, token)
        except (ApiHatasi, KeyError, OSError) as hata:
            k["durum"], k["hata"] = "hata", str(hata)
            kaydet(takvim, f"{k['id']} hata", True)
            print("HATA", k["id"], hata)
            hata_var = True
            continue
        try:
            sonuc = istek(f"{IG_ID}/media_publish", {"creation_id": kap}, token)
            k["durum"], k["medya_id"] = "yayinda", sonuc["id"]
            k["yayin_zamani"] = dt.datetime.now(dt.timezone.utc).isoformat()
            print("YAYINDA", k["id"], sonuc["id"])
        except (ApiHatasi, KeyError, OSError) as hata:
            k["durum"], k["hata"] = "belirsiz", str(hata)
            print("BELİRSİZ", k["id"], hata)
            hata_var = True
        kaydet(takvim, f"{k['id']} {k['durum']}", True)
    if hata_var:
        sys.exit(1)


if __name__ == "__main__":
    main()
