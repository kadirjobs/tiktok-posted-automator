# Faz 3 — TikTok Content Posting API Minimum Uyum Planı

Bu belge, Posted Automator’un TikTok [Content Sharing Guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines) ile uyumlu **minimum** yayın akışını tanımlar.

> **Not:** Tam otomatik “Drive → anında public post” modeli TikTok’un “utility tool” tanımıyla çelişir. Faz 3’te hedef: **teknik upload + publish altyapısı** + **insan onaylı son adım**.

---

## 1. Hedef mod (MVP — unaudited client)

| Özellik | Değer |
|---------|--------|
| Görünürlük | `SELF_ONLY` (sadece ben) — varsayılan |
| Hesap | Tek kişisel hesap (`personal`) |
| Audit | Yok (şimdilik) |
| Public yayın | Audit sonrası ayrı faz |

---

## 2. Akış (önerilen)

```text
Drive sync → medya hazır → Admin "Onay kuyruğu"
    ↓
Kullanıcı önizleme + metadata + onay
    ↓
TikTok creator_info kontrolü
    ↓
Chunk upload → publish (SELF_ONLY)
    ↓
publish/status poll → tamamlandı
```

**Kritik:** TikTok API çağrısı (upload/publish) yalnızca kullanıcı **“Yayınla”** dedikten sonra.

---

## 3. Minimum onay ekranı (UI gereksinimleri)

Tek sayfa: `GET /admin/publish/{post_id}`

### 3.1 Gösterilmesi zorunlu bilgiler

| Alan | Kaynak | Kural |
|------|--------|--------|
| Bağlı TikTok hesabı (nickname) | `creator_info` API | Her zaman görünür |
| Video önizleme | local `storage/{post_id}/video.mp4` | Zorunlu |
| Caption / başlık | kullanıcı düzenleyebilir | Varsayılan Drive metni, silinebilir |
| Gizlilik | `privacy_level_options` | Dropdown, **varsayılan boş** — kullanıcı seçmeli |
| Yorum / Duet / Stitch | `creator_info` | Checkbox, **varsayılan kapalı** |
| Ticari içerik | toggle | **Varsayılan kapalı** |
| Süre uyarısı | `max_video_post_duration_sec` | Aşılırsa yayın engelle |

### 3.2 Yayın öncesi metin (checkbox + buton)

Kullanıcı işaretlemeden **Yayınla** pasif:

> By posting, you agree to TikTok's [Music Usage Confirmation](https://www.tiktok.com/legal/page/global/music-usage-confirmation/en).

Ticari içerik açıksa metin TikTok kurallarına göre güncellenir (Branded Content Policy).

### 3.3 Yayın sonrası

- “İşleniyor, profilinizde birkaç dakika içinde görünebilir” mesajı  
- `publish/status` poll veya webhook ile durum gösterimi  

---

## 4. API entegrasyon sırası (Faz 3 geliştirme)

| Sıra | Modül | Dosya (planlanan) |
|------|--------|-------------------|
| 1 | `creator_info` | `services/tiktok/creator.py` |
| 2 | Init upload + chunk | `chunker.py`, `uploader.py` |
| 3 | Publish | `publisher.py` |
| 4 | Status poll | `publisher.py` / `validator.py` |
| 5 | Onay UI | `api/publish_routes.py` + basit HTML şablon |

---

## 5. Otomasyon sınırları (bilinçli kısıt)

| Yapılacak | Yapılmayacak (audit öncesi) |
|-----------|------------------------------|
| Drive’dan otomatik hazırlık | Kullanıcı onayı olmadan publish |
| Kuyruğa alma (`queued` → `ready_for_review`) | Varsayılan `PUBLIC` görünürlük |
| `SELF_ONLY` ile test yayını | Toplu public burst |
| Token refresh (Faz 2) | Watermark / logo ekleme |

---

## 6. Veri modeli ekleri (MongoDB)

`posts` koleksiyonuna eklenecek alanlar:

```json
{
  "publish": {
    "privacy_level": null,
    "allow_comment": false,
    "allow_duet": false,
    "allow_stitch": false,
    "commercial_content_enabled": false,
    "user_consent_at": null,
    "tiktok_publish_id": null,
    "tiktok_share_id": null
  },
  "status": "ready_for_review"
}
```

Durum makinesi:

```text
downloaded → ready_for_review → publishing → published / failed
```

---

## 7. Test checklist (Faz 3 bitiş)

- [ ] `creator_info` nickname ekranda görünüyor  
- [ ] Gizlilik seçilmeden Yayınla disabled  
- [ ] Onay checkbox olmadan Yayınla disabled  
- [ ] Video önizleme çalışıyor  
- [ ] `SELF_ONLY` ile post oluşuyor  
- [ ] `publish/status` completed dönüyor  
- [ ] Günlük limit aşımında yayın engelleniyor  

---

## 8. Audit sonrası (Faz 6+)

- Public `privacy_level` seçenekleri  
- Gelişmiş ticari içerik UX  
- Çoklu hesap (politika ve kota izin verirse)  
- TikTok Content Posting API audit başvurusu  

---

## 9. TikTok formu için site URL’leri

GitHub Pages yayınladıktan sonra portalda:

| Alan | Örnek URL |
|------|-----------|
| Website | `https://[user].github.io/tiktok-posted-automator/` |
| Privacy Policy | `https://[user].github.io/tiktok-posted-automator/privacy-policy.html` |
| Terms of Service | `https://[user].github.io/tiktok-posted-automator/terms-of-service.html` |

`docs/` içindeki `.md` dosyalarından HTML üretilebilir veya repo root’ta `index.html` eklenebilir.
