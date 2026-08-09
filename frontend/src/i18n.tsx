import { PropsWithChildren, createContext, useContext, useEffect, useMemo, useState } from "react";

export type AppLocale = "en" | "ar-EG";
export type Locale = AppLocale;

export const LOCALE_STORAGE_KEY = "permitops.locale";
const LEGACY_LOCALE_KEYS = ["permitops-locale", "permitops-about-language", "permitops-language", "about-locale", "readiness-locale", "locale", "language"];

const translations: Record<string, string> = {
  "My Work": "عملي", "Opportunities": "الفرص", "Engineering & Closeout": "الهندسة والإقفال", "Notifications & delivery": "الإشعارات والتسليم", "Verify Data": "مراجعة البيانات",
  "Permits": "التصاريح", "Reviews": "المراجعات", "Issues": "المشكلات", "Notifications": "الإشعارات",
  "Administration": "الإدارة", "About PermitOps": "حول PermitOps", "PERMIT WORKFLOW": "سير عمل التصاريح",
  "Demo as": "العرض بدور", "Permit Preparer": "مُعدّ التصريح", "Data Verifier": "مدقق البيانات",
  "Responsible Engineer": "المهندس المسؤول", "Package Approver": "معتمد الحزمة", "Final Submitter": "المُرسل النهائي",
  "System Admin": "مسؤول النظام", "Current user": "المستخدم الحالي", "Safe boundary": "حدود آمنة",
  "Synthetic data only": "بيانات اصطناعية فقط", "No portal writes": "لا كتابة في البوابة", "No closure automation": "لا أتمتة للإقفال",
  "SYNTHETIC PROTOTYPE": "نموذج أولي اصطناعي", "SYNTHETIC DEV": "تطوير اصطناعي", "AMEC Engineering": "هندسة AMEC",
  "SYNTHETIC PROTOTYPE · NO PORTAL WRITES · HUMAN SUBMISSION REQUIRED": "نموذج أولي اصطناعي · لا كتابة في البوابة · الإرسال البشري مطلوب",
  "HUMAN SUBMISSION REQUIRED": "الإرسال البشري مطلوب", "Return to My Work": "العودة إلى عملي", "English": "الإنجليزية", "العربي": "العربية",
  "Loading synthetic baseline…": "جارٍ تحميل خط الأساس الاصطناعي…", "API unavailable": "واجهة API غير متاحة",
  "Open": "فتح", "Close": "إغلاق", "Save": "حفظ", "Cancel": "إلغاء", "Retry": "إعادة المحاولة",
  "Create": "إنشاء", "Delete": "حذف", "Edit": "تحرير", "Filter": "تصفية", "Search": "بحث", "Submit": "إرسال",
  "Approve": "اعتماد", "Verify": "تحقق", "Assign": "تعيين", "Refresh": "تحديث", "No records": "لا توجد سجلات",
  "No results": "لا توجد نتائج", "Project detail": "تفاصيل المشروع", "Go-Live Setup": "التجهيز للتشغيل",
  "Control diagnostics": "تشخيص الضوابط", "Project register": "سجل المشاريع", "Documents / source evidence": "المستندات / أدلة المصدر",
  "Conflicts": "التعارضات", "Configuration": "الإعدادات", "Package readiness": "جاهزية الحزمة", "Municipality preparation": "إعداد البلدية",
  "Findings & work": "الملاحظات والعمل", "Lineage & validity": "النَسَب والصلاحية", "Attachments & grids": "المرفقات والجداول",
  "Test extraction": "تجربة الاستخراج", "Expected results": "النتائج المتوقعة", "Test analysis": "تحليل الاختبار",
  "Test targets": "أهداف الاختبار", "Test documents": "مستندات الاختبار", "Tier 1 decisions": "قرارات المستوى الأول",
  "Tier 2 backlog": "المتراكم للمستوى الثاني", "Delivery / data": "التسليم / البيانات", "Go-live setup decision": "قرار تجهيز التشغيل",
  "Setup baseline": "خط أساس التجهيز", "Commercial draft": "المسودة التجارية", "Submission confirmation": "تأكيد الإرسال",
  "Project setup": "تجهيز المشروع", "Business case": "حالة الأعمال", "Business baseline": "خط أساس الأعمال",
  "Privacy & data": "الخصوصية والبيانات", "Volume baseline": "خط أساس الحجم", "Ministry inquiry": "استفسار الوزارة",
  "RAID log": "سجل RAID", "Expansion foundation": "أساس التوسع",
};

export function translate(value: string, locale: Locale): string {
  return locale === "ar-EG" ? (translations[value] || value) : value;
}

export function normalizeLocale(value: unknown): AppLocale {
  const normalized = String(value || "").trim().toLowerCase();
  if (["ar", "ar-eg", "arabic"].includes(normalized)) return "ar-EG";
  if (["en", "en-us", "english"].includes(normalized)) return "en";
  return "en";
}

function readInitialLocale(): AppLocale {
  const canonical = localStorage.getItem(LOCALE_STORAGE_KEY);
  const legacy = LEGACY_LOCALE_KEYS.map((key) => localStorage.getItem(key)).find((value) => value !== null);
  const locale = normalizeLocale(canonical ?? legacy);
  localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  for (const key of LEGACY_LOCALE_KEYS) localStorage.removeItem(key);
  return locale;
}

const originalText = new WeakMap<Text, string>();
const lastLocalizedText = new WeakMap<Text, string>();
const originalAttributes = new WeakMap<HTMLElement, Map<string, string | null>>();
const lastLocalizedAttributes = new WeakMap<HTMLElement, Map<string, string>>();

function localizeDom(locale: Locale) {
  const isArabic = locale === "ar-EG";
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  let node: Node | null;
  while ((node = walker.nextNode())) nodes.push(node as Text);
  for (const text of nodes) {
    const current = text.nodeValue || "";
    if (!current.trim() || text.parentElement?.closest("script,style")) continue;
    const previous = lastLocalizedText.get(text);
    if (!originalText.has(text) || (previous !== undefined && current !== previous)) originalText.set(text, current);
    const source = originalText.get(text) || current;
    const next = isArabic ? source.replace(source.trim(), translate(source.trim(), locale)) : source;
    if (current !== next) text.nodeValue = next;
    lastLocalizedText.set(text, next);
  }
  document.querySelectorAll<HTMLElement>("input,textarea,button,[aria-label],[title]").forEach((element) => {
    if (!originalAttributes.has(element)) originalAttributes.set(element, new Map());
    if (!lastLocalizedAttributes.has(element)) lastLocalizedAttributes.set(element, new Map());
    const sourceAttributes = originalAttributes.get(element)!;
    const localizedAttributes = lastLocalizedAttributes.get(element)!;
    for (const attr of ["placeholder", "aria-label", "title"]) {
      const current = element.getAttribute(attr);
      const previous = localizedAttributes.get(attr);
      if (!sourceAttributes.has(attr) || (previous !== undefined && current !== previous)) sourceAttributes.set(attr, current);
      const source = sourceAttributes.get(attr);
      if (source === null || source === undefined) continue;
      const next = isArabic ? translate(source, locale) : source;
      if (current !== next) element.setAttribute(attr, next);
      localizedAttributes.set(attr, next);
    }
  });
}

type LocaleContextValue = { locale: Locale; setLocale: (locale: Locale) => void; t: (value: string) => string };
const LocaleContext = createContext<LocaleContextValue>({ locale: "en", setLocale: () => undefined, t: (value) => value });

export function LocaleProvider({ children }: PropsWithChildren) {
  const [locale, setLocaleState] = useState<AppLocale>(readInitialLocale);
  const setLocale = (next: Locale) => {
    const normalized = normalizeLocale(next);
    localStorage.setItem(LOCALE_STORAGE_KEY, normalized);
    for (const key of LEGACY_LOCALE_KEYS) localStorage.removeItem(key);
    setLocaleState(normalized);
  };
  useEffect(() => {
    const isArabic = locale === "ar-EG";
    const direction = isArabic ? "rtl" : "ltr";
    document.documentElement.lang = locale;
    document.documentElement.dir = direction;
    document.body.dir = direction;
    const appRoot = document.getElementById("root") || document.body.firstElementChild;
    appRoot?.setAttribute("dir", direction);
    for (const element of [document.documentElement, document.body, appRoot].filter(Boolean) as HTMLElement[]) {
      element.classList.remove("locale-ar", "rtl", "arabic");
      if (isArabic) element.classList.add("locale-ar");
    }
    localizeDom(locale);
    const observer = new MutationObserver(() => localizeDom(locale));
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [locale]);
  const value = useMemo(() => ({ locale, setLocale, t: (value: string) => translate(value, locale) }), [locale]);
  return <LocaleContext.Provider value={value}><button className="global-language-switch" type="button" onClick={() => setLocale(locale === "ar-EG" ? "en" : "ar-EG")} aria-label={locale === "ar-EG" ? "Switch to English" : "Switch to Arabic"}>{locale === "ar-EG" ? "English" : "العربي"}</button>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}
