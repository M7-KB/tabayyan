// Product-facing text. Arabic only (SPEC.md §8, §6.6, §6.4). Keep every value free of Latin letters;
// strings.test.js enforces this.
export const strings = {
  appName: 'تبيّن',
  tagline: 'تحقّق من الادعاءات الدينية في النص أو الرابط أو المقطع الصوتي',
  skipToContent: 'تخطَّ إلى المحتوى',
  aiNotice: 'هذه أداة ذكاء اصطناعي، وليست فتوى.',
  // Temporary: remove when the check endpoint is wired (T-504).
  previewBanner: 'نسخة تجريبية للتطوير. التحقق من الادعاءات غير مفعّل بعد.',

  inputHeading: 'ما الذي تريد التحقق منه؟',
  textLabel: 'النص المراد التحقق منه',
  textPlaceholder: 'الصق النص هنا…',
  textEmptyHint: 'اكتب نصاً أو الصقه لتتمكن من المتابعة.',
  textSubmit: 'متابعة',

  privacyHeading: 'الخصوصية',
  privacyLines: [
    'تُرسل النصوص والمقاطع الصوتية والمرئية التي تُدخلها إلى مزوّد خدمة ذكاء اصطناعي لمعالجتها، ولا نحفظها لدينا.',
    'تُحذف المقاطع الصوتية والمرئية بعد المعالجة مباشرة.',
    'لا تحتاج إلى حساب، ولا نخزّن أسئلتك.',
  ],

  uploadHeading: 'أو ارفع مقطعاً صوتياً أو مرئياً',
  uploadLimits: 'الحد الأقصى ٣ دقائق وحجم ٢٥ ميغابايت.',
  uploadChooseFile: 'اختر ملفاً',
  uploadNoFileHint: 'اختر ملفاً أولاً.',
  uploadNoConsentHint: 'ضع علامة على خانة الموافقة لتفعيل الرفع.',
  uploadSubmit: 'رفع المقطع',
  consent: 'أؤكد أن لدي حق مشاركة هذا المقطع لغرض التحقق',

  // Card UI (T-505). Two strings are owner-given and come from api/policy/content_policy.yaml:
  // stateLabels.supported_contradicts and sourceTextIntro. Everything else in this block is
  // PROVISIONAL: it is not in SPEC.md or the policy file yet, and needs owner and Sharia specialist
  // approval (SPEC.md §12 item 1) before release.
  stateLabels: {
    supported_confirms: 'مدعوم بالمصدر المعتمد',
    supported_contradicts: 'لا يطابق المصدر المعتمد',
    disputed: 'توجد مواقف مختلفة في المصادر',
    cannot_confirm: 'لا يمكن التأكد من المصدر المعتمد',
  },
  sourceTextIntro: 'النص كما ورد في المصدر:',
  claimHeading: 'الادعاء كما أُدخل',
  timestampFrom: 'من',
  timestampTo: 'إلى',
  explanationHeading: 'شرح مُولَّد بالذكاء الاصطناعي',
  scriptureLabel: 'نص من المصدر',
  sourceLink: 'المصدر',
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
}
