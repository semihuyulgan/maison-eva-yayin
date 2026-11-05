#!/usr/bin/env python3
"""Maison Eva: 4 haftalık yayın takvimini üretir (takvim.json + takvim.md).

Günler proje kararından gelir; saatler başlangıç varsayımıdır, ilk ayın
istatistiklerine göre değiştirilecek. Tüm saatler Europe/Istanbul.
"""
import datetime as dt
import json
import pathlib

BASLANGIC = dt.date(2026, 11, 6)
GUN_SAYISI = 28
CAROUSEL_SAATI = {0: "19:00", 2: "18:00", 4: "16:00", 5: "11:00", 6: "14:00"}
HIKAYE_SAATLERI = ["10:00", "15:00", "20:30"]
GUN_ADI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

ALT = "Tarihinizi ve kişi sayınızı DM'den paylaşın, detayları birlikte konuşalım. 0534 685 01 57 · Meriç, Bornova"

# (konu, tür, açıklama). Sıra yayın sırasıdır; ilk satırın görselleri hazır (paket-01).
CAROUSELLER = [
    ("Nişan akşamı", "nisan", "Sevdiklerinizle kutlayacağınız bir nişan akşamı."),
    ("Kız çocuğu doğum günü", "kiz", "Çocuğunuzun doğum günü için aynı salonun gündüz hâli."),
    ("Salon gündüz", "mekan", "Gün ışığında salonumuz. Kapasitemiz 100 kişi."),
    ("Salon seçerken 5 soru", "bilgi", "Salon bakarken bu 5 soruyu sormayı unutmayın. Kaydedin, lazım olur."),
    ("Erkek çocuğu doğum günü", "erkek", "Gün ışığında, bol koşturmacalı bir doğum günü fikri."),
    ("İsteme merasimi", "isteme", "Aileler için sıcak ve sade bir isteme düzeni."),
    ("Bir salon, iki hâl", "donusum", "Aynı salon: akşam nişan, gündüz doğum günü."),
    ("Detaylar", "detay", "Perde, çiçek, şamdan. Küçük detaylar kutlamanın havasını değiştirir."),
    ("Kız çocuğu pastel tema", "kiz", "Pastel tonlarda bir doğum günü fikri."),
    ("Rezervasyon nasıl yapılır", "bilgi", "Rezervasyon üç adımda: tarih, kişi sayısı, görüşme."),
    ("Nişan: aile anları", "nisan", "En güzel kareler planlanmayanlar."),
    ("Erkek çocuğu macera teması", "erkek", "Yıldızlar, balonlar ve bol koşturmaca için bir doğum günü fikri."),
    ("50 kişi mi, 100 kişi mi", "bilgi", "Aynı salon, iki farklı düzen. Kişi sayınıza göre planlayalım."),
    ("Küçük kutlamalar", "kutlama", "Yıl dönümü, mezuniyet, aile buluşması. Küçük kutlamalar için de buradayız."),
    ("Salon akşam", "mekan", "Işıklar kısıldığında salonumuz."),
    ("Kız çocuğu doğum günü: pasta anı", "kiz", "Mumlar üflenmeden önceki o an."),
    ("Mekân kiralamaya ne dahil", "bilgi", "Kiralamaya alan ve müzik sistemi dahildir. Pasta, ikram ve içecek seçeneklerini talebinize göre ayrıca planlayabiliriz."),
    ("İsteme: masa düzeni", "isteme", "Sade, özenli bir isteme masası."),
    ("Erkek çocuğu doğum günü: oyun anı", "erkek", "Gün ışığında bol kahkahalı bir kutlama fikri."),
    ("Aralık tarihleri", "cagri", "Aralık için tarih düşünüyorsanız şimdiden konuşalım."),
]

HIKAYE_DONGU = [
    ("gunun-karesi", "Günün carousel'inden bir kare, 'yeni gönderi' metniyle"),
    ("bilgi-soru", "Kısa bilgi: kapasite, konum, kiralama veya etkinlik sorusu"),
    ("cagri", "Akşam çağrısı: tarih ve kişi sayısı, telefon"),
]


def main():
    kok = pathlib.Path(__file__).resolve().parent
    kuyruk = []
    siradaki = 0
    for g in range(GUN_SAYISI):
        gun = BASLANGIC + dt.timedelta(days=g)
        hafta_gunu = gun.weekday()
        for i, saat in enumerate(HIKAYE_SAATLERI):
            kod, not_ = HIKAYE_DONGU[i]
            kimlik = f"{gun}-hikaye-{i + 1}"
            hazir = g == 0
            kuyruk.append({
                "id": kimlik, "tur": "hikaye", "zaman": f"{gun}T{saat}:00+03:00", "konu": not_, "tema": kod,
                "gorseller": [f"medya/paket-01/hikaye-{i + 1}.jpg"] if hazir else [],
                "durum": "hazir" if hazir else "gorsel-bekliyor",
            })
        if hafta_gunu in CAROUSEL_SAATI:
            konu, tema, metin = CAROUSELLER[siradaki]
            hazir = siradaki == 0
            kuyruk.append({
                "id": f"{gun}-carousel", "tur": "carousel",
                "zaman": f"{gun}T{CAROUSEL_SAATI[hafta_gunu]}:00+03:00",
                "konu": konu, "tema": tema, "aciklama": f"{metin}\n\n{ALT}",
                "gorseller": [f"medya/paket-01/carousel-{n}.jpg" for n in range(1, 5)] if hazir else [],
                "durum": "hazir" if hazir else "gorsel-bekliyor",
            })
            siradaki += 1
    kuyruk.sort(key=lambda k: k["zaman"])
    (kok / "takvim.json").write_text(json.dumps(kuyruk, ensure_ascii=False, indent=1), encoding="utf-8")

    satirlar = ["# Maison Eva yayın takvimi", "", f"{BASLANGIC} ile başlayan 4 hafta. Saatler Türkiye saati. Hikâyeler her gün 10:00, 15:00, 20:30.", "", "| Tarih | Gün | Saat | Carousel |", "|---|---|---|---|"]
    for k in kuyruk:
        if k["tur"] == "carousel":
            t = dt.datetime.fromisoformat(k["zaman"])
            satirlar.append(f"| {t:%d.%m} | {GUN_ADI[t.weekday()]} | {t:%H:%M} | {k['konu']} |")
    (kok / "takvim.md").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print(len([k for k in kuyruk if k["tur"] == "carousel"]), "carousel,", len([k for k in kuyruk if k["tur"] == "hikaye"]), "hikâye")


if __name__ == "__main__":
    main()
