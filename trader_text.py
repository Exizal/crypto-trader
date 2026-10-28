"""English and Turkish interface messages."""

TEXT = {
    "en": {
        "title": "Crypto Trader",
        "subtitle": "Binance.com · Bitcoin / USDT · automatic spot trading",
        "language": "Language / Dil",
        "intro": "Automatic Bitcoin spot entries with OpenAI review, fixed spending limits and "
        "exchange-hosted exits. Connect both APIs and enable trading when you are ready.",
        "units": "USDT is the unit used to count this practice balance. BTC means Bitcoin. These "
        "are simulated holdings, separate from your real money.",
        "halted": "Practice paused because a loss limit was reached",
        "start": "Start automatic trading",
        "stop": "Pause new purchases",
        "fetch": "Get latest prices",
        "folder": "Open saved files",
        "job_busy": "A task is already running. Please wait until it finishes.",
        "fetch_busy": "Downloading recorded prices…",
        "backtest_busy": "Trying the rules on recorded prices…",
        "job_done": "Task finished. The saved results have been updated.",
        "job_failed": "The task could not finish. Check your internet connection. Details are in "
        "the saved logs.",
        "key": "HMAC API key",
        "missing": "Enter both the API key and its secret, or close this window to skip the check.",
        "error_title": "Could not complete that step",
        "error": "That step did not finish. Make sure this app is in a folder where you can save "
        "files, and check your internet connection.",
        "ai_settings": "AI review",
        "ai_intro": "OpenAI reviews each qualifying entry before it can be submitted. It can "
        "reject a proposal, but cannot increase the budget, change the order or "
        "override risk limits.",
        "ai_privacy": "The request contains public prices, indicators and the proposed trade "
        "figures. Binance keys, account identifiers and your full portfolio are "
        "never sent. The OpenAI key is stored with Windows encryption.",
        "ai_costs": "OpenAI API charges are separate from your 10 USDT trading allocation. This "
        "app permits at most 6 review attempts per UTC day and 512 output tokens per "
        "request. Set a project hard spend limit in your OpenAI account. A missing "
        "key, API failure or rejected review blocks new purchases.",
        "ai_current": "Saved model: {model}. Enter a key again to replace the AI connection.",
        "ai_key": "OpenAI API key",
        "ai_model": "Model identifier",
        "ai_consent": "I allow the market/proposal data described above to be sent to OpenAI and "
        "understand that API requests are billed separately.",
        "ai_consent_required": "Read and select the AI data-sharing and billing checkbox before "
        "saving.",
        "ai_checking": "Checking API key access to the selected model…",
        "ai_saved": "Model access verified and the key saved with Windows encryption. Responses "
        "are requested only for qualifying trade proposals.",
        "ai_setup_failed": "The AI connection could not be verified. Check the key, model access "
        "and API project permissions.",
        "ai_unconfigured": "AI connection required · new purchases are blocked",
        "ai_ready": "AI review is configured",
        "ai_reviewing": "AI is reviewing the proposed entry",
        "ai_wait": "AI declined this entry · no purchase sent",
        "ai_approved": "AI accepted the entry review",
        "ai_error": "AI unavailable or response invalid · no purchase sent",
        "ai_stale": "AI review expired · no purchase sent",
        "ai_limit": "Daily AI request limit reached · no purchase sent",
        "ai_summary": "{model} · {status}",
        "submitted_order": "Submitted",
        "protected_order": "Stop confirmed",
        "pending_order": "Pending",
        "review_order": "Check Binance",
        "closed_order": "Completed",
        "not_filled": "Not filled",
        "dashboard": "Dashboard",
        "connection": "Connection",
        "guide": "Help",
        "research": "Historical results",
        "badge_off": "REAL TRADING OFF",
        "badge_on": "REAL TRADING ENABLED",
        "budget_card": "Allocated budget",
        "cash_card": "Bot cash",
        "value_card": "Bot value, including Bitcoin",
        "connect": "Connect Binance",
        "authorize": "I authorize automatic real orders within this 10 USDT allocation. I "
        "understand I can lose this money.",
        "authority_needed": "Read and select the authorization box before starting real trading.",
        "need_connection": "Connect your Binance API key locally before starting.",
        "paused": "Paused. Existing Binance stop and target orders remain active.",
        "connecting": "Verifying Binance connection and saved trading records…",
        "pausing": "Pausing. A request already sent may still complete at Binance.",
        "waiting_signal": "Connected · waiting for the strategy’s next buying signal",
        "minimum_order": "Purchase skipped · risk-sized amount does not meet Binance’s minimum",
        "active_position": "Order list active · checking the purchase and Binance-hosted exits",
        "submitting": "Submitting a protected purchase to Binance",
        "risk_halt": "Loss limit reached · new purchases disabled; existing exits remain active",
        "uncertain_order": "Order status uncertain · no repeat purchase; check Binance",
        "check_exchange": "Action required · new purchases disabled; inspect orders in Binance",
        "order_rejected": "Binance rejected the request · trading paused",
        "stale_data": "Price information is stale · no purchase sent",
        "connection_error": "Connection problem · no new purchase; existing Binance exits remain "
        "active",
        "status_off": "Real trading is off. An existing exchange order may still execute.",
        "heartbeat_live": "Last confirmed update: {time} (Türkiye time)",
        "no_live_check": "No live account check has completed yet.",
        "position_heading": "Orders managed by this app",
        "table_time": "Created (Türkiye)",
        "table_status": "Status",
        "table_buy": "BTC buy amount",
        "table_stop": "Stop price",
        "table_target": "Target price",
        "no_orders": "No real orders have been submitted by this installation.",
        "position_note": "Only this app’s allocation is shown. Your other Binance funds are not "
        "added to its budget. Bitcoin too small to sell may remain in this "
        "allocation.",
        "limits_heading": "Trading limits",
        "limits": "Budget: 10 USDT. Maximum exposure: 7.50 USDT. Planned stop loss per new "
        "purchase: up to 0.10 USDT, before gaps and unsold remainders. At most 3 entries "
        "per UTC day. New purchases pause after a 2% daily loss or a 10% fall from the "
        "highest bot value. Limits do not guarantee a maximum loss.",
        "protection_note": "A purchase is submitted with a Binance-hosted sell target and stop. "
        "Pausing or closing this app stops new decisions; those exchange orders "
        "can still sell. Small leftover Bitcoin may be too small for an exit "
        "order.",
        "connection_intro": "An API key is a separate access pass created in Binance. Signing into "
        "the website does not connect this app. Enter the key and secret here; "
        "do not send them in chat.",
        "connection_steps": "In Binance API Management, create an HMAC key. Enable reading and "
        "Spot trading, restrict it to your trusted IP address, and keep "
        "withdrawals, transfers, margin and futures disabled. This app rejects "
        "a key with unsupported permissions. The Binance UI may name Spot "
        "trading “Spot & Margin”; the app itself has no margin endpoints.",
        "save_connection": "Verify and save connection",
        "privacy_live": "Saved using Windows sign-in encryption on this computer. Your Binance "
        "password and verification codes are never needed by this app.",
        "saved": "A connection is saved for this Windows sign-in. Click Start on the dashboard to "
        "recheck it. Changing keys requires preserving and migrating the existing trading "
        "records.",
        "connection_saved": "Connection verified and saved with Windows encryption. Real trading "
        "remains off until you enable it on the dashboard.",
        "connection_failed": "Could not connect. Check the key, Spot/read permissions, IP "
        "restriction, disabled withdrawals/transfers/leverage and available "
        "USDT. No new connection was saved.",
        "running_setup": "Verifying account permissions…",
        "live_failed": "Could not start safely. Check the connection and saved records. No new "
        "order will be sent. Inspect Binance for any existing order.",
        "history_live": "Rules-only historical check; AI reviews are excluded. {count:,} hourly "
        "prices; {trades} completed trades.\n"
        "Estimated final value: {final:.4f} USDT; cash: {cash:.4f} USDT; remaining "
        "Bitcoin: {base:.8f} BTC.\n"
        "Estimated change: {change:.2f}%. Unsold Bitcoin is valued at the last "
        "recorded price. This does not measure the live AI-assisted strategy.",
        "history_none_live": "No result for the current real-trading rules yet. Run a historical "
        "check first.",
        "help_live": "Bitcoin (BTC) is a digital asset whose price changes. USDT is the asset used "
        "here to buy and sell Bitcoin. This app uses real Binance funds after you "
        "enable it; its allocation is not practice money.\n"
        "\n"
        "Crypto Trader monitors Binance.com Bitcoin prices and places spot orders "
        "after you connect your account and enable trading. You need available USDT "
        "in your Binance Spot wallet; the app does not transfer money for you.\n"
        "\n"
        "A price-trend rule proposes an entry. OpenAI reviews the public market "
        "snapshot and proposal. It can decline the trade but cannot change the "
        "budget, size, prices or risk checks. The review score is not a probability "
        "of profit. If AI is missing, unavailable or unconvinced, no purchase is "
        "sent. Existing exchange exits keep working independently.\n"
        "\n"
        "The starting allocation is 10 USDT. Maximum total exposure is 7.50 USDT, "
        "including small Bitcoin leftovers. Planned stop loss per purchase is up to "
        "0.10 USDT with estimated charges. At most three entries are allowed per UTC "
        "day. A daily 2% loss or a 10% fall from peak bot value pauses new purchases. "
        "Gaps, fees, outages, failed protection and unsold Bitcoin can cause larger "
        "losses; these are planning limits, not guaranteed maximum losses.\n"
        "\n"
        "A qualifying order is submitted with its profit target and stop. The limit "
        "purchase must fill completely immediately or expire. Binance activates the "
        "exit pair after a full fill. The app checks their status. Pause new "
        "purchases, or close the app, to stop new decisions. Native Binance orders "
        "can remain active and sell while the app is closed. Small remainders may be "
        "too small to sell or protect.\n"
        "\n"
        "OpenAI requests are billed separately from the trading budget. Only prices, "
        "indicators and proposal figures are sent; Binance keys and account "
        "identifiers are excluded. A maximum of six AI review attempts per UTC day is "
        "enforced by this app. Set an OpenAI project hard spend limit too.\n"
        "\n"
        "Keep your entire app folder. Do not delete live_state.json or .private to "
        "restart the allocation. Keys are encrypted for your Windows sign-in. Trading "
        "records are authenticated and checked against recent Binance orders. An "
        "uncertain request is queried using its saved IDs and is not blindly "
        "repeated. Inspect Binance if the app reports a problem. Manually trading or "
        "withdrawing the same balances can disrupt reconciliation.\n"
        "\n"
        "The historical check evaluates the price rules without AI. It assumes fills "
        "and uses current order-size rules on past prices. It is not a live track "
        "record. Signed Binance execution and paid model responses have not been "
        "verified with your credentials, and profitability is unproven.",
        "credential_label": "API secret",
        "ai_navigation": "AI review",
    },
    "tr": {
        "title": "Kripto Trader",
        "subtitle": "Binance.com · Bitcoin / USDT · otomatik spot alım satım",
        "language": "Language / Dil",
        "intro": "OpenAI incelemesi, sabit harcama sınırları ve borsada tutulan çıkış emirleriyle "
        "otomatik Bitcoin spot alımı. İki API bağlantısını kurun ve hazır olduğunuzda "
        "işlemleri açın.",
        "units": "USDT, bu denemede bakiyeyi gösteren birimdir. BTC, Bitcoin’in kısaltmasıdır. "
        "Buradaki varlıklar sanaldır; gerçek paranızdan ayrıdır.",
        "halted": "Kayıp sınırına ulaşıldığı için yeni alımlar durduruldu",
        "start": "Otomatik işlemleri başlat",
        "stop": "Yeni alımları duraklat",
        "fetch": "Güncel fiyatları indir",
        "folder": "Kayıtlı dosyaları aç",
        "job_busy": "Bir işlem devam ediyor. Lütfen bitmesini bekleyin.",
        "fetch_busy": "Geçmiş fiyatlar indiriliyor…",
        "backtest_busy": "Kurallar geçmiş fiyatlar üzerinde deneniyor…",
        "job_done": "İşlem tamamlandı. Kayıtlı sonuçlar güncellendi.",
        "job_failed": "İşlem tamamlanamadı. İnternet bağlantınızı kontrol edin. Ayrıntılar kayıtlı "
        "günlük dosyalarındadır.",
        "key": "HMAC API anahtarı",
        "missing": "API anahtarını ve gizli anahtarı girin ya da bu kontrolü atlamak için "
        "pencereyi kapatın.",
        "error_title": "Bu adım tamamlanamadı",
        "error": "İşlem tamamlanamadı. Uygulamanın dosya kaydedebildiğiniz bir klasörde olduğundan "
        "emin olun ve internet bağlantınızı kontrol edin.",
        "ai_settings": "Yapay zekâ incelemesi",
        "ai_intro": "OpenAI, kurallara uyan her alımı gönderilmeden önce inceler. Öneriyi "
        "reddedebilir; bütçeyi artıramaz, emri değiştiremez veya risk sınırlarını "
        "aşamaz.",
        "ai_privacy": "İstekte herkese açık fiyatlar, göstergeler ve önerilen işlem tutarları "
        "bulunur. Binance anahtarları, hesap kimlikleri ve portföyünüzün tamamı "
        "gönderilmez. OpenAI anahtarı Windows şifrelemesiyle saklanır.",
        "ai_costs": "OpenAI API ücretleri 10 USDT işlem bütçesinden ayrıdır. Uygulama UTC gününde "
        "en fazla 6 inceleme denemesine ve istekte en fazla 512 çıktı belirtecine izin "
        "verir. OpenAI hesabınızda proje için kesin harcama sınırı belirleyin. Eksik "
        "anahtar, API hatası veya reddedilen inceleme yeni alımı engeller.",
        "ai_current": "Kayıtlı model: {model}. Yapay zekâ bağlantısını değiştirmek için anahtarı "
        "yeniden girin.",
        "ai_key": "OpenAI API anahtarı",
        "ai_model": "Model kimliği",
        "ai_consent": "Yukarıda açıklanan piyasa ve işlem önerisi verilerinin OpenAI’a "
        "gönderilmesine izin veriyorum. API isteklerinin ayrıca ücretlendirildiğini "
        "anlıyorum.",
        "ai_consent_required": "Kaydetmeden önce yapay zekâ veri paylaşımı ve ücretlendirme "
        "kutusunu okuyup işaretleyin.",
        "ai_checking": "API anahtarının seçilen modele erişimi kontrol ediliyor…",
        "ai_saved": "Model erişimi doğrulandı; anahtar Windows şifrelemesiyle saklandı. Yalnızca "
        "uygun işlem önerileri için yanıt istenir.",
        "ai_setup_failed": "Yapay zekâ bağlantısı doğrulanamadı. Anahtarı, modele erişimi ve API "
        "proje izinlerini kontrol edin.",
        "ai_unconfigured": "Yapay zekâ bağlantısı gerekli · yeni alımlar engellendi",
        "ai_ready": "Yapay zekâ incelemesi ayarlandı",
        "ai_reviewing": "Yapay zekâ alım önerisini inceliyor",
        "ai_wait": "Yapay zekâ bu alımı reddetti · emir gönderilmedi",
        "ai_approved": "Yapay zekâ alım incelemesini kabul etti",
        "ai_error": "Yapay zekâ kullanılamıyor veya yanıt geçersiz · emir gönderilmedi",
        "ai_stale": "Yapay zekâ incelemesi zaman aşımına uğradı · emir gönderilmedi",
        "ai_limit": "Günlük yapay zekâ istek sınırına ulaşıldı · emir gönderilmedi",
        "ai_summary": "{model} · {status}",
        "submitted_order": "Gönderildi",
        "protected_order": "Stop doğrulandı",
        "pending_order": "Bekliyor",
        "review_order": "Kontrol gerekli",
        "closed_order": "Tamamlandı",
        "not_filled": "Gerçekleşmedi",
        "dashboard": "Genel bakış",
        "connection": "Bağlantı",
        "guide": "Yardım",
        "research": "Geçmiş sonuçlar",
        "badge_off": "GERÇEK İŞLEMLER KAPALI",
        "badge_on": "GERÇEK İŞLEMLER AÇIK",
        "budget_card": "Ayrılan bütçe",
        "cash_card": "Botun nakit bakiyesi",
        "value_card": "Bitcoin dâhil bot değeri",
        "connect": "Binance’i bağla",
        "authorize": "Bu 10 USDT bütçeyle otomatik gerçek emir gönderilmesine izin veriyorum. Bu "
        "parayı kaybedebileceğimi anlıyorum.",
        "authority_needed": "Gerçek işlemleri başlatmadan önce izin kutusunu okuyup işaretleyin.",
        "need_connection": "Başlamadan önce Binance API anahtarınızı uygulamada bağlayın.",
        "paused": "Duraklatıldı. Binance’teki mevcut stop ve hedef emirleri aktif kalır.",
        "connecting": "Binance bağlantısı ve kayıtlı işlem bilgileri doğrulanıyor…",
        "pausing": "Duraklatılıyor. Binance’e gönderilmiş bir istek yine de tamamlanabilir.",
        "waiting_signal": "Bağlı · stratejinin yeni alım sinyali bekleniyor",
        "minimum_order": "Alım atlandı · risk sınırına uygun tutar Binance’in alt sınırını "
        "karşılamıyor",
        "active_position": "Emir listesi aktif · alım ve Binance’teki çıkış emirleri kontrol "
        "ediliyor",
        "submitting": "Korumalı alım emri Binance’e gönderiliyor",
        "risk_halt": "Kayıp sınırına ulaşıldı · yeni alımlar kapalı; mevcut çıkış emirleri aktif",
        "uncertain_order": "Emir durumu belirsiz · alım tekrarlanmaz; Binance’i kontrol edin",
        "check_exchange": "Kontrol gerekiyor · yeni alımlar kapalı; Binance’teki emirleri "
        "inceleyin",
        "order_rejected": "Binance isteği reddetti · işlemler duraklatıldı",
        "stale_data": "Fiyat bilgisi güncel değil · alım emri gönderilmedi",
        "connection_error": "Bağlantı sorunu · yeni alım yok; Binance’teki mevcut çıkış emirleri "
        "aktif",
        "status_off": "Gerçek işlemler kapalı. Borsadaki mevcut bir emir yine de gerçekleşebilir.",
        "heartbeat_live": "Son doğrulanan güncelleme: {time} (Türkiye saati)",
        "no_live_check": "Henüz gerçek hesap kontrolü tamamlanmadı.",
        "position_heading": "Bu uygulamanın yönettiği emirler",
        "table_time": "Oluşturma (Türkiye)",
        "table_status": "Durum",
        "table_buy": "BTC alım miktarı",
        "table_stop": "Stop fiyatı",
        "table_target": "Hedef fiyatı",
        "no_orders": "Bu kurulumdan henüz gerçek emir gönderilmedi.",
        "position_note": "Yalnızca bu uygulamaya ayrılan tutar gösterilir. Diğer Binance "
        "varlıklarınız bütçeye eklenmez. Satış için çok küçük kalan Bitcoin bu "
        "bütçede kalabilir.",
        "limits_heading": "İşlem sınırları",
        "limits": "Bütçe: 10 USDT. Yatırımdaki en yüksek tutar: 7,50 USDT. Fiyat boşlukları ve "
        "satılamayan küçük bakiyeler hariç, her yeni alımda planlanan stop kaybı en "
        "fazla 0,10 USDT. UTC gününde en fazla 3 giriş. Günlük %2 kayıp veya botun "
        "gördüğü en yüksek değerden %10 düşüş yeni alımları durdurur. Bu sınırlar azami "
        "kaybı garanti etmez.",
        "protection_note": "Alım, Binance’te tutulacak satış hedefi ve stop ile birlikte "
        "gönderilir. Duraklatmak veya uygulamayı kapatmak yeni kararları "
        "durdurur; borsadaki bu emirler yine de satış yapabilir. Küçük Bitcoin "
        "artıkları çıkış emri için yetersiz kalabilir.",
        "connection_intro": "API anahtarı Binance’te ayrıca oluşturulan bir erişim iznidir. Siteye "
        "giriş yapmak uygulamayı bağlamaz. Anahtarı ve gizli anahtarı buraya "
        "girin; sohbete göndermeyin.",
        "connection_steps": "Binance API Yönetimi üzerinden HMAC anahtarı oluşturun. Okuma ve Spot "
        "işlem iznini açın, güvenilir IP adresinizle sınırlandırın; para "
        "çekme, transfer, marjin ve vadeli işlem izinlerini kapalı tutun. "
        "Uygulama uygun olmayan izinleri reddeder. Binance arayüzünde Spot "
        "izni “Spot ve Marjin” olarak geçebilir; uygulama marjin işlemi "
        "yapmaz.",
        "save_connection": "Bağlantıyı doğrula ve kaydet",
        "privacy_live": "Bu bilgisayarda Windows oturumunuza bağlı şifrelemeyle kaydedilir. "
        "Binance giriş şifreniz ve doğrulama kodunuz gerekmez.",
        "saved": "Bu Windows oturumu için bağlantı kayıtlı. Yeniden kontrol için genel bakıştan "
        "Başlat’a basın. Anahtar değiştirmek, mevcut işlem kayıtlarının korunmasını ve "
        "taşınmasını gerektirir.",
        "connection_saved": "Bağlantı doğrulandı ve Windows şifrelemesiyle kaydedildi. Genel "
        "bakıştan açana kadar gerçek işlemler kapalı kalır.",
        "connection_failed": "Bağlantı kurulamadı. Anahtarı, Spot/okuma izinlerini, IP "
        "kısıtlamasını, kapalı para çekme/transfer/kaldıraç izinlerini ve "
        "USDT bakiyesini kontrol edin. Yeni bağlantı kaydedilmedi.",
        "running_setup": "Hesap izinleri doğrulanıyor…",
        "live_failed": "Güvenli biçimde başlatılamadı. Bağlantıyı ve kayıtlı bilgileri kontrol "
        "edin. Yeni emir gönderilmez. Binance’te mevcut emir olup olmadığını "
        "inceleyin.",
        "history_live": "Yalnızca kuralların geçmiş hesabı; yapay zekâ incelemesi hariçtir. "
        "{count:,} saatlik fiyat; {trades} tamamlanan işlem.\n"
        "Tahmini son değer: {final:.4f} USDT; nakit: {cash:.4f} USDT; kalan "
        "Bitcoin: {base:.8f} BTC.\n"
        "Tahmini değişim: %{change:.2f}. Satılmamış Bitcoin son kayıtlı fiyatla "
        "değerlenir. Bu hesap, gerçek yapay zekâ destekli stratejinin "
        "performansını ölçmez.",
        "history_none_live": "Güncel gerçek işlem kuralları için henüz geçmiş sonuç yok. Önce "
        "geçmiş incelemesini çalıştırın.",
        "help_live": "Bitcoin (BTC), fiyatı değişen dijital bir varlıktır. USDT, burada Bitcoin "
        "alıp satmak için kullanılan varlıktır. Uygulamayı açtığınızda gerçek Binance "
        "bakiyenizle işlem yapılır; ayrılan tutar sanal para değildir.\n"
        "\n"
        "Crypto Trader, Binance.com Bitcoin fiyatlarını izler; hesabınızı bağlayıp "
        "işlemleri açtıktan sonra spot emir gönderebilir. Binance Spot cüzdanınızda "
        "kullanılabilir USDT bulunmalıdır; uygulama sizin için para transfer etmez.\n"
        "\n"
        "Fiyat eğilimine dayalı kural bir alım önerir. OpenAI, herkese açık piyasa "
        "verilerini ve öneriyi inceler. İşlemi reddedebilir; bütçeyi, miktarı, "
        "fiyatları veya risk kontrollerini değiştiremez. İnceleme puanı, kazanç "
        "olasılığı değildir. Yapay zekâ bağlı değilse, erişilemiyorsa veya öneriyi "
        "yeterli bulmazsa alım gönderilmez. Borsadaki mevcut çıkış emirleri bağımsız "
        "çalışır.\n"
        "\n"
        "Başlangıç bütçesi 10 USDT’dir. Küçük Bitcoin artıkları dâhil en yüksek "
        "toplam yatırım 7,50 USDT’dir. Her alımda tahmini ücretlerle planlanan stop "
        "kaybı en fazla 0,10 USDT’dir. UTC gününde en fazla üç giriş yapılır. Günlük "
        "%2 kayıp veya botun en yüksek değerinden %10 düşüş yeni alımları durdurur. "
        "Fiyat boşlukları, ücretler, kesintiler, başarısız koruma ve satılamayan "
        "Bitcoin daha büyük kayıplara yol açabilir; bu sınırlar azami kayıp garantisi "
        "değildir.\n"
        "\n"
        "Uygun emir, satış hedefi ve stop ile birlikte gönderilir. Limit alımın "
        "tamamı hemen gerçekleşmeli, aksi hâlde iptal olmalıdır. Binance, alım "
        "tamamen gerçekleşince çıkış çiftini etkinleştirir. Uygulama durumlarını "
        "kontrol eder. Yeni kararları durdurmak için Yeni alımları duraklat’a basın "
        "veya uygulamayı kapatın. Binance’teki emirler uygulama kapalıyken aktif "
        "kalıp satış yapabilir. Küçük artıklar satış veya koruma için yetersiz "
        "kalabilir.\n"
        "\n"
        "OpenAI istekleri işlem bütçesinden ayrı ücretlendirilir. Yalnızca fiyatlar, "
        "göstergeler ve önerilen işlem tutarları gönderilir; Binance anahtarları ve "
        "hesap kimlikleri gönderilmez. Uygulama, UTC gününde en fazla altı yapay zekâ "
        "inceleme denemesine izin verir. OpenAI projesinde ayrıca kesin harcama "
        "sınırı belirleyin.\n"
        "\n"
        "Uygulama klasörünü birlikte saklayın. Bütçeyi yeniden başlatmak için "
        "live_state.json veya .private klasörünü silmeyin. Anahtarlar Windows "
        "oturumunuza bağlı şifrelenir. İşlem kayıtlarının bütünlüğü ve son Binance "
        "emirleri kontrol edilir. Belirsiz istek kayıtlı kimliklerle sorgulanır, "
        "körlemesine tekrarlanmaz. Uygulama sorun bildirirse Binance’i inceleyin. "
        "Aynı bakiyelerde elle işlem veya çekim yapmak eşleştirmeyi bozabilir.\n"
        "\n"
        "Geçmiş inceleme, fiyat kurallarını yapay zekâ olmadan değerlendirir. "
        "Emirlerin gerçekleştiğini varsayar ve güncel miktar kurallarını eski "
        "fiyatlarda kullanır. Gerçek işlem geçmişi değildir. İmzalı Binance işlemleri "
        "ve ücretli model yanıtları sizin anahtarlarınızla doğrulanmamıştır; kazanç "
        "sağlandığı kanıtlanmamıştır.",
        "credential_label": "API gizli anahtarı",
        "ai_navigation": "Yapay zekâ",
    },
}
