import os
import json


def load_translations(translations_dir):
    """
    Зарежда всички JSON файлове с преводи от указаната директория.
    Имената на файловете (без .json) се използват като кодове на езици.
    """
    translations = {}
    if not os.path.isdir(translations_dir):
        print(f"Warning: Translations directory '{translations_dir}' not found.")
        return translations

    for filename in os.listdir(translations_dir):
        if filename.endswith(".json"):
            lang_code = filename[:-5]  # Премахва '.json'
            filepath = os.path.join(translations_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    translations[lang_code] = json.load(f)
            except Exception as e:
                print(f"Error loading translation file {filename}: {e}")
    return translations


def get_translation(key, lang_code, translations_data, fallback_lang='en'):
    """
    Взема превод за даден ключ и език.
    Ако ключът не е намерен за дадения език, опитва с fallback езика.
    Ако и там не е намерен, връща самия ключ.
    """
    try:
        # Опит за намиране на вложен ключ
        keys = key.split('.')
        value = translations_data.get(lang_code, {})
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break

        if value is not None:
            return value

        # Fallback към основния език, ако е различен
        if lang_code != fallback_lang:
            value = translations_data.get(fallback_lang, {})
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    value = None
                    break
            if value is not None:
                return value

    except KeyError:
        pass  # Ще се върне ключът по-долу

    # Ако ключът не е намерен никъде
    # print(f"Warning: Translation key '{key}' not found for language '{lang_code}' or fallback '{fallback_lang}'.")
    return key  # Връща самия ключ като fallback