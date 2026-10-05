// Product-facing text. Arabic only (SPEC.md §8, §6.6, §6.4). Keep every value free of Latin letters;
// strings.test.js enforces this.
export const strings = {
  appName: 'تبيّن',
  tagline: 'تحقّق من الادعاءات والأسئلة الدينية من مصادرها المعتمدة.',
  skipToContent: 'تخطَّ إلى المحتوى',
  aiNotice: 'هذه أداة ذكاء اصطناعي، وليست فتوى.',
  themeToDark: 'تفعيل الوضع الداكن',
  themeToLight: 'تفعيل الوضع الفاتح',
  // Temporary: remove when the check endpoint is wired (T-504).
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
  resultsRetry: 'حاول مرة أخرى',
  resultsHeading: 'النتائج',
  checkErrors: {
    NO_CLAIMS: 'لم نجد في النص ادعاءً يمكن التحقق منه. جرّب صياغة الادعاء كجملة واضحة.',
    TEXT_NOT_SUPPORTED_LANG: 'اللغة غير مدعومة. أدخل النص بالعربية أو بالإنجليزية.',
    PIPELINE_DEGRADED: 'تعذّر إكمال التحقق الآن، ولن نعرض نتيجة غير مكتملة. حاول مرة أخرى بعد قليل.',
    RATE_LIMITED: 'طلبات كثيرة في وقت قصير. انتظر دقيقة ثم حاول مرة أخرى.',
    NETWORK: 'تعذّر الاتصال بالخدمة. تحقق من اتصالك بالإنترنت ثم حاول مرة أخرى.',
    UNKNOWN: 'حدث خطأ غير متوقع. حاول مرة أخرى.',
  },
}
