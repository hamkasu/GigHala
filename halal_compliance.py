"""
Halal Compliance System for GigHala
====================================

This module enforces strict Halal compliance for all gigs posted on the platform.
It ensures that only Shariah-compliant work is allowed, protecting the integrity
of the platform and serving the Muslim community in Malaysia.

Purpose:
- Define halal-approved gig categories
- Identify prohibited keywords and content
- Provide validation functions for gig submissions
- Support both Malay and English languages

Islamic Principles:
- Better to reject borderline cases than allow potentially haram content
- Protect users from inadvertently participating in haram activities
- Maintain platform integrity as a trusted halal marketplace
"""

import re
from typing import Dict, List, Tuple

# =============================================================================
# HALAL-APPROVED CATEGORIES (Bilingual: Malay / English)
# =============================================================================

HALAL_APPROVED_CATEGORIES = [
    {
        'slug': 'design',
        'name_en': 'Graphic Design',
        'name_ms': 'Reka Bentuk Grafik',
        'description_en': 'Logo design, branding, flyers, posters (halal content only)',
        'description_ms': 'Reka bentuk logo, jenama, risalah, poster (kandungan halal sahaja)',
        'icon': '🎨'
    },
    {
        'slug': 'writing',
        'name_en': 'Writing & Translation',
        'name_ms': 'Penulisan & Terjemahan',
        'description_en': 'Content writing, copywriting, translation (halal topics only)',
        'description_ms': 'Penulisan kandungan, penulisan iklan, terjemahan (topik halal sahaja)',
        'icon': '✍️'
    },
    {
        'slug': 'video',
        'name_en': 'Video & Animation',
        'name_ms': 'Video & Animasi',
        'description_en': 'Video editing, animation, motion graphics (halal content only)',
        'description_ms': 'Penyuntingan video, animasi, grafik bergerak (kandungan halal sahaja)',
        'icon': '🎬'
    },
    {
        'slug': 'tutoring',
        'name_en': 'Tutoring & Education',
        'name_ms': 'Pengajaran & Pendidikan',
        'description_en': 'Academic tutoring, skills training, Islamic studies',
        'description_ms': 'Bimbingan akademik, latihan kemahiran, pengajian Islam',
        'icon': '📚'
    },
    {
        'slug': 'content',
        'name_en': 'Content Creation',
        'name_ms': 'Penciptaan Kandungan',
        'description_en': 'Social media content, blog posts, newsletters (halal topics only)',
        'description_ms': 'Kandungan media sosial, catatan blog, surat berita (topik halal sahaja)',
        'icon': '📱'
    },
    {
        'slug': 'web',
        'name_en': 'Web Development',
        'name_ms': 'Pembangunan Web',
        'description_en': 'Website development, web apps (halal businesses only)',
        'description_ms': 'Pembangunan laman web, aplikasi web (perniagaan halal sahaja)',
        'icon': '💻'
    },
    {
        'slug': 'programming',
        'name_en': 'Programming & Tech',
        'name_ms': 'Pengaturcaraan & Teknologi',
        'description_en': 'Software development, mobile apps, automation (halal purposes only)',
        'description_ms': 'Pembangunan perisian, aplikasi mudah alih, automasi (tujuan halal sahaja)',
        'icon': '⚙️'
    },
    {
        'slug': 'marketing',
        'name_en': 'Digital Marketing',
        'name_ms': 'Pemasaran Digital',
        'description_en': 'SEO, social media marketing, ads (halal products/services only)',
        'description_ms': 'SEO, pemasaran media sosial, iklan (produk/perkhidmatan halal sahaja)',
        'icon': '📈'
    },
    {
        'slug': 'admin',
        'name_en': 'Admin & Customer Support',
        'name_ms': 'Admin & Sokongan Pelanggan',
        'description_en': 'Virtual assistance, data entry, customer service',
        'description_ms': 'Bantuan maya, kemasukan data, perkhidmatan pelanggan',
        'icon': '📋'
    },
    {
        'slug': 'delivery',
        'name_en': 'Delivery Services',
        'name_ms': 'Perkhidmatan Penghantaran',
        'description_en': 'Food delivery (halal only), parcel delivery, courier',
        'description_ms': 'Penghantaran makanan (halal sahaja), penghantaran bungkusan, kurier',
        'icon': '🚗'
    },
    {
        'slug': 'general',
        'name_en': 'Cleaning Services',
        'name_ms': 'Khidmat Pembersihan',
        'description_en': 'House cleaning, office cleaning, deep cleaning',
        'description_ms': 'Pembersihan rumah, pembersihan pejabat, pembersihan mendalam',
        'icon': '🧹'
    },
    {
        'slug': 'handyman',
        'name_en': 'Handyman & Repairs',
        'name_ms': 'Tukang & Pembaikan',
        'description_en': 'Home repairs, furniture assembly, maintenance',
        'description_ms': 'Pembaikan rumah, pemasangan perabot, penyelenggaraan',
        'icon': '🔧'
    },
    {
        'slug': 'photography',
        'name_en': 'Photography & Videography',
        'name_ms': 'Fotografi & Videografi',
        'description_en': 'Event photography, product photography (halal events/products only)',
        'description_ms': 'Fotografi acara, fotografi produk (acara/produk halal sahaja)',
        'icon': '📷'
    },
    {
        'slug': 'consulting',
        'name_en': 'Business Consulting',
        'name_ms': 'Perundingan Perniagaan',
        'description_en': 'Business strategy, Islamic finance consulting, halal certification',
        'description_ms': 'Strategi perniagaan, perundingan kewangan Islam, pensijilan halal',
        'icon': '💼'
    },
    {
        'slug': 'coaching',
        'name_en': 'Coaching & Mentoring',
        'name_ms': 'Bimbingan & Mentoring',
        'description_en': 'Life coaching, career guidance, Islamic coaching',
        'description_ms': 'Bimbingan hidup, panduan kerjaya, bimbingan Islam',
        'icon': '🎯'
    },
    {
        'slug': 'events',
        'name_en': 'Event Planning',
        'name_ms': 'Perancangan Acara',
        'description_en': 'Wedding planning (Islamic), corporate events, halal catering',
        'description_ms': 'Perancangan perkahwinan (Islam), acara korporat, katering halal',
        'icon': '🎉'
    },
    {
        'slug': 'data',
        'name_en': 'Data Entry & Research',
        'name_ms': 'Kemasukan Data & Penyelidikan',
        'description_en': 'Data collection, research, data analysis',
        'description_ms': 'Pengumpulan data, penyelidikan, analisis data',
        'icon': '📊'
    },
    {
        'slug': 'crafts',
        'name_en': 'Arts & Crafts',
        'name_ms': 'Seni & Kraf',
        'description_en': 'Handicrafts, Islamic calligraphy, custom gifts',
        'description_ms': 'Kraftangan, kaligrafi Islam, hadiah tersuai',
        'icon': '🎨'
    },
    {
        'slug': 'music',
        'name_en': 'Music & Audio',
        'name_ms': 'Muzik & Audio',
        'description_en': 'Nasheed, voice-over, audio editing (Islamic content only)',
        'description_ms': 'Nasyid, suara latar, penyuntingan audio (kandungan Islam sahaja)',
        'icon': '🎵'
    },
    {
        'slug': 'caregiving',
        'name_en': 'Caregiving & Nursing',
        'name_ms': 'Penjagaan & Kejururawatan',
        'description_en': 'Elderly care, child care, nursing services',
        'description_ms': 'Penjagaan warga tua, penjagaan kanak-kanak, perkhidmatan kejururawatan',
        'icon': '👨‍⚕️'
    },
    {
        'slug': 'pets',
        'name_en': 'Pet Care',
        'name_ms': 'Penjagaan Haiwan',
        'description_en': 'Pet sitting, grooming (halal pets: cats, birds, fish only)',
        'description_ms': 'Penjagaan haiwan, dandanan (haiwan halal: kucing, burung, ikan sahaja)',
        'icon': '🐱'
    },
    {
        'slug': 'garden',
        'name_en': 'Gardening & Landscaping',
        'name_ms': 'Berkebun & Landskap',
        'description_en': 'Garden maintenance, landscaping, plant care',
        'description_ms': 'Penyelenggaraan taman, landskap, penjagaan tanaman',
        'icon': '🌱'
    },
    {
        'slug': 'finance',
        'name_en': 'Accounting & Bookkeeping',
        'name_ms': 'Perakaunan & Simpan Kira',
        'description_en': 'Bookkeeping, tax filing, Islamic finance (NO riba/interest)',
        'description_ms': 'Simpan kira, pemfailan cukai, kewangan Islam (TIADA riba/faedah)',
        'icon': '💰'
    },
    {
        'slug': 'tours',
        'name_en': 'Tour Guide & Travel',
        'name_ms': 'Pemandu Pelancong & Pelancongan',
        'description_en': 'Halal tourism, umrah guidance, local tours',
        'description_ms': 'Pelancongan halal, panduan umrah, lawatan tempatan',
        'icon': '🧳'
    },
    {
        'slug': 'online-selling',
        'name_en': 'Online Selling & E-commerce',
        'name_ms': 'Jualan Online & E-dagang',
        'description_en': 'Product listing, marketplace management (halal products only)',
        'description_ms': 'Penyenaraian produk, pengurusan pasaran (produk halal sahaja)',
        'icon': '🛒'
    },
    {
        'slug': 'virtual-assistant',
        'name_en': 'Virtual Assistant',
        'name_ms': 'Pembantu Maya',
        'description_en': 'Email management, scheduling, admin tasks',
        'description_ms': 'Pengurusan emel, penjadualan, tugas pentadbiran',
        'icon': '💼'
    },
    {
        'slug': 'micro-tasks',
        'name_en': 'Micro-Tasks',
        'name_ms': 'Tugas Mikro',
        'description_en': 'Simple online tasks, surveys, app testing (halal only)',
        'description_ms': 'Tugas dalam talian ringkas, tinjauan, ujian aplikasi (halal sahaja)',
        'icon': '✅'
    },
    {
        'slug': 'engineering',
        'name_en': 'Engineering & CAD',
        'name_ms': 'Kejuruteraan & CAD',
        'description_en': 'CAD design, technical drawings, engineering consulting',
        'description_ms': 'Reka bentuk CAD, lukisan teknikal, perundingan kejuruteraan',
        'icon': '📐'
    },
    {
        'slug': 'creative-other',
        'name_en': 'Other Creative Services',
        'name_ms': 'Perkhidmatan Kreatif Lain',
        'description_en': 'Other halal creative work not listed above',
        'description_ms': 'Kerja kreatif halal lain yang tidak disenaraikan di atas',
        'icon': '🎭'
    },
]

# Category slugs for quick validation
HALAL_APPROVED_CATEGORY_SLUGS = [cat['slug'] for cat in HALAL_APPROVED_CATEGORIES]

# =============================================================================
# PROHIBITED KEYWORDS (Bilingual: Malay & English)
# =============================================================================

PROHIBITED_KEYWORDS = {
    # Alcohol & Intoxicants (الخمر)
    'alcohol': [
        'alcohol', 'alkohol', 'beer', 'bir', 'wine', 'wain', 'whiskey', 'wiski',
        'vodka', 'rum', 'gin', 'champagne', 'liquor', 'arak', 'tuak', 'toddy',
        'sake', 'soju', 'cognac', 'brandy', 'tequila', 'cocktail', 'koktail',
        'bar', 'pub', 'nightclub', 'kelab malam', 'brewery', 'kilang bir',
        'liquor store', 'kedai arak', 'wine tasting', 'minuman keras',
        'alcoholic', 'beralkohol', 'intoxicating', 'memabukkan',
        # Beer brands
        'heineken', 'tiger beer', 'carlsberg', 'guinness', 'corona', 'budweiser',
        'stella artois', 'heinken', 'tigers beer', 'tiger lager', 'anchor beer',
        'asahi', 'kirin', 'sapporo', 'hoegaarden', 'erdinger', 'paulaner',
        'chang beer', 'singha', 'leo beer', 'skol', 'miller', 'coors',
        'peroni', 'kronenbourg', 'desperados', 'foster', 'becks',
        # Whiskey/Whisky brands
        'jack daniels', 'johnnie walker', 'chivas regal', 'jameson', 'glenfiddich',
        'glenlivet', 'macallan', 'jd whiskey', 'jd whisky', 'black label',
        'red label', 'blue label', 'gold label', 'green label', 'ballantines',
        'dewar', 'famous grouse', 'crown royal', 'jim beam', 'makers mark',
        'wild turkey', 'four roses', 'bulleit', 'lagavulin', 'talisker',
        # Cognac/Brandy brands
        'hennessy', 'remy martin', 'martell', 'courvoisier', 'vsop', 'xo cognac',
        'henny', 'remy', 'napoleon brandy', 'louis xiii', 'camus',
        # Vodka brands
        'absolut', 'smirnoff', 'grey goose', 'belvedere', 'ciroc', 'ketel one',
        'skyy', 'finlandia', 'stolichnaya', 'stoli', 'titos', 'russian standard',
        # Rum brands
        'bacardi', 'captain morgan', 'havana club', 'malibu', 'kraken', 'sailor jerry',
        'mount gay', 'appleton', 'goslings', 'diplomatico', 'ron zacapa',
        # Tequila brands
        'jose cuervo', 'patron', 'don julio', 'casamigos', '1800 tequila',
        'sauza', 'espolon', 'herradura', 'clase azul', 'olmeca',
        # Gin brands
        'bombay sapphire', 'tanqueray', 'gordon', 'hendricks', 'beefeater',
        'plymouth', 'aviation', 'monkey 47', 'sipsmith', 'botanist',
        # Wine brands
        'yellowtail', 'barefoot wine', 'gallo', 'beringer', 'jacob creek',
        'penfolds', 'chateau', 'bordeaux', 'chianti', 'chardonnay', 'cabernet',
        'sauvignon', 'merlot', 'pinot noir', 'riesling', 'moscato', 'prosecco',
        # Liqueur brands
        'baileys', 'kahlua', 'amaretto', 'jagermeister', 'campari', 'aperol',
        'cointreau', 'grand marnier', 'sambuca', 'frangelico', 'benedictine',
        'drambuie', 'southern comfort', 'fireball', 'pimms',
        # Local/Regional brands
        'montoku', 'lihing', 'langkau', 'brem', 'tuak manis',
        # General alcohol terms
        'spirits', 'hard liquor', 'booze', 'alcoholic beverage', 'minuman beralkohol',
        'wine bar', 'cocktail bar', 'whisky bar', 'liquor license', 'lesen arak'
    ],

    # Gambling & Betting (القمار)
    'gambling': [
        'gambling', 'judi', 'casino', 'kasino', 'betting', 'pertaruhan',
        'lottery', 'loteri', 'jackpot', 'slot machine', 'mesin slot',
        'poker', 'roulette', 'blackjack', '4d', 'toto', 'magnum',
        'sports betting', 'pertaruhan sukan', 'online casino', 'kasino dalam talian',
        'bet', 'taruhan', 'wager', 'game of chance', 'permainan nasib'
    ],

    # Pork & Pig-Related (الخنزير)
    'pork': [
        'pork', 'babi', 'pig', 'ham', 'bacon', 'bekon', 'sausage babi',
        'pork chop', 'char siew', 'char siu', 'bak kut teh', 'non-halal meat',
        'daging tidak halal', 'lard', 'lemak babi', 'gelatin babi'
    ],

    # Adult & Sexual Content (الفاحشة)
    'adult': [
        'adult', 'dewasa', 'porn', 'porno', 'pornography', 'pornografi',
        'sex', 'seks', 'xxx', 'escort', 'prostitution', 'pelacuran',
        'massage parlor', 'urut plus', 'sensual', 'sensual massage',
        'erotic', 'erotik', 'nude', 'bogel', 'nudity', 'strip', 'stripper',
        'brothel', 'rumah pelacuran', 'call girl', 'gigolo', 'webcam model',
        'onlyfans', 'sexual content', 'kandungan seksual'
    ],

    # Interest & Usury (الربا)
    'riba': [
        'interest', 'faedah', 'usury', 'riba', 'interest rate', 'kadar faedah',
        'interest-based', 'berasaskan faedah', 'conventional loan', 'pinjaman konvensional',
        'conventional bank', 'bank konvensional', 'interest income', 'pendapatan faedah',
        'loan shark', 'along', 'ah long', 'illegal moneylending', 'pinjaman haram',
        'payday loan', 'pinjaman gaji', 'high interest', 'faedah tinggi'
    ],

    # Fraud & Scams (الغش)
    'fraud': [
        'scam', 'penipuan', 'fraud', 'fraudulent', 'ponzi', 'pyramid scheme',
        'skim piramid', 'get rich quick', 'cepat kaya', 'money game',
        'permainan wang', 'fake', 'palsu', 'counterfeit', 'tiruan',
        'identity theft', 'kecurian identiti', 'phishing', 'money laundering',
        'pengubahan wang haram', 'mlm scam', 'penipuan mlm'
    ],

    # Drugs & Narcotics (المخدرات)
    'drugs': [
        'drugs', 'dadah', 'marijuana', 'ganja', 'cocaine', 'kokain',
        'heroin', 'heroin', 'methamphetamine', 'syabu', 'ice', 'ais',
        'ecstasy', 'ekstasi', 'lsd', 'cannabis', 'kanabis', 'narcotics',
        'narkotik', 'drug dealer', 'pengedar dadah', 'drug trafficking',
        'pengedaran dadah', 'vape', 'vaping', 'e-cigarette', 'rokok elektronik'
    ],

    # Tobacco (التبغ)
    'tobacco': [
        'cigarette', 'rokok', 'tobacco', 'tembakau', 'cigar', 'cerut',
        'smoking', 'merokok', 'vape', 'vaping', 'shisha', 'hookah',
        'e-cigarette', 'rokok elektronik', 'nicotine', 'nikotin'
    ],

    # Religious Defamation & Blasphemy
    'blasphemy': [
        'blasphemy', 'penghujatan', 'anti-islam', 'anti islam',
        'islamophobia', 'islamofobia', 'insult islam', 'hina islam',
        'mock religion', 'mengejek agama', 'apostasy promotion', 'galakan murtad'
    ],

    # Black Magic & Occult (السحر)
    'occult': [
        'black magic', 'sihir', 'bomoh', 'dukun', 'witchcraft', 'santau',
        'voodoo', 'spell', 'jampi', 'curse', 'sumpahan', 'fortune telling',
        'ramalan nasib', 'palmistry', 'tarot', 'astrology', 'astrologi',
        'horoscope', 'horoskop', 'numerology', 'numerologi'
    ],

    # MLM & Get-Rich-Quick Schemes (Exploitative)
    'mlm_exploitative': [
        'guaranteed income', 'pendapatan terjamin', 'no work required',
        'tanpa perlu kerja', 'passive income guaranteed', 'income dijamin',
        'earn money while sleeping', 'dapat duit masa tidur',
        'become millionaire', 'jadi jutawan', 'unlimited earnings', 'pendapatan tanpa had'
    ],

    # Other Haram Activities
    'other_haram': [
        'dating service', 'perkhidmatan temu janji', 'matchmaking non-halal',
        'valentine', 'clubbing', 'entertainment haram', 'hiburan haram',
        'tattoo', 'tatu', 'body piercing', 'tindikan badan'
    ]
}

# Flatten all prohibited keywords for easy searching
ALL_PROHIBITED_KEYWORDS = []
for category, keywords in PROHIBITED_KEYWORDS.items():
    ALL_PROHIBITED_KEYWORDS.extend(keywords)

# =============================================================================
# HALAL COMPLIANCE VALIDATION FUNCTIONS
# =============================================================================

def check_prohibited_keywords(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains any prohibited keywords.

    Args:
        text: The text to check (title, description, etc.)

    Returns:
        Tuple of (is_compliant, list_of_violations)
        - is_compliant: True if no violations found, False otherwise
        - list_of_violations: List of detected prohibited keywords
    """
    if not text:
        return True, []

    # Normalize text: lowercase and remove extra spaces
    text_normalized = text.lower().strip()

    # DO NOT fast-track "test" content as it can be used to bypass haram detection
    # test_keywords = ["test", "testing", "percubaan", "ujian", "try", "cuba"]
    
    # Check for direct inclusion or normalized content
    normalized_content = "".join([c if c.isalnum() else " " for c in text_normalized])
    
    # if any(keyword in text_normalized or keyword in normalized_content for keyword in test_keywords):
    #     return True, []

    violations = []

    for keyword in ALL_PROHIBITED_KEYWORDS:
        # Use word boundary matching to avoid false positives
        # e.g., "bacon" should match but not "bacons" in "fibonacci cons"
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'

        if re.search(pattern, text_normalized):
            violations.append(keyword)

    is_compliant = len(violations) == 0
    return is_compliant, violations


def validate_category(category: str) -> Tuple[bool, str]:
    """
    Validate if category is in the halal-approved list.

    Args:
        category: Category slug to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not category:
        return False, "Category is required / Kategori diperlukan"

    if category not in HALAL_APPROVED_CATEGORY_SLUGS:
        return False, (
            f"Category '{category}' is not in the approved halal category list. "
            f"Please select from the approved categories. / "
            f"Kategori '{category}' tidak dalam senarai kategori halal yang diluluskan. "
            f"Sila pilih daripada kategori yang diluluskan."
        )

    return True, ""


def validate_gig_halal_compliance(
    title: str,
    description: str,
    category: str,
    skills: str = None
) -> Tuple[bool, Dict[str, any]]:
    """
    Complete halal compliance validation for a gig.

    This is the main validation function that should be called when creating
    or editing a gig. It performs comprehensive checks:
    1. Category must be in approved list
    2. Title must not contain prohibited keywords
    3. Description must not contain prohibited keywords
    4. Skills (if provided) must not contain prohibited keywords

    Args:
        title: Gig title
        description: Gig description
        category: Category slug
        skills: Optional skills text

    Returns:
        Tuple of (is_compliant, validation_result_dict)

        validation_result_dict contains:
        {
            'is_compliant': bool,
            'errors': List[str],  # User-facing error messages
            'violations': {
                'category': bool,
                'title': List[str],
                'description': List[str],
                'skills': List[str]
            },
            'message_en': str,  # English error message
            'message_ms': str   # Malay error message
        }
    """
    result = {
        'is_compliant': True,
        'errors': [],
        'violations': {
            'category': False,
            'title': [],
            'description': [],
            'skills': []
        },
        'message_en': '',
        'message_ms': ''
    }

    # 1. Validate category
    category_valid, category_error = validate_category(category)
    if not category_valid:
        result['is_compliant'] = False
        result['violations']['category'] = True
        result['errors'].append(category_error)

    # 2. Check title for prohibited keywords
    title_compliant, title_violations = check_prohibited_keywords(title)
    if not title_compliant:
        result['is_compliant'] = False
        result['violations']['title'] = title_violations
        result['errors'].append(
            f"Title contains prohibited content: {', '.join(title_violations[:3])} / "
            f"Tajuk mengandungi kandungan yang dilarang: {', '.join(title_violations[:3])}"
        )

    # 3. Check description for prohibited keywords
    desc_compliant, desc_violations = check_prohibited_keywords(description)
    if not desc_compliant:
        result['is_compliant'] = False
        result['violations']['description'] = desc_violations
        result['errors'].append(
            f"Description contains prohibited content: {', '.join(desc_violations[:3])} / "
            f"Penerangan mengandungi kandungan yang dilarang: {', '.join(desc_violations[:3])}"
        )

    # 4. Check skills for prohibited keywords (if provided)
    if skills:
        skills_compliant, skills_violations = check_prohibited_keywords(skills)
        if not skills_compliant:
            result['is_compliant'] = False
            result['violations']['skills'] = skills_violations
            result['errors'].append(
                f"Skills contain prohibited content: {', '.join(skills_violations[:3])} / "
                f"Kemahiran mengandungi kandungan yang dilarang: {', '.join(skills_violations[:3])}"
            )

    # Generate comprehensive error messages
    if not result['is_compliant']:
        result['message_en'] = (
            "This gig cannot be posted because it contains non-halal elements. "
            "GigHala is a strictly halal-compliant platform. "
            "Please review the prohibited content guidelines and modify your gig."
        )
        result['message_ms'] = (
            "Gig ini tidak boleh dipos kerana mengandungi elemen yang tidak halal. "
            "GigHala adalah platform yang mematuhi halal secara ketat. "
            "Sila semak garis panduan kandungan yang dilarang dan ubah suai gig anda."
        )

    return result['is_compliant'], result


def get_category_display_name(category_slug: str, language: str = 'en') -> str:
    """
    Get display name for a category in the specified language.

    Args:
        category_slug: Category slug (e.g., 'design')
        language: 'en' for English, 'ms' for Malay

    Returns:
        Display name in the specified language, or the slug if not found
    """
    for cat in HALAL_APPROVED_CATEGORIES:
        if cat['slug'] == category_slug:
            if language == 'ms':
                return cat['name_ms']
            return cat['name_en']
    return category_slug


def get_halal_guidelines_text() -> Dict[str, str]:
    """
    Get halal compliance guidelines text in both languages.

    Returns:
        Dictionary with 'en' and 'ms' keys containing guidelines text
    """
    return {
        'en': """
GigHala Halal Compliance Guidelines:

STRICTLY PROHIBITED:
❌ Alcohol, tobacco, drugs, or intoxicants
❌ Gambling, betting, or games of chance
❌ Pork or non-halal meat products
❌ Adult content, pornography, or sexual services
❌ Interest-based finance (riba) or usury
❌ Fraud, scams, or deceptive schemes
❌ Black magic, occult, or fortune telling
❌ Religious defamation or blasphemy
❌ Any haram activities prohibited by Islamic law

REQUIREMENTS:
✅ Select from approved halal categories only
✅ Ensure all content is Shariah-compliant
✅ Use respectful and modest language
✅ Confirm your gig serves halal purposes
✅ Report any violations to halal@gighala.com

When in doubt, contact our Halal Compliance Team.
        """,
        'ms': """
Garis Panduan Pematuhan Halal GigHala:

DILARANG SAMA SEKALI:
❌ Alkohol, tembakau, dadah, atau bahan memabukkan
❌ Judi, pertaruhan, atau permainan nasib
❌ Daging babi atau produk daging tidak halal
❌ Kandungan dewasa, pornografi, atau perkhidmatan seksual
❌ Kewangan berasaskan faedah (riba) atau riba
❌ Penipuan, skim, atau rancangan menipu
❌ Sihir, ilmu ghaib, atau ramalan nasib
❌ Penghujatan agama atau penghujatan
❌ Sebarang aktiviti haram yang dilarang oleh undang-undang Islam

KEPERLUAN:
✅ Pilih daripada kategori halal yang diluluskan sahaja
✅ Pastikan semua kandungan mematuhi Syariah
✅ Gunakan bahasa yang sopan dan sederhana
✅ Sahkan gig anda untuk tujuan halal
✅ Laporkan sebarang pelanggaran ke halal@gighala.com

Jika ragu-ragu, hubungi Pasukan Pematuhan Halal kami.
        """
    }


# =============================================================================
# LOGGING & AUDIT TRAIL
# =============================================================================

def log_halal_violation(
    user_id: int,
    gig_id: int,
    violation_type: str,
    violations: List[str],
    ip_address: str = None
):
    """
    Log halal compliance violations for admin review and security audit.

    This function should be called whenever a gig fails halal validation.
    It creates an audit trail for compliance monitoring and pattern detection.

    Args:
        user_id: ID of the user attempting to post the gig
        gig_id: ID of the gig (if available, else None)
        violation_type: Type of violation ('category', 'keywords', 'multiple')
        violations: List of specific violations detected
        ip_address: User's IP address (optional, for security)
    """
    # This will be implemented in app.py using the existing security_logger
    # For now, this is a placeholder that documents the expected behavior
    pass


# =============================================================================
# CATEGORY HELPERS
# =============================================================================

def get_categories_for_dropdown() -> List[Dict[str, str]]:
    """
    Get formatted category list for frontend dropdowns.

    Returns:
        List of dicts with slug, name_en, name_ms, and icon
    """
    return [
        {
            'slug': cat['slug'],
            'name_en': cat['name_en'],
            'name_ms': cat['name_ms'],
            'display': f"{cat['icon']} {cat['name_en']} / {cat['name_ms']}",
            'icon': cat['icon']
        }
        for cat in HALAL_APPROVED_CATEGORIES
    ]


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    'HALAL_APPROVED_CATEGORIES',
    'HALAL_APPROVED_CATEGORY_SLUGS',
    'PROHIBITED_KEYWORDS',
    'ALL_PROHIBITED_KEYWORDS',
    'check_prohibited_keywords',
    'validate_category',
    'validate_gig_halal_compliance',
    'get_category_display_name',
    'get_halal_guidelines_text',
    'log_halal_violation',
    'get_categories_for_dropdown',
]
