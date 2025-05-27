#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import g4f
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

class Russian_German_Translator:
    def __init__(self):
        self.cache = {}
        self.cache_lock = threading.Lock()
        
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def get_cache_key(self, text, direction):
        text_hash = hashlib.md5(text.strip().lower().encode()).hexdigest()
        return f"{direction}:{text_hash}"
    
    def get_from_cache(self, text, direction):
        key = self.get_cache_key(text, direction)
        with self.cache_lock:
            return self.cache.get(key)
    
    def save_to_cache(self, text, direction, translation):
        key = self.get_cache_key(text, direction)
        with self.cache_lock:
            self.cache[key] = translation
    
    def try_model(self, model, messages, timeout=15):
        try:
            response = g4f.ChatCompletion.create(
                model=model,
                messages=messages,
                timeout=timeout
            )
            return response.strip() if response and response.strip() else None
        except Exception:
            return None
    
    def translate_ru_to_de(self, text):
        cached = self.get_from_cache(text, 'ru_to_de')
        if cached:
            return f"{cached}"
        
        prompt = f"""ЭКСПЕРТНЫЙ ПЕРЕВОД: РУССКИЙ → НЕМЕЦКИЙ

ТВОЯ РОЛЬ: Ты - элитный лингвист-переводчик с 20+ лет опыта, специализирующийся на русско-немецкой паре языков. Ты знаешь каждую грамматическую тонкость, культурную особенность и стилистический нюанс обоих языков.

ИСХОДНЫЙ ТЕКСТ: "{text}"

ЗАДАЧА: Создать ИДЕАЛЬНЫЙ перевод, который:
Звучит как написанный носителем немецкого языка
Сохраняет 100% смысла и эмоциональной окраски
Учитывает все грамматические правила (падежи, роды, времена)
Подбирает наиболее точные лексические эквиваленты
Передает стиль речи (формальный/разговорный/сленг)
Адаптирует идиомы и фразеологизмы

АЛГОРИТМ ДЕЙСТВИЙ:
1. Анализируй контекст и подтекст
2. Определи стилистический регистр
3. Учти культурные особенности
4. Примени корректную немецкую грамматику
5. Проверь естественность звучания

  РЕЗУЛЬТАТ ДОЛЖЕН БЫТЬ:
- Грамматически безупречным
- Стилистически адекватным  
- Культурно адаптированным
- Максимально естественным

ВЫВЕДИ ТОЛЬКО ФИНАЛЬНЫЙ ПЕРЕВОД БЕЗ КОММЕНТАРИЕВ!

НЕМЕЦКИЙ ПЕРЕВОД:"""
        
        messages = [{"role": "user", "content": prompt}]
        
        models = ["gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"]

        futures = []
        for model in models:
            future = self.executor.submit(self.try_model, model, messages)
            futures.append(future)
        
        for future in as_completed(futures, timeout=20):
            try:
                result = future.result()
                if result and len(result) > 5:  
                    self.save_to_cache(text, 'ru_to_de', result)
                    return result
            except Exception:
                continue

        try:
            response = g4f.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "Ты профессиональный переводчик с русского на немецкий язык. Делай точные и естественные переводы."
                }, {
                    "role": "user", 
                    "content": f"Переведи на немецкий: {text}"
                }]
            )
            result = response.strip() if response else "Нет ответа"
            self.save_to_cache(text, 'ru_to_de', result)
            return result
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def translate_de_to_ru(self, text):

        cached = self.get_from_cache(text, 'de_to_ru')
        if cached:
            return f"[CACHE] {cached}"

        prompt = f"""ЭКСПЕРТНЫЙ ПЕРЕВОД: НЕМЕЦКИЙ → РУССКИЙ

ТВОЯ РОЛЬ: Ты - виртуозный переводчик-полиглот, мастер немецко-русского перевода с безупречным чувством языка. Твои переводы неотличимы от текстов, написанных носителями русского языка.

ИСХОДНЫЙ ТЕКСТ: "{text}"

🔥 ЗАДАЧА: Создать БЕЗУПРЕЧНЫЙ перевод, который:
✅ Звучит абсолютно естественно на русском языке
✅ Передает каждый оттенок смысла и эмоций
✅ Соблюдает все нормы русской грамматики и стилистики
✅ Использует максимально точную лексику
✅ Сохраняет регистр речи (официальный/бытовой/молодежный)
✅ Адаптирует немецкие реалии для русского читателя

🧠 МЫСЛИТЕЛЬНЫЙ ПРОЦЕСС:
1. Декодируй глубинный смысл немецкого текста
2. Определи коммуникативную интенцию автора
3. Найди оптимальные русские эквиваленты
4. Проверь гармонию и благозвучие
5. Убедись в естественности конечного результата

⚡ ТВОЙ ПЕРЕВОД ДОЛЖЕН:
- Читаться как оригинальный русский текст
- Быть стилистически выверенным
- Сохранять авторскую интонацию
- Звучать современно и живо

ВЫВЕДИ ТОЛЬКО ИДЕАЛЬНЫЙ РУССКИЙ ПЕРЕВОД!

РУССКИЙ ПЕРЕВОД:"""
        
        messages = [{"role": "user", "content": prompt}]
        
        models = ["gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"]
        
        futures = []
        for model in models:
            future = self.executor.submit(self.try_model, model, messages)
            futures.append(future)

        for future in as_completed(futures, timeout=20):
            try:
                result = future.result()
                if result and len(result) > 5: 
                    self.save_to_cache(text, 'de_to_ru', result)
                    return result
            except Exception:
                continue
        
        try:
            response = g4f.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "Ты профессиональный переводчик с немецкого на русский язык. Делай точные и естественные переводы."
                }, {
                    "role": "user", 
                    "content": f"Переведи на русский: {text}"
                }]
            )
            result = response.strip() if response else "Нет ответа"
            self.save_to_cache(text, 'de_to_ru', result)
            return result
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def detect_language(self, text):
        cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        german_chars = ['ä', 'ö', 'ü', 'ß', 'Ä', 'Ö', 'Ü']
        german_count = sum(1 for char in text if char in german_chars)
        
        if cyrillic_count > 0:
            return 'ru'
        elif german_count > 0 or any(word in text.lower() for word in ['der', 'die', 'das', 'und', 'ich', 'ist', 'ein', 'eine']):
            return 'de'
        else:
            return 'unknown'
    
    def auto_translate(self, text):
        lang = self.detect_language(text)
        
        if lang == 'ru':
            return self.translate_ru_to_de(text), 'ru_to_de'
        elif lang == 'de':
            return self.translate_de_to_ru(text), 'de_to_ru'
        else:
            print("Не удалось определить язык. Пожалуйста, выберите направление перевода:")
            print("1 - Русский -> Немецкий")
            print("2 - Немецкий -> Русский")
            choice = input("Ваш выбор (1/2): ").strip()
            
            if choice == '1':
                return self.translate_ru_to_de(text), 'ru_to_de'
            elif choice == '2':
                return self.translate_de_to_ru(text), 'de_to_ru'
            else:
                return "Вы выбрали несуществующий вариант.", None

def main():
    translator = Russian_German_Translator()
    
    while True:
        try:
            text = input("\nВведите текст: ").strip()

            if not text:
                continue

            translation, direction = translator.auto_translate(text)
            
            if direction:
                print(f"Результат: {translation}")
            else:
                print(translation)
            
        except KeyboardInterrupt:
            translator.executor.shutdown(wait=True)
            break
        except Exception as e:
            print(f"\n[ERROR] > {str(e)}")
            time.sleep(10)

if __name__ == "__main__":
    main()
