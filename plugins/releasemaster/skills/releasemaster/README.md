# ReleaseMaster — Claude Skill

Mühendis + editör + release manager rollerini birleştiren Claude skill'i: değişiklikleri analiz eder, dokümantasyonu üretir/günceller, sürüm notu ve changelog hazırlar. Çoklu repo (backend / frontend / mobil) ürünlerini tek bir ürün olarak ele alır.

## Kurulum

| Kapsam | Konum |
|---|---|
| Kullanıcı (tüm projeler) | `%USERPROFILE%\.claude\skills\releasemaster\` (Win) · `~/.claude/skills/releasemaster/` |
| Workspace (ekip, git ile paylaşılır) | `<workspace>/.claude/skills/releasemaster/` |
| claude.ai / masaüstü | Klasörü zip'leyip Settings → Capabilities → Skills'ten yükle |

```powershell
# Windows, kullanıcı kapsamı
Copy-Item -Recurse .\releasemaster "$env:USERPROFILE\.claude\skills\releasemaster"
```

Gereksinimler: `git`, Python 3.8+ (ek paket yok).

## İlk kullanım

```
/releasemaster init
```
Repoları tarar, mevcut dokümantasyonu sorar, `.releasemaster/releasemaster.config.json` dosyasını oluşturur. Bu dosya skill'in hafızasıdır (repolar, doküman dizini, son sürüm bilgisi) — git'e commit'lenirse ekip aynı bilgiyi kullanır.

## Komutlar

| Komut | Ne yapar |
|---|---|
| `init` | Kurulum sihirbazı |
| `status` | Repolar, son sürüm, son sürümden beri commit sayıları |
| `analyze [aralık]` | Teknik analiz (breaking change, migration, config, risk) — dosya yazmaz |
| `notes [aralık] [--platform] [--audience]` | Sürüm notu (varsayılan: ürün bazlı, platform etiketli) |
| `changelog [aralık]` | CHANGELOG.md günceller (Keep a Changelog) |
| `docs init compact\|basic\|full` | Sıfırdan dokümantasyon |
| `docs update [aralık]` | Son değişikliklerden etkilenen dokümanları günceller |
| `release [versiyon]` | Uçtan uca sürüm hazırlığı + checklist |
| `config` | Ayarları göster/değiştir |

Aralık örnekleri: `son sürümden beri`, `v1.4.0'dan beri`, `1 Ekim'den beri`, `a1b2c3d commit'inden beri`, `api=v1.4.0..HEAD mobile=9c8d7e6..develop`. Belirtilmezse skill duruma göre önerir ve onay ister.

Her dosya yazımı öncesi önizleme/diff gösterilir ve onay alınır (`approval` ayarı ile değiştirilebilir).

## Claude (claude.ai / masaüstü) ile kullanım

claude.ai'da skill bir sandbox'ta çalışır ve diskindeki repoları göremez. Git geçmişini tek zip olarak götürürsün:

```powershell
# çalışma alanı kökünde (git + Python gerekir)
python <skill-klasörü>\scripts\portable.py export
# config henüz yoksa: python ...\portable.py export --repo ..\api --repo ..\web
```
Oluşan `releasemaster-upload.zip` dosyasını sohbete ekle ve "son sürüm notundan sonrası için sürüm notu hazırla" de. Zip yalnızca **commit'leri** taşır (tüm dallar ve etiketler), commit'lenmemiş değişiklikler dahil değildir. İş bitince Claude yeni dosyaları ve güncellenmiş `.releasemaster/releasemaster.config.json` dosyasını sana geri verir; ikisini repoya koyup commit'lersin. Slash komutları yalnızca Claude Code'dadır; claude.ai'da aynı işi sözle istersin.

## Yapı

```
SKILL.md                    ana talimatlar
references/                 setup, config şeması, sürüm notu, dokümantasyon, editoryal stil
templates/                  README, docs-basic seti, CHANGELOG, release notes iskeletleri
scripts/digest.py           PR bazlı özet + repolar arası bağlantı + risk checklist'i (quick/standard/deep)
scripts/portable.py        repo geçmişini tek zip'e paketler / sandbox'ta açar (claude.ai için)
scripts/verify.py          sürüm notu/CHANGELOG taslağındaki PR, endpoint, config anahtarı, migration, hash iddialarını repolara karşı doğrular
scripts/collect_changes.py  çoklu repo commit toplama (tag / tarih / commit / son sürüm / --timeline)
scripts/detect_project.py   stack, doküman, versiyonlama tespiti
```
