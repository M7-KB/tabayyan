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
}
