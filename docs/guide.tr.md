# Kullanım rehberi

## Bağlantı ve başlatma

EXE dosyasını kayıt yapabildiğiniz bir klasörden açın. Python kurmanız gerekmez. Sağ üstten Türkçe veya English seçebilirsiniz.

**Bağlantı** bölümüne Binance.com HMAC API anahtarınız girilir. API anahtarı ayrı bir erişim iznidir; Binance giriş şifreniz değildir. Binance API Yönetimi üzerinden oluşturun. Okuma ve Spot işlemi açın; güvenilir IP kısıtlamasını etkinleştirin. Para çekme, transfer, marjin ve vadeli işlemleri kapalı tutun. Binance birleşik izni “Spot ve Marjin” olarak adlandırabilir; uygulama yalnızca Spot işlemlerini uygular. Binance giriş ve doğrulamasını kendiniz tamamlayın. Anahtarı ve gizli anahtarı uygulamanın gizli alanlarına girip doğrulayarak kaydedin.

**Yapay zekâ incelemesi** bölümüne OpenAI API anahtarı girilir. Varsayılan model `gpt-6-luna`dır. Paylaşım ve ücretlendirme açıklamasını okuyup izin kutusunu işaretleyin. Kontrol, anahtarın seçilen modeli görebildiğini doğrular; gerçek yanıt yalnızca uygun bir alım önerisinde istenir. OpenAI API ücretleri, 10 USDT işlem bütçesinden ayrıdır. Sağlayıcı hesabında proje için kesin harcama sınırı belirleyin.

**Genel bakış** bölümünde sınırları okuyun, gerçek emir izni kutusunu işaretleyin ve **Otomatik işlemleri başlat** düğmesine basın. Binance Spot cüzdanınızda en az 10 USDT kullanılabilir olmalıdır. Uygulama hesabınıza para taşımaz. Her açılışta gerçek işlemler kapalı başlar.

## Otomatik olarak ne olur?

Bitcoin alınan varlıktır. USDT, ayrılan bakiyeyi göstermek için kullanılan birimdir. Program herkese açık fiyatları izler; sabit eğilim kuralı yukarı döndüğünde alım önerir. Ücreti, kullanılabilir parayı, riski ve Binance alt sınırlarını kontrol eder; sonra öneriyi OpenAI’a inceletir. Ret veya erişilemeyen model, alım yapılmaması demektir. Yapay zekâ kabulü sabit sınırları aşamaz.

Uygun alım, Binance’teki satış hedefi ve stop ile birlikte gönderilir. Alımın tamamı hemen gerçekleşmeli, aksi hâlde iptal olmalıdır. Tam gerçekleşmede Binance çıkış emirlerini etkinleştirir. Uygulama başarı varsaymak yerine borsanın gerçek emir ve gerçekleşme kayıtlarını sorgular.

Yeni kararlar ve kayıt eşleştirmesi için uygulama açık, bilgisayar açık ve internete bağlı kalmalıdır. **Yeni alımları duraklat** düğmesi veya uygulamayı kapatmak yeni kararları durdurur; gönderilmiş istek tamamlanabilir. **Borsadaki mevcut çıkış emirleri uygulama duraklatılmış veya kapalıyken de gerçekleşebilir.** Doğrudan yönetmek isterseniz Binance üzerinden inceleyin.

Başlangıç bütçesi 10 USDT’dir; artık bakiyeler dâhil yatırım sınırı 7,50 USDT’dir. Her girişte planlanan kayıp payı 0,10 USDT’dir. Fiyat boşlukları, kesintiler, reddedilen koruma, ücretler ve satılamayan Bitcoin daha büyük kayıplara yol açabilir. Küçük BTC artıkları satış alt sınırının altında ve korumasız kalabilir. Günlük ve toplam kayıp kontrolleri yeni alımları durdurur; azami kaybı garanti etmez.

## Durum ve kayıtlar

Genel bakış; uygulamaya ayrılan parayı, son doğrulanan değeri, yönetilen emirleri, son güncellemeyi ve yapay zekâ durumunu gösterir. Diğer Binance varlıklarınız botun bütçesine eklenmez. İnceleme puanı kazanç olasılığı değildir. Özellikle küçük bakiyede sinyal beklenmesi veya alım atlanması normal olabilir.

Uygulama belirsiz emir bildirir veya Binance’i kontrol etmenizi isterse hesabı doğrudan inceleyin. Sıfırlamak amacıyla `live_state.json` veya `.private/` klasörünü silmeyin. Şifreli bağlantılar, bütçe kaydı ve yerel bilgiler birlikte kalmalıdır. Anahtarlar ve gerçek hesap kayıtları GitHub deposuna eklenmez.

Geçmiş kontrol yalnızca kuralları karşılaştırır. Yapay zekâyı içermez; emirlerin gerçekleştiğini varsayar ve kalan BTC’yi kayıtlı fiyatla değerler. Küçük bakiye tek başına satılamayabilir. Bu, gerçek işlem geçmişi değildir ve kazanç kanıtlamaz.

## Eski kurulumu güncelleme

Yeni alımları duraklatın ve eski sürümü kapatın. Borsadaki aktif emirleri inceleyin. Mevcut `live_state.json`, `.private/`, ayarlar ve kayıtlar yerinde kalacak şekilde yalnızca EXE dosyasını değiştirin. Aynı hesapla yeni bir 10 USDT ayırmak için ikinci temiz kurulum çalıştırmayın. Güncelleme, geçerli eski bütçe kayıtlarını doğrular ve kayıt doğrulama biçimini taşır. Yeni alımlar için OpenAI bağlantısı gerekir; mevcut Binance çıkış emirleri bağımsız kalır.

Hesap anahtarı değişimi ve eksik/bozuk gerçek kayıtların kurtarılması otomatik değildir. Kurtarma öncesi [güvenlik notlarını](../SECURITY.md) inceleyin. İmzalı emir gönderimi ve ücretli model üretimi, uygun kendi hesaplarınızla ayrıca doğrulanmalıdır. Güvenilir kazanç sağlandığı gösterilmemiştir.
