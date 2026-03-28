import en from './en.json';
import zhHans from './zh-Hans.json';
import zhHant from './zh-Hant.json';

export type Locale = 'en' | 'zh-Hans' | 'zh-Hant';

const translations: Record<Locale, typeof en> = {
  en,
  'zh-Hans': zhHans,
  'zh-Hant': zhHant,
};

export function t(locale: Locale, key: string): string {
  const keys = key.split('.');
  let result: unknown = translations[locale];
  for (const k of keys) {
    if (result && typeof result === 'object') {
      result = (result as Record<string, unknown>)[k];
    } else {
      return key;
    }
  }
  return typeof result === 'string' ? result : key;
}

export { en, zhHans, zhHant };
