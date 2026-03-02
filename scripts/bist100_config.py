# ============================================================
# BIST100 News Sentiment Platform — Company & Keyword Config
# All 100 companies from official Borsa Istanbul BIST100 list
# Turkish name, English name, ticker, regex patterns
# Ambiguity classification + co-occurrence filtering
#
# Composition changes quarterly (Jan/Apr/Jul/Oct)
# Source: https://www.borsaistanbul.com/en/indices
# Last verified: March 2026 (Q1 2026 period)
# ============================================================

# ---------- G20 COUNTRY FILTER (6 major news producers, excl. Turkey) ----------
G20_COUNTRIES = ['US', 'GB', 'DE', 'FR', 'JP', 'CN']

SCOPE_LABELS = {
    "TR": "TÜRKİYE",
    "G20": "ULUSLARARASI",
}

# ---------- CO-OCCURRENCE CONTEXT FILTER ----------
# For ambiguous company names, the article must ALSO contain:
#   (a) a BIST/borsa reference, OR
#   (b) the company's specific ticker code
# This is much stricter than generic stock terms — greatly reduces false positives.
#
# In BigQuery, each ambiguous company's filter becomes:
#   REGEXP_CONTAINS(text_all, company_pattern)
#   AND REGEXP_CONTAINS(text_all, BIST_CONTEXT_BASE + "|" + ticker_pattern)

# Base context: BIST references (shared across all ambiguous companies)
BIST_CONTEXT_BASE = (
    r"\bbist\b|\bbist.?100\b|\bxu100\b"
    r"|\bborsa istanbul\b"
    r"|\bhisse senedi\b|\bhisse\b"
)

def get_ambiguous_context_pattern(ticker):
    """Build co-occurrence filter for a specific ambiguous company.
    Article must mention BIST/borsa OR the company's ticker code."""
    return BIST_CONTEXT_BASE + r"|\b" + ticker.lower() + r"\b"

# Example: Pegasus (PGSUS) context filter becomes:
#   \bbist\b|\bbist.?100\b|\bxu100\b|\bborsa istanbul\b|\bhisse senedi\b|\bhisse\b|\bpgsus\b

# ---------- ALL 100 BIST100 COMPANIES ----------
# needs_context: False = unique name, True = ambiguous, needs co-occurrence filter

BIST100_COMPANIES = [
    # --- 1-10 ---
    {"label": "AG Anadolu Grubu", "ticker": "AGHOL", "pattern": r"ag anadolu grubu|anadolu grubu holding|\baghol\b", "needs_context": False},
    {"label": "Akbank",           "ticker": "AKBNK", "pattern": r"\bakbank\b|\bakbnk\b", "needs_context": False},
    {"label": "Aksa Akrilik",     "ticker": "AKSA",  "pattern": r"aksa akrilik|\baksa kimya\b", "needs_context": True},
    {"label": "Aksa Enerji",      "ticker": "AKSEN", "pattern": r"aksa enerji|\baksen\b", "needs_context": False},
    {"label": "Alarko Holding",   "ticker": "ALARK", "pattern": r"alarko holding|\balark\b|\balarko\b", "needs_context": False},
    {"label": "Altınay Savunma",  "ticker": "ALTNY", "pattern": r"altınay savunma|altinay savunma|\baltny\b|\baltınay\b|\baltinay\b", "needs_context": False},
    {"label": "Anadolu Sigorta",  "ticker": "ANSGR", "pattern": r"anadolu sigorta|\bansgr\b", "needs_context": False},
    {"label": "Anadolu Efes",     "ticker": "AEFES", "pattern": r"anadolu efes|\baefes\b", "needs_context": False},
    {"label": "Arçelik",          "ticker": "ARCLK", "pattern": r"\barçelik\b|\barcelik\b|\barclk\b", "needs_context": False},
    {"label": "Aselsan",          "ticker": "ASELS", "pattern": r"\baselsan\b|\basels\b", "needs_context": False},

    # --- 11-20 ---
    {"label": "Astor Enerji",     "ticker": "ASTOR", "pattern": r"astor enerji|\bastor\b", "needs_context": True},
    {"label": "Balsu Gıda",       "ticker": "BALSU", "pattern": r"balsu gıda|balsu gida|\bbalsu\b", "needs_context": False},
    {"label": "Batıçim",          "ticker": "BTCIM", "pattern": r"\bbatıçim\b|\bbaticim\b|\bbtcim\b|batı çimento|bati cimento", "needs_context": False},
    {"label": "Batısöke",         "ticker": "BSOKE", "pattern": r"\bbatısöke\b|\bbatisoke\b|\bbsoke\b", "needs_context": False},
    {"label": "BİM",              "ticker": "BIMAS", "pattern": r"\bbim mağaza\b|\bbim magaza\b|\bbimas\b|bim birleşik|bim birlesik", "needs_context": False},
    {"label": "Borusan Birleşik", "ticker": "BRSAN", "pattern": r"borusan birleşik|borusan birlesik|\bbrsan\b|\bborusan boru\b", "needs_context": False},
    {"label": "Borusan Yatırım",  "ticker": "BRYAT", "pattern": r"borusan yatırım|borusan yatirim|\bbryat\b", "needs_context": False},
    {"label": "Coca Cola İçecek", "ticker": "CCOLA", "pattern": r"coca.?cola içecek|coca.?cola icecek|\bccola\b", "needs_context": False},
    {"label": "CW Enerji",        "ticker": "CWENE", "pattern": r"cw enerji|\bcwene\b", "needs_context": True},
    {"label": "Çan2 Termik",      "ticker": "CANTE", "pattern": r"çan2 termik|can2 termik|\bcante\b", "needs_context": False},

    # --- 21-30 ---
    {"label": "Çimsa",            "ticker": "CIMSA", "pattern": r"\bçimsa\b|\bcimsa\b", "needs_context": False},
    {"label": "DAP Gayrimenkul",  "ticker": "DAPGM", "pattern": r"dap gayrimenkul|\bdapgm\b", "needs_context": True},
    {"label": "Destek Finans",    "ticker": "DSTKF", "pattern": r"destek finans faktoring|destek faktoring|\bdstkf\b", "needs_context": False},
    {"label": "Doğan Holding",    "ticker": "DOHOL", "pattern": r"doğan holding|dogan holding|doğan şirketler|dogan sirketler|\bdohol\b", "needs_context": True},
    {"label": "Doğuş Otomotiv",   "ticker": "DOAS",  "pattern": r"doğuş otomotiv|dogus otomotiv|\bdoas\b", "needs_context": False},
    {"label": "Efor Yatırım",     "ticker": "EFOR",  "pattern": r"efor yatırım|efor yatirim|\befor\b", "needs_context": True},
    {"label": "Ege Endüstri",     "ticker": "EGEEN", "pattern": r"ege endüstri|ege endustri|\begeen\b", "needs_context": False},
    {"label": "Eczacıbaşı İlaç",  "ticker": "ECILC", "pattern": r"eczacıbaşı ilaç|eczacibasi ilac|\becilc\b|\beczacıbaşı\b|\beczacibasi\b", "needs_context": False},
    {"label": "Emlak Konut",      "ticker": "EKGYO", "pattern": r"emlak konut|\bekgyo\b", "needs_context": False},
    {"label": "Enerjisa",         "ticker": "ENJSA", "pattern": r"\benerjisa\b|\benjsa\b", "needs_context": False},

    # --- 31-40 ---
    {"label": "Enerya Enerji",    "ticker": "ENERY", "pattern": r"enerya enerji|\benerya\b|\benery\b", "needs_context": False},
    {"label": "ENKA İnşaat",      "ticker": "ENKAI", "pattern": r"enka inşaat|enka insaat|\benkai\b", "needs_context": False},
    {"label": "Ereğli Demir",     "ticker": "EREGL", "pattern": r"ereğli demir|eregli demir|\beregl\b|\berdemir\b", "needs_context": False},
    {"label": "Europower Enerji", "ticker": "EUPWR", "pattern": r"europower enerji|\beupwr\b|\beuropower\b", "needs_context": False},
    {"label": "Fenerbahçe",       "ticker": "FENER", "pattern": r"fenerbahçe futbol|fenerbahce futbol|\bfener\b", "needs_context": True},
    {"label": "Ford Otosan",      "ticker": "FROTO", "pattern": r"ford otosan|ford otomotiv|\bfroto\b", "needs_context": False},
    {"label": "Galatasaray",      "ticker": "GSRAY", "pattern": r"galatasaray sportif|\bgsray\b", "needs_context": True},
    {"label": "Gen İlaç",         "ticker": "GENIL", "pattern": r"gen ilaç|gen ilac|gen sağlık|gen saglik|\bgenil\b", "needs_context": True},
    {"label": "Girişim Elektrik", "ticker": "GESAN", "pattern": r"girişim elektrik|girisim elektrik|\bgesan\b", "needs_context": False},
    {"label": "Grainturk",        "ticker": "GRTHO", "pattern": r"\bgrainturk\b|\bgrtho\b", "needs_context": False},

    # --- 41-50 ---
    {"label": "Gübre Fabrikaları","ticker": "GUBRF", "pattern": r"gübre fabrika|gubre fabrika|\bgubrf\b|\bgübretas\b|\bgubretas\b", "needs_context": False},
    {"label": "Gülermak",         "ticker": "GLRMK", "pattern": r"\bgülermak\b|\bgulermak\b|\bglrmk\b", "needs_context": False},
    {"label": "Gür-Sel Turizm",   "ticker": "GRSEL", "pattern": r"gür.?sel turizm|gur.?sel turizm|\bgrsel\b", "needs_context": True},
    {"label": "Sabancı Holding",  "ticker": "SAHOL", "pattern": r"sabancı holding|sabanci holding|\bsahol\b", "needs_context": False},
    {"label": "Hektaş",           "ticker": "HEKTS", "pattern": r"\bhektaş\b|\bhektas\b|\bhekts\b", "needs_context": False},
    {"label": "İş Yatırım",       "ticker": "ISMEN", "pattern": r"iş yatırım menkul|is yatirim menkul|\bismen\b", "needs_context": False},
    {"label": "İzdemir Enerji",   "ticker": "IZENR", "pattern": r"izdemir enerji|\bizenr\b|\bizdemir\b", "needs_context": False},
    {"label": "Kardemir",         "ticker": "KRDMD", "pattern": r"\bkardemir\b|\bkrdmd\b", "needs_context": False},
    {"label": "Katılımevim",      "ticker": "KTLEV", "pattern": r"\bkatılımevim\b|\bkatilimevim\b|\bktlev\b", "needs_context": False},
    {"label": "Kiler Holding",    "ticker": "KLRHO", "pattern": r"kiler holding|\bklrho\b", "needs_context": True},

    # --- 51-60 ---
    {"label": "Kocaer Çelik",     "ticker": "KCAER", "pattern": r"kocaer çelik|kocaer celik|\bkcaer\b", "needs_context": False},
    {"label": "Koç Holding",      "ticker": "KCHOL", "pattern": r"koç holding|koc holding|\bkchol\b", "needs_context": False},
    {"label": "Kontrolmatik",     "ticker": "KONTR", "pattern": r"\bkontrolmatik\b|\bkontr\b", "needs_context": False},
    {"label": "Kuyaş Yatırım",    "ticker": "KUYAS", "pattern": r"kuyaş yatırım|kuyas yatirim|\bkuyas\b", "needs_context": False},
    {"label": "Margün Enerji",    "ticker": "MAGEN", "pattern": r"margün enerji|margun enerji|\bmagen\b", "needs_context": False},
    {"label": "Mavi Giyim",       "ticker": "MAVI",  "pattern": r"mavi giyim", "needs_context": True},
    {"label": "MIA Teknoloji",    "ticker": "MIATK", "pattern": r"mia teknoloji|\bmiatk\b", "needs_context": True},
    {"label": "Migros",           "ticker": "MGROS", "pattern": r"\bmigros\b|\bmgros\b", "needs_context": False},
    {"label": "MLP Sağlık",       "ticker": "MPARK", "pattern": r"mlp sağlık|mlp saglik|\bmpark\b|mlp health", "needs_context": False},
    {"label": "Oba Makarnacılık", "ticker": "OBAMS", "pattern": r"oba makarnacılık|oba makarnacilik|\bobams\b", "needs_context": True},

    # --- 61-70 ---
    {"label": "Odaş Elektrik",    "ticker": "ODAS",  "pattern": r"odaş elektrik|odas elektrik|\bodas\b", "needs_context": True},
    {"label": "Otokar",           "ticker": "OTKAR", "pattern": r"\botokar\b|\botkar\b", "needs_context": False},
    {"label": "Oyak Çimento",     "ticker": "OYAKC", "pattern": r"oyak çimento|oyak cimento|\boyakc\b", "needs_context": False},
    {"label": "Pasifik Eurasia",  "ticker": "PASEU", "pattern": r"pasifik eurasia|pasifik lojistik|\bpaseu\b", "needs_context": False},
    {"label": "Pasifik Teknoloji","ticker": "PATEK", "pattern": r"pasifik teknoloji|\bpatek\b", "needs_context": True},
    {"label": "Pegasus",          "ticker": "PGSUS", "pattern": r"pegasus hava|pegasus air|\bpgsus\b", "needs_context": True},
    {"label": "Petkim",           "ticker": "PETKM", "pattern": r"\bpetkim\b|\bpetkm\b", "needs_context": False},
    {"label": "Qua Granite",      "ticker": "QUAGR", "pattern": r"qua granite|\bquagr\b", "needs_context": False},
    {"label": "Ral Yatırım",      "ticker": "RALYH", "pattern": r"ral yatırım|ral yatirim|\bralyh\b", "needs_context": True},
    {"label": "Reeder Teknoloji", "ticker": "REEDR", "pattern": r"reeder teknoloji|\breedr\b", "needs_context": False},

    # --- 71-80 ---
    {"label": "Sasa Polyester",   "ticker": "SASA",  "pattern": r"sasa polyester|\bsasa\b", "needs_context": True},
    {"label": "Şekerbank",        "ticker": "SKBNK", "pattern": r"\bşekerbank\b|\bsekerbank\b|\bskbnk\b", "needs_context": False},
    {"label": "Şok Marketler",    "ticker": "SOKM",  "pattern": r"şok marketler|sok marketler|\bsokm\b", "needs_context": False},
    {"label": "Tab Gıda",         "ticker": "TABGD", "pattern": r"tab gıda|tab gida|\btabgd\b", "needs_context": True},
    {"label": "TAV Havalimanları", "ticker": "TAVHL", "pattern": r"tav havalimanları|tav havalimanlari|\btavhl\b|tav airports", "needs_context": False},
    {"label": "Tekfen Holding",   "ticker": "TKFEN", "pattern": r"tekfen holding|\btkfen\b|\btekfen\b", "needs_context": False},
    {"label": "Tofaş",            "ticker": "TOASO", "pattern": r"\btofaş\b|\btofas\b|\btoaso\b", "needs_context": False},
    {"label": "Trabzonspor",      "ticker": "TSPOR", "pattern": r"trabzonspor sportif|trabzonspor futbol|\btspor\b", "needs_context": True},
    {"label": "TR Anadolu Metal",  "ticker": "TRMET", "pattern": r"tr anadolu metal|\btrmet\b", "needs_context": True},
    {"label": "TR Doğal Enerji",   "ticker": "TRENJ", "pattern": r"tr doğal enerji|tr dogal enerji|\btrenj\b", "needs_context": True},

    # --- 81-90 ---
    {"label": "Tukaş Gıda",       "ticker": "TUKAS", "pattern": r"\btukaş\b|\btukas\b", "needs_context": False},
    {"label": "Tureks Turizm",    "ticker": "TUREX", "pattern": r"\btureks\b|\bturex\b", "needs_context": False},
    {"label": "Turkcell",         "ticker": "TCELL", "pattern": r"\bturkcell\b|\btcell\b", "needs_context": False},
    {"label": "Tüpraş",           "ticker": "TUPRS", "pattern": r"\btüpraş\b|\btupras\b|\btuprs\b", "needs_context": False},
    {"label": "Türk Altın",       "ticker": "TRALT", "pattern": r"türk altın işletme|turk altin isletme|\btralt\b", "needs_context": True},
    {"label": "THY",              "ticker": "THYAO", "pattern": r"türk hava yolları|turk hava yollari|turkish airlines|\bthyao\b|\bthy\b", "needs_context": False},
    {"label": "Garanti BBVA",     "ticker": "GARAN", "pattern": r"garanti bankası|garanti bankasi|garanti bbva|\bgaran\b", "needs_context": False},
    {"label": "Halkbank",         "ticker": "HALKB", "pattern": r"\bhalkbank\b|\bhalkb\b|halk bankası|halk bankasi", "needs_context": False},
    {"label": "İş Bankası",       "ticker": "ISCTR", "pattern": r"iş bankası|is bankasi|türkiye iş bank|\bisctr\b", "needs_context": False},
    {"label": "TSKB",             "ticker": "TSKB",  "pattern": r"sınai kalkınma bankası|sinai kalkinma bankasi|\btskb\b", "needs_context": False},

    # --- 91-100 ---
    {"label": "Türkiye Sigorta",  "ticker": "TURSG", "pattern": r"türkiye sigorta|turkiye sigorta|\btursg\b", "needs_context": False},
    {"label": "Şişecam",          "ticker": "SISE",  "pattern": r"\bşişecam\b|\bsisecam\b|\bsise\b", "needs_context": False},
    {"label": "Vakıfbank",        "ticker": "VAKBN", "pattern": r"\bvakıfbank\b|\bvakifbank\b|\bvakbn\b|vakıflar bankası", "needs_context": False},
    {"label": "Türk Telekom",     "ticker": "TTKOM", "pattern": r"türk telekom|turk telekom|\bttkom\b", "needs_context": False},
    {"label": "Türk Traktör",     "ticker": "TTRAK", "pattern": r"türk traktör|turk traktor|\bttrak\b", "needs_context": False},
    {"label": "Ülker",            "ticker": "ULKER", "pattern": r"\bülker\b|\bulker\b", "needs_context": False},
    {"label": "Vestel",           "ticker": "VESTL", "pattern": r"\bvestel\b|\bvestl\b", "needs_context": False},
    {"label": "Yapı Kredi",       "ticker": "YKBNK", "pattern": r"yapı kredi|yapi kredi|\bykbnk\b", "needs_context": False},
    {"label": "Yeo Teknoloji",    "ticker": "YEOTK", "pattern": r"yeo teknoloji|\byeotk\b", "needs_context": False},
    {"label": "Zorlu Enerji",     "ticker": "ZOREN", "pattern": r"zorlu enerji|\bzoren\b", "needs_context": False},
]

# ---------- VALIDATION ----------
assert len(BIST100_COMPANIES) == 100, f"Expected 100 companies, got {len(BIST100_COMPANIES)}"
_tickers = [c["ticker"] for c in BIST100_COMPANIES]
assert len(set(_tickers)) == 100, f"Duplicate tickers found: {[t for t in _tickers if _tickers.count(t) > 1]}"

_safe = [c for c in BIST100_COMPANIES if not c["needs_context"]]
_ambig = [c for c in BIST100_COMPANIES if c["needs_context"]]
print(f"BIST100 config loaded: {len(BIST100_COMPANIES)} companies "
      f"({len(_safe)} safe, {len(_ambig)} ambiguous)")

# ---------- GAUGE KEYWORDS ----------
GAUGE_GENERIC_KEYWORDS = [
    {"label": "borsa istanbul",   "pattern": r"borsa istanbul|\bbist\b"},
    {"label": "hisse senedi",     "pattern": r"hisse senedi|hisse senetleri"},
    {"label": "istanbul stock",   "pattern": r"istanbul stock exchange"},
    {"label": "türk borsası",     "pattern": r"türk borsası|turk borsasi|turkish stock"},
    {"label": "BIST100",          "pattern": r"bist.?100|xu100"},
]

# Top 15 blue-chip companies for gauge
GAUGE_BLUECHIP_TICKERS = [
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "EREGL",
    "FROTO", "GARAN", "HALKB", "ISCTR", "KCHOL",
    "SAHOL", "SISE", "THYAO", "TUPRS", "TCELL",
]

GAUGE_KEYWORDS = list(GAUGE_GENERIC_KEYWORDS)
for ticker in GAUGE_BLUECHIP_TICKERS:
    company = next((c for c in BIST100_COMPANIES if c["ticker"] == ticker), None)
    if company:
        GAUGE_KEYWORDS.append({"label": company["label"], "pattern": company["pattern"]})

assert len(GAUGE_KEYWORDS) == 20, f"Expected 20 gauge keywords, got {len(GAUGE_KEYWORDS)}"
print(f"Gauge keywords: {len(GAUGE_KEYWORDS)} ({len(GAUGE_GENERIC_KEYWORDS)} generic + {len(GAUGE_BLUECHIP_TICKERS)} blue-chip)")

# ---------- RANKING KEYWORDS ----------
RANKING_SAFE = [c for c in BIST100_COMPANIES if not c["needs_context"]]
RANKING_AMBIGUOUS = [c for c in BIST100_COMPANIES if c["needs_context"]]
print(f"Ranking keywords: {len(RANKING_SAFE)} safe + {len(RANKING_AMBIGUOUS)} ambiguous")

# ---------- FINANCIAL CONTENT FILTER (Layer 1) ----------
# Applied to ALL queries — article must have financial/economic V2Theme
# This filters out sports, politics, entertainment, etc.
FINANCIAL_THEME_FILTER = (
    r"econ_|fncact_|tax_|bus_|fin_"
    r"|bankruptcy|invest|stock|bourse|market|trade"
    r"|revenue|profit|earning|dividend|ipo|merger"
    r"|acquisition|inflation|gdp|fiscal|monetary"
)

# ---------- SETTINGS ----------
WINDOW_HOURS = 24
MIN_ARTICLES_GAUGE = 3
MIN_ARTICLES_RANKING = 3
MIN_ARTICLES_TOTAL = 30
TOP_N = 10

# No baselines — gauge shows only current 24h average

# Outlier removal (Layer 3)
TONE_WINSORIZE_LIMIT = 15       # Cap extreme tones at ±15
SINGLE_SOURCE_CAP = 0.60        # Flag if >60% articles from one domain
MIN_COMPANIES_FOR_POST = 3      # Skip G20 ranking post if fewer qualify

# ---------- CHART TEXT ----------
CHART_TITLE_GAUGE = "BIST100 Haber Duygu Göstergesi"
CHART_TITLE_RANKING_POS = "En Pozitif Haberler"
CHART_TITLE_RANKING_NEG = "En Negatif Haberler"

TWEET_HASHTAGS = "#BIST100 #BorsaIstanbul #Borsa #Hisse"
DISCLAIMER = "Yatırım tavsiyesi değildir."

# ---------- X POSTING SCHEDULE (UTC) ----------
SCHEDULE = {
    "gauge_morning":    {"hour": 7,  "type": "gauge"},
    "tr_positive":      {"hour": 10, "type": "ranking_tr_positive"},
    "tr_negative":      {"hour": 13, "type": "ranking_tr_negative"},
    "g20_positive":     {"hour": 16, "type": "ranking_g20_positive"},
    "g20_negative":     {"hour": 19, "type": "ranking_g20_negative"},
    "gauge_evening":    {"hour": 22, "type": "gauge"},
}
