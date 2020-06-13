

class Translator:
    def __init__(self, rows, logger):
        self.data = {}
        self.default_lang = 'en'
        self.logger = logger
        if rows is None:
            self.logger.error('Translation object has no rows!')
            return

        for row in rows:
            if row['keyword'] not in self.data:
                self.data[row['keyword']] = {}

            self.data[row['keyword']][row['lang']] = row['value']

    def setLang(self, lang):
        self.default_lang = lang

    def getTranslation(self, keyword):
        return self.getLangTranslation(self.default_lang, keyword)

    def getLangTranslation(self, lang, keyword):
        try:
            return self.data[keyword][lang]
        except Exception as e:
            self.logger.error('Failed to get translation for: lang={lang}, keyword={keyword}, reason: {err}'.format(lang=lang, keyword=keyword, err=str(e)))
            if lang.lower() != self.default_lang:
                return self.getLangTranslation(self.default_lang, keyword)
            return 'NO_TRANSLATION_{lang}_{keyword}'.format(lang=lang, keyword=keyword)
