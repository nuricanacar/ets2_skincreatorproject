# 🚛 ETS2 Skin Tool - V0.1 Beta

Bu proje, Euro Truck Simulator 2 için otomatikleştirilmiş, tüm tırlara uyumlu ve "beton gibi" net (solid) logolara sahip boyama paketleri üretmek amacıyla geliştirilen bir Python aracıdır. **V0.1 Beta** sürümü, "Pembe Tır" hatasının tamamen çözüldüğü ve resmi SCS DLC standartlarına geçildiği ilk kararlı sürümdür.

## 🚀 Geliştirme Süreci ve Teknik Devrimler

Proje, başlangıçta karşılaşılan teknik kısıtlamalar nedeniyle C# tabanlı yapıdan **Python** mimarisine taşınmış ve şu kritik başarılar elde edilmiştir:

### 1. Resmi DLC Mimarisi (Reverse Engineering)
Rastgele klasör yapıları yerine, resmi SCS DLC'leri (`dlc_valentine`, `dlc_raven` vb.) analiz edilerek **Universal Paintjob** sistemine geçilmiştir. 
* **Dosya Yolu:** `/vehicle/truck/upgrade/paintjob/universal/`

### 2. Dinamik TOBJ Header Çözümü (40-Byte Fix)
Eski yöntemde kullanılan 44 baytlık hatalı başlıklar yerine, kod artık bilgisayarınızdaki resmi bir DLC dosyasını tarayarak **gerçek 40-baytlık SCS başlığını** dinamik olarak kopyalar. Bu sayede "Pembe Tır" (Failed reading map name) hatası kalıcı olarak çözülmüştür.

### 3. DDS & ImageMagick (Wand) Entegrasyonu
Oyun motorunun (Prism3D) %100 uyumlu gördüğü **DXT5** sıkıştırmasını sağlamak için ImageMagick motoru sisteme dahil edilmiştir.
* **Alpha Fix:** Logoların opak durması için pikseller taranarak şeffaflık eşikleri sabitlenmiştir (`Alpha > 0 => 255`).

---

## 🛠️ Mevcut Durum ve Hata (Bug) Tablosu

Aşağıdaki tablo, 4096x4096px şeffaf tuval üzerine yerleştirilen logoların oyun içindeki güncel durumunu ve koordinat kalibrasyon ihtiyacını göstermektedir.

| Tır Modeli | Durum | Gözlemlenen Hata / Teknik Not |
| :--- | :---: | :--- |
| **Daf XD** | ✅ | Başarılı. Logo doğru yerde. |
| **Daf NGD** | ✅ | Başarılı. Logo doğru yerde. |
| **Man TGX** | ✅ | Başarılı. Logo doğru yerde. |
| **Daf XF 105** | ⚠️ | Logo yanlış koordinatta. |
| **Daf XF** | ❌ | Logo kapıda görünmüyor (Doku mor değil). |
| **Iveco Stralis / Highway** | ⚠️ | Logo yanlış koordinatta. |
| **Iveco S-Way** | 🚫 | Mod listede hiç görünmüyor (Internal name hatası). |
| **Man TGX Euro 5** | ⚠️ | Logo yanlış koordinatta. |
| **Man TGX Euro 6** | ⚠️ | Yanlış yerleşim + Çamurluklarda (yan tampon) hayalet logo. |
| **Mercedes Actros / New Actros** | ⚠️ | Logo yanlış koordinatta. |
| **Renault Magnum / Premium** | ⚠️ | Logo yanlış koordinatta. |
| **Renault T** | ⚠️ | Kapıda doğru; ancak çatıda ters, çamurluklarda hayalet logo. |
| **Scania R / S (Yeni Nesil)** | ⚠️ | Kapıda doğru; ancak yan çamurluklarda hayalet logo var. |
| **Scania R 2009 / Streamline** | ⚠️ | Logo yanlış koordinatta. |
| **Volvo FH 3** | ⚠️ | Logo yanlış koordinatta. |
| **Volvo FH 4 / 5 / 16** | ⚠️ | Kapıda görünmüyor; çamurluklarda 3 adet hayalet logo var. |

---

## 📅 V0.2 Yol Haritası (Gelecek Planları)

Bir sonraki geliştirme aşamasında aşağıdaki kronik sorunlara odaklanılacaktır:

1.  **Koordinat Kalibrasyonu:** Yanlış yerde duran logoların JSON koordinat verileri 4K şablonlara göre güncellenecektir.
2.  **Side-Skirt (Çamurluk) Çakışması:** Renault ve Volvo gibi modellerde çamurluk UV'lerinin kapı alanı ile çakışması, "Maskeleme" veya "Koordinat Kısıtlama" yöntemiyle çözülecektir.
3.  **Iveco S-Way Aktivasyonu:** Tanımlama dosyalarındaki eksiklikler giderilecektir.
4.  **Dorse Entegrasyonu:** Sistem dorseler için de aktif edilecektir.

---

## 🚀 Kullanım Talimatları

1.  **Gereksinimler:** Bilgisayarınızda [ImageMagick](https://imagemagick.org/script/download.php#windows) kurulu olmalıdır (Kurulumda "Add to PATH" ve "Install legacy utilities" kutucuklarını işaretleyin).
2.  **Kütüphane Kurulumu:** ```bash
    pip install Wand Pillow
    ```
3.  **Çalıştırma:**
    ```bash
    python main.py
    ```
4.  Uygulama üzerinden logonuzu seçin, "Generate for ALL Trucks" deyin ve `.scs` dosyanızı oluşturun.
