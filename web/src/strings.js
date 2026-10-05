// Product-facing text. Arabic only (SPEC.md §8, §6.6, §6.4). Keep every value free of Latin letters;
// strings.test.js enforces this.
export const strings = {
  appName: 'تبيّن',
  tagline: 'تحقّق من الادعاءات والأسئلة الدينية من مصادرها المعتمدة.',
  skipToContent: 'تخطَّ إلى المحتوى',
  aiNotice: 'هذه أداة ذكاء اصطناعي، وليست فتوى.',
  themeToDark: 'تفعيل الوضع الداكن',
  themeToLight: 'تفعيل الوضع الفاتح',
  // Shown until GET /health answers (see api/health.js).
  previewBanner: 'نسخة تجريبية للتطوير. التحقق من الادعاءات غير مفعّل بعد.',

  inputHeading: 'ما الذي تريد التحقق منه؟',
  textLabel: 'الادعاء أو السؤال المراد التحقق منه',
  textPlaceholder: 'اكتب الادعاء أو السؤال هنا…',
  textEmptyHint: 'اكتب الادعاء أو السؤال لتتمكن من الإرسال.',
  textSubmit: 'إرسال',

  // Example chips: a short label and the approved text it fills into the composer. These are owner-reviewed
  // items. The list stays empty until the owner supplies the approved texts, and no chip row is shown meanwhile.
  examplesLabel: 'أمثلة للتجربة',
  exampleChips: [],

  privacySummary: 'يُرسَل نصك إلى مزوّد ذكاء اصطناعي، ولا نحفظه في خوادمنا.',
  privacyLines: [
    'يُرسَل النص الذي تُدخله إلى مزوّد خدمة ذكاء اصطناعي، وتُرسَل عبارات البحث المستخرجة منه إلى المصادر المعتمدة.',
    'لا نحفظه في خوادمنا، وقد يحتفظ مزوّد الخدمة بالبيانات مؤقتاً وفق سياسته.',
    'لا تحتاج إلى حساب.',
  ],

  uploadHeading: 'أو ارفع مقطعاً صوتياً أو مرئياً',
  uploadLimits: 'الحد الأقصى ٣ دقائق وحجم ٢٥ ميغابايت.',
  uploadChooseFile: 'اختر ملفاً',
  uploadNoFileHint: 'اختر ملفاً أولاً.',
  uploadNoConsentHint: 'ضع علامة على خانة الموافقة لتفعيل الرفع.',
  uploadSubmit: 'رفع المقطع',
  consent: 'أؤكد أن لدي حق مشاركة هذا المقطع لغرض التحقق',

  // Audio and video clip (behind features.mediaUpload). The privacy copy for clips is the owner-approved
  // disclosure of SPEC.md §6.6 and §12; it is shown only when the flag is on.
  privacySummaryMedia: 'يُرسَل نصك أو مقطعك إلى مزوّد ذكاء اصطناعي، ولا نحفظه في خوادمنا.',
  privacyLinesMedia: [
    'تُرسل النصوص والمقاطع الصوتية والمرئية التي تُدخلها إلى مزوّد خدمة ذكاء اصطناعي لمعالجتها، ولا نحفظها في خوادمنا.',
    'تُحذف المقاطع بعد المعالجة مباشرة، ولا تُكتب على القرص ولا تُسجَّل في السجلات.',
    'لا نحدد هوية المتحدث ولا نتعرف على الأصوات، والبطاقات تحكم على الأقوال لا على الأشخاص.',
    'قد يحتفظ مزوّد الخدمة بالبيانات مؤقتاً وفق سياسته. لا تحتاج إلى حساب.',
  ],
  transcribingHeading: 'جارٍ تفريغ المقطع',
  transcribing: 'جارٍ تحويل المقطع إلى نص… قد يستغرق ذلك دقيقة.',
  transcriptHeading: 'راجع النص قبل التحقق',
  transcriptHint: 'صحّح النص إن لزم. لن يبدأ التحقق قبل أن تؤكد النص.',
  // Default for the transcribe response's notice_ar (SPEC.md §3); the screen shows the server's text when present.
  transcriptNotice: 'راجع النص وصحّحه قبل المتابعة',
  transcriptStubNote: 'هذا نص تجريبي للعرض، ولم يُستخرج من المقطع.',
  transcriptStubText: 'نص تجريبي للمراجعة.',
  transcriptLabel: 'النص المستخرج من المقطع',
  transcriptEmpty: 'النص فارغ. أضف نصاً، أو ارجع واختر مقطعاً آخر.',
  transcriptConfirm: 'تأكيد النص والتحقق',
  transcriptDiscard: 'إلغاء والعودة',
  mediaErrorHeading: 'تعذّر تفريغ المقطع',
  mediaErrorBack: 'العودة لاختيار ملف',
  transcribeErrors: {
    CONSENT_REQUIRED: 'ضع علامة على خانة الموافقة قبل رفع المقطع.',
    MEDIA_TOO_LONG: 'المقطع أطول من ٣ دقائق. اختر مقطعاً أقصر.',
    MEDIA_TOO_LARGE: 'حجم الملف أكبر من ٢٥ ميغابايت. اختر مقطعاً أصغر.',
    UNSUPPORTED_MEDIA: 'نوع الملف غير مدعوم. اختر ملف صوت أو فيديو.',
    TRANSCRIBE_UNAVAILABLE: 'خدمة التفريغ غير متاحة الآن. حاول بعد قليل، أو اكتب النص مباشرة.',
    NETWORK: 'تعذّر الاتصال بالخدمة. تحقق من اتصالك ثم حاول مرة أخرى.',
    UNKNOWN: 'حدث خطأ غير متوقع أثناء التفريغ. حاول مرة أخرى.',
  },

  // Card UI (T-505). stateLabels and sourceTextIntro follow the SPEC.md §12 item 1 table. Only
  // supported_contradicts and sourceTextIntro are owner-given; the other three labels are PROVISIONAL
  // and need owner review before release (SPEC.md §0.7).
  stateLabels: {
    supported_confirms: 'يؤيده المصدر المعتمد',
    supported_contradicts: 'لا يطابق المصدر المعتمد',
    disputed: 'مسألة مختلف فيها',
    cannot_confirm: 'لا يمكن التأكد من المصادر المتاحة',
  },
  sourceTextIntro: 'النص كما ورد في المصدر:',
  claimHeading: 'الادعاء كما أُدخل',
  timestampFrom: 'من',
  timestampTo: 'إلى',
  explanationHeading: 'شرح مُولَّد بالذكاء الاصطناعي',
  scriptureLabel: 'نص من المصدر',
  sourceLink: 'المصدر',
  quoteSourceNote: 'النصوص منقولة من مصادرها المعتمدة كما هي، مع الرابط للتحقق.',
  // Published answer (SPEC.md §0.5, §0.8). The excerpt is the source's own text, shown apart from our explanation.
  publishedAnswerHeading: 'جواب منشور من مصدر معتمد',
  publishedAnswerNote: 'هذا نص الجواب كما نشره المصدر، وليس شرحاً من تبيّن.',
  publishedAnswerLink: 'عرض الجواب في المصدر',
  translationLabel: 'ترجمة من المصدر',
  translationSourceLink: 'مصدر الترجمة',
  gradingLabel: 'الحكم',
  gradingSourceLink: 'مصدر الحكم',
  positionsHeading: 'المواقف المختلفة، بلا ترتيب',
  misquoteHeading: 'ملاحظة: نص قريب من نص في المصدر',
  cannotConfirmBody: 'لم نجد في المصادر المعتمدة ما يكفي للتأكد من هذا الادعاء.',
  referralHeading: 'جهة مرجعية للفتوى',
  readyQuestionHeading: 'سؤال جاهز للطرح',
  termHeading: 'المصطلح',
  verifyHeading: 'كيف تتحقق بنفسك؟',
  devPreviewBanner: 'بيانات تجريبية للعرض فقط، ولا تمثل مصدراً معتمداً.',

  // Results and check errors (T-504). Each error gives a next step. Provisional copy: owner review.
  resultsLoading: 'جارٍ التحقق من الادعاءات… قد يستغرق ذلك دقيقة.',
  resultsEmpty: 'لم تُرجع الخدمة أي بطاقة لهذا النص. عدّل النص وحاول مرة أخرى.',
  resultsEditText: 'تعديل النص',
  resultsEditClaims: 'تعديل الادعاءات',
  resultsRetry: 'حاول مرة أخرى',
  resultsHeading: 'النتائج',
  resultsCancel: 'إلغاء والرجوع إلى الادعاءات',
  checkErrors: {
    NO_CLAIMS: 'لم نجد في النص ادعاءً يمكن التحقق منه. جرّب صياغة الادعاء كجملة واضحة.',
    TEXT_NOT_SUPPORTED_LANG: 'اللغة غير مدعومة. أدخل النص بالعربية أو بالإنجليزية.',
    INVALID_REQUEST: 'تعذّر إرسال الطلب بصيغته الحالية. عدّل النص وحاول مرة أخرى.',
    PIPELINE_DEGRADED: 'تعذّر إكمال التحقق الآن، ولن نعرض نتيجة غير مكتملة. حاول مرة أخرى بعد قليل.',
    RATE_LIMITED: 'طلبات كثيرة في وقت قصير. انتظر دقيقة ثم حاول مرة أخرى.',
    NETWORK: 'تعذّر الاتصال بالخدمة. تحقق من اتصالك بالإنترنت ثم حاول مرة أخرى.',
    TIMEOUT: 'استغرق الطلب وقتاً أطول من المتوقع. نصّك وادعاءاتك محفوظة، حاول مرة أخرى.',
    UNKNOWN: 'حدث خطأ غير متوقع. حاول مرة أخرى.',
  },

  // Claim review (SPEC.md §6.2): the extracted claims are shown for the user to confirm or edit before any check runs.
  extractingHeading: 'جارٍ استخراج الادعاءات',
  extracting: 'جارٍ تحليل النص لاستخراج الادعاءات… قد يستغرق ذلك لحظات.',
  extractCancel: 'إلغاء والرجوع إلى النص',
  claimsHeading: 'الادعاءات المستخرجة',
  claimsHint: 'راجع كل ادعاء وصحّحه إن لزم. أفرغ خانة الادعاء لتجاهله. لن يبدأ التحقق قبل أن تؤكد.',
  claimLabel: 'الادعاء',
  claimsNoneLeft: 'اترك ادعاءً واحداً على الأقل مكتوباً لتتمكن من التحقق.',
  claimsEmpty: 'لم نجد في النص ادعاءً يمكن التحقق منه. عدّل النص وحاول مرة أخرى.',
  claimsConfirm: 'تأكيد والتحقق',
  claimsBack: 'العودة إلى النص',
  extractErrorHeading: 'تعذّر استخراج الادعاءات',
  extractRetry: 'حاول مرة أخرى',
}
