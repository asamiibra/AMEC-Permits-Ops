import { PropsWithChildren, createContext, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "en" | "ar";

const translations: Record<string, string> = {
  "My Work": "عملي", "Opportunities": "الفرص", "Engineering & Closeout": "الهندسة والإقفال",
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
  return locale === "ar" ? (translations[value] || value) : value;
}

function localizeDom(locale: Locale) {
  if (locale !== "ar") return;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  let node: Node | null;
  while ((node = walker.nextNode())) nodes.push(node as Text);
  for (const text of nodes) {
    const value = text.nodeValue?.trim();
    if (!value || text.parentElement?.closest("script,style")) continue;
    const translated = translate(value, locale);
    if (translated !== value && text.nodeValue) text.nodeValue = text.nodeValue.replace(value, translated);
  }
  document.querySelectorAll<HTMLElement>("input,textarea,button,[aria-label],[title]").forEach((element) => {
    for (const attr of ["placeholder", "aria-label", "title"]) {
      const value = element.getAttribute(attr);
      if (value) element.setAttribute(attr, translate(value, locale));
    }
  });
}

type LocaleContextValue = { locale: Locale; setLocale: (locale: Locale) => void; t: (value: string) => string };
const LocaleContext = createContext<LocaleContextValue>({ locale: "en", setLocale: () => undefined, t: (value) => value });

export function LocaleProvider({ children }: PropsWithChildren) {
  const [locale, setLocaleState] = useState<Locale>(() => (localStorage.getItem("permitops-locale") as Locale) || "en");
  const setLocale = (next: Locale) => { localStorage.setItem("permitops-locale", next); setLocaleState(next); };
  useEffect(() => {
    document.documentElement.lang = locale === "ar" ? "ar-EG" : "en";
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
    document.body.classList.toggle("locale-ar", locale === "ar");
    localizeDom(locale);
    const observer = new MutationObserver(() => localizeDom(locale));
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [locale]);
  const value = useMemo(() => ({ locale, setLocale, t: (value: string) => translate(value, locale) }), [locale]);
  return <LocaleContext.Provider value={value}><button className="global-language-switch" type="button" onClick={() => setLocale(locale === "ar" ? "en" : "ar")} aria-label={locale === "ar" ? "Switch to English" : "Switch to Arabic"}>{locale === "ar" ? "English" : "العربي"}</button>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}
