# ReleaseMaster

[English](README.md) · **Türkçe**

Bir veya birden fazla git deposunun geçmişini okuyup sürüm notuna, changelog'a ve proje dokümantasyonuna çeviren Claude skill'i (aynı zamanda Claude Code plugin'i; Codex, Cursor, OpenCode ve Kimi Code ile de kullanılabilir). Commit mesajlarına değil, gerçekten ne değiştiğine bakar.

- **Mühendis:** Diff'leri okur: migration'lar, yeni config anahtarları, route'lar, bağımlılık değişiklikleri, kırıcı değişiklikler, incelemeden geçmeyen commit'ler.
- **Editör:** Projenin kendi biçiminde, dilinde ve tonunda yazar. Zaten sürüm notların varsa onların biçimini izler.
- **Release manager:** Aralığı seçer (son nottan / etiketten / tarihten / commit'ten), sürüm önerir, changelog'u tutar, en son neyin yayınlandığını hatırlar ve onayın olmadan hiçbir dosya yazmaz.

Bir ürün çoğu zaman birden fazla depodur (backend, web, mobil). ReleaseMaster bunları tek ürün sayar: tek doküman, maddelerde platform etiketi; platform bazlı not yalnızca sen istersen.

## Kurulum

**Claude Code (plugin, önerilen)**

```
/plugin marketplace add akkiris/releasemaster
/plugin install releasemaster@releasemaster
```

Oturumu yeniden başlat. `/releasemaster:` yazınca tüm komutlar açıklamalarıyla listelenir, ezberlemen gerekmez.

**Diğer araçlar: Codex, Cursor, OpenCode, Kimi Code**

Dördü de açık Agent Skills biçimini (içinde `SKILL.md` olan klasör) `.agents/skills/` altından okur, yani tek kopya dördüne yeter. Kurulum için Python gerekmez, klasörü kopyalaman yeterli:

```powershell
# Windows PowerShell
git clone https://github.com/akkiris/releasemaster.git
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force releasemaster\plugins\releasemaster\skills\releasemaster "$HOME\.agents\skills\releasemaster"
```

```bash
# macOS / Linux
git clone https://github.com/akkiris/releasemaster.git
mkdir -p ~/.agents/skills
cp -r releasemaster/plugins/releasemaster/skills/releasemaster ~/.agents/skills/releasemaster
```

Yalnızca tek proje için (git ile ekibe paylaşılır) `<proje>/.agents/skills/releasemaster` altına kopyala. Sonra aracı yeniden başlat.

Yalnızca OpenCode, isteğe bağlı: özel komutlar `/releasemaster-notes`, `/releasemaster-init`, …

```powershell
New-Item -ItemType Directory -Force "$HOME\.config\opencode\commands" | Out-Null
Copy-Item releasemaster\adapters\opencode\commands\*.md "$HOME\.config\opencode\commands\"
```

Betik mi tercih edersin? `python tools/install.py --for codex cursor opencode kimi` aynı işi yapar (`--scope project`, `--dry-run`, `--uninstall` var). İsteğe bağlıdır, başka hiçbir şey ona bağlı değil.

Claude Code'u **ve** Cursor/OpenCode'u birlikte kullanıyorsan: Claude plugin'ini yukarıdaki gibi kur ve `.agents/skills` kopyasını da yap. Skill'i ayrıca `.claude/skills` içine koyma; Cursor ve OpenCode o klasörü de okuduğu için skill iki kez listelenir.

**claude.ai / masaüstü uygulaması (skill yükleme)**

```
python tools/build_skill_zip.py        # dist/releasemaster-skill.zip üretir
```

Zip'i Settings → Capabilities → Skills bölümünden yükle. Depolarını nasıl vereceğin için [claude.ai ile kullanım](#claudeai-ile-kullanım) bölümüne bak.

Script'lerin çalıştığı makinede `git` ve Python 3.8+ yeterli, ek paket gerekmez.

## Komutlar

| Komut | Ne yapar | Dosya yazar mı |
|---|---|---|
| `/releasemaster:init` | Depoları, mevcut dokümanı ve önceki sürüm notunu tespit eder, config'i yazar | yalnızca config |
| `/releasemaster:status` | Depolar, son not/sürüm, ondan beri commit sayısı | hayır |
| `/releasemaster:analyze [aralık]` | Mühendis analizi: kırıcı değişiklik, migration, config, risk | hayır |
| `/releasemaster:notes [aralık]` | Sürüm notu (mevcut biçimini izler) | evet, onayla |
| `/releasemaster:changelog [aralık]` | `CHANGELOG.md` günceller (Keep a Changelog), eski bölümlere dokunmaz | evet, onayla |
| `/releasemaster:docs-init [compact\|basic\|full]` | Sıfırdan dokümantasyon üretir | evet, onayla |
| `/releasemaster:docs-update [aralık]` | Son değişikliklerden etkilenen dokümanları bulur, cerrahi düzenler | evet, onayla |
| `/releasemaster:release [versiyon]` | Checklist'li uçtan uca sürüm hazırlığı | evet, onayla |
| `/releasemaster:config` | Ayarları göster / değiştir | yalnızca config |

Çağırma biçimi araca göre değişir:

| Araç | Nasıl çağrılır |
|---|---|
| Claude Code | `/releasemaster:notes` (plugin komutları, otomatik tamamlanır) |
| Codex | `$releasemaster notes` |
| Cursor | `/releasemaster notes` |
| OpenCode | `/releasemaster-notes` (isteğe bağlı komutları kopyaladıktan sonra) ya da sözle iste |
| Kimi Code | `/skill:releasemaster notes` |

Her araçta isteğini düz cümleyle de anlatabilirsin; skill onu doğru komuta eşler.

Hızlı sorular için komut gerekmez: "son 1 haftada neler değişti?" kısa bir özetle sohbette cevap verir, dosya yazmaz.

Aralık örnekleri: `son sürümden beri`, `v1.4.0'dan beri`, `1 Ekim'den beri`, `a1b2c3d commit'inden beri`, ya da depo bazında `api=v1.4.0..HEAD web=9c8d7e6..develop`. Vermezsen bir aralık önerir ve sorar.

## Adım adım

<!-- ekran görüntüleri: docs/images/ -->

1. **Bir kez kur:** `/releasemaster:init`. Depolarını bulur (`*.code-workspace` içinde tanımlı klasörler dahil), dokümantasyon olup olmadığını sorar. Zaten sürüm notların varsa sonuncusunu commit'lere eşlemeyi önerir; böylece sonraki not tam o noktadan başlar. Çıktı: `.releasemaster/releasemaster.config.json`. Skill'in hafızası budur, ekiple paylaşmak için commit'le.
2. **Etrafa bak:** `/releasemaster:status` her depo için dal, son not/sürüm ve ondan sonra kaç commit geldiğini gösterir.
3. **Hızlı bir soru sor:** "bu hafta backend ve web'de neler değişti?" temalara göre 3–8 madde ve tek satırlık deploy uyarısı verir (migration, yeni config anahtarı, PR'sız commit). Dosya yok, kurulum yok.
4. **Sürüm notu yaz:** `/releasemaster:notes`. Arka planda: bir digest commit'leri PR'a göre gruplar, bir özelliğin backend ve frontend parçalarını birbirine bağlar, riskli diff parçalarını çıkarır. Taslak iskelet teknik tabloları doldurur, model düzyazıyı yazar, ardından bir denetleyici her PR numarasını, endpoint'i, config anahtarını, migration'ı ve commit hash'ini depolara karşı doğrular. Bir şey yazılmadan önce önizlemeyi görür ve onaylarsın.
5. **Changelog'u güncelle:** `/releasemaster:changelog`. Yeni bölüm `[Unreleased]` altına girer, mevcut bölümler birebir aynı kalır.
6. **Dokümantasyon:** Hiç yoksa `/releasemaster:docs-init` (compact: tek güçlü README; basic: README + `docs/`; full: ayrıca ADR'ler, API referansı, runbook'lar), yeni geliştirmelerden sonra `/releasemaster:docs-update`.

## Arka planda ne çalışıyor

| Script | Görevi |
|---|---|
| `scripts/collect_changes.py` | Bir aralığın ham commit'leri (etiket / tarih / commit / son sürüm / önceki not), merge commit'lerinden PR eşlemesi, sinyaller |
| `scripts/digest.py` | PR bazlı digest, depolar arası bağlantı adayları, riskli diff parçaları, sürüm checklist'i; taslak not için `--format skeleton` |
| `scripts/verify.py` | Notu depolara karşı doğrular: uydurma PR, endpoint, config anahtarı, migration ya da hash hatadır; atlananları işaretler |
| `scripts/detect_project.py` | Stack, mevcut doküman ve sürüm notları, etiketler, commit kuralları |
| `scripts/portable.py` | Disk erişimi olmayan sandbox'lar (claude.ai) için depoları git bundle olarak paketler |

Model onlarca `git show` çıktısı yerine kompakt bir digest okur ve kendi iddialarını modele ihtiyaç duymayan bir script ile denetler.

## claude.ai ile kullanım

claude.ai'da skill, diskini göremeyen bir sandbox'ta çalışır. Geçmişi bir kez paketle:

```
python plugins/releasemaster/skills/releasemaster/scripts/portable.py export
# config henüz yoksa: ... export --repo ../api --repo ../web
```

Oluşan `releasemaster-upload.zip` dosyasını sohbete ekle ve sözle iste ("son sürüm notundan sonrası için sürüm notu hazırla"). Zip yalnızca commit'leri taşır (tüm dallar ve etiketler), commit'lenmemiş çalışmayı değil. İş bitince yeni dosyaları ve güncellenmiş config'i geri alırsın; commit'le ve skill'in nerede kaldığını bilmesi için sonraki export'ta config'i de ekle. Slash komutları araca bağlıdır (Komutlar bölümüne bak); claude.ai'da yoktur, sözle iste.

## Çoklu depo config'i

```json
{
  "product": { "name": "Acme", "language": "tr", "versioning": { "scheme": "semver" } },
  "repos": [
    { "name": "api", "path": "../acme-api", "platform": "backend", "defaultBranch": "main" },
    { "name": "web", "path": "../acme-web", "platform": "frontend", "defaultBranch": "main" }
  ],
  "docs": { "path": "docs", "exists": true },
  "releaseNotes": { "path": "docs/releases", "fileNamePattern": "{version}.md" },
  "approval": "always"
}
```

Tüm şema: [`config-schema.md`](plugins/releasemaster/skills/releasemaster/references/config-schema.md).

## Ne kadar iyi çalışıyor?

Gerçek bir ürün (.NET backend ve React frontend, Azure DevOps tarzı "Merged PR" geçmişi) üzerinde beş senaryo, her biri 2–3 koşu, aynı modelin skill'siz haliyle karşılaştırıldı:

- Elle yazılmış mevcut bir nottan ilk kez sınır bulma: kontrollerin skill'le %91–100'ü geçti, skill'siz %64.
- Hızlı haftalık özet: %96'ya karşı %62, süre ve token yaklaşık aynı.
- Rutin işler (ikinci tur not, changelog güncelleme): skill'siz ile aynı kalite, ama yaklaşık %15–40 daha yavaş ve %7–10 daha fazla token.
- Puanlanan 30 koşuda uydurma endpoint ya da PR numarası görülmedi. `verify.py` bir sigorta olarak var ve test vakalarındaki enjekte hataları yakalıyor.

Bunlar tek projeden küçük örneklemler ve yalnızca Claude ile ölçüldü. Skill açık Agent Skills biçimini izliyor ve kurulum yolları her aracın dokümanından alındı, ama Codex, Cursor, OpenCode ve Kimi Code içinde henüz çalıştırılmadı. Bunların hepsini garanti değil, bir işaret olarak oku.

## Depo yapısı

```
.claude-plugin/marketplace.json            marketplace manifesti (Claude Code)
plugins/releasemaster/
  .claude-plugin/plugin.json               plugin manifesti
  commands/                                /releasemaster:<komut> dosyaları
  skills/releasemaster/                    skill: SKILL.md, references/, templates/, scripts/
adapters/opencode/commands/                isteğe bağlı OpenCode özel komutları
tools/install.py                           diğer araçlar için isteğe bağlı kurulum betiği
tools/build_skill_zip.py                   claude.ai yüklemesi için zip
```

## Güvenlik

Her yazma önizleme ya da diff olarak gösterilir ve onayını ister (config'teki `approval` ile gevşetilebilir). Sen istemedikçe etiket atılmaz, commit ya da push yapılmaz. Mevcut dokümanlar cerrahi olarak düzenlenir, baştan yazılmaz.
