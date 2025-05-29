#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_from_directory
import g4f
import webbrowser
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import re

app = Flask(__name__)

class UniversalTranslator:
    def __init__(self):
        self.cache = {}
        self.word_cache = {}
        self.cache_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        self.languages = self.load_languages()
        
    def load_languages(self):
        try:
            with open('languages.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'auto': 'Автоопределение',
                'ru': 'Русский',
                'en': 'English',
                'de': 'Deutsch',
                'fr': 'Français',
                'es': 'Español',
                'it': 'Italiano',
                'pt': 'Português',
                'zh': '中文',
                'ja': '日本語',
                'ko': '한국어',
                'ar': 'العربية'
            }
    
    def get_cache_key(self, text, source_lang, target_lang):
        text_hash = hashlib.md5(text.strip().lower().encode()).hexdigest()
        return f"{source_lang}_{target_lang}:{text_hash}"
    
    def get_word_cache_key(self, word, source_lang, target_lang):
        word_hash = hashlib.md5(word.strip().lower().encode()).hexdigest()
        return f"word_{source_lang}_{target_lang}:{word_hash}"
    
    def get_from_cache(self, text, source_lang, target_lang):
        key = self.get_cache_key(text, source_lang, target_lang)
        with self.cache_lock:
            return self.cache.get(key)
    
    def save_to_cache(self, text, source_lang, target_lang, translation):
        key = self.get_cache_key(text, source_lang, target_lang)
        with self.cache_lock:
            self.cache[key] = translation
    
    def get_word_from_cache(self, word, source_lang, target_lang):
        key = self.get_word_cache_key(word, source_lang, target_lang)
        with self.cache_lock:
            return self.word_cache.get(key)
    
    def save_word_to_cache(self, word, source_lang, target_lang, translation):
        key = self.get_word_cache_key(word, source_lang, target_lang)
        with self.cache_lock:
            self.word_cache[key] = translation
    
    def extract_words(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def smart_translate_with_word_cache(self, text, source_lang, target_lang):
        words = self.extract_words(text)
        cached_words = {}
        uncached_words = []
        
        for word in set(words):
            cached_translation = self.get_word_from_cache(word, source_lang, target_lang)
            if cached_translation:
                cached_words[word] = cached_translation
            else:
                uncached_words.append(word)
        
        print(f"Cached words: {len(cached_words)}/{len(set(words))}")
        
        if not uncached_words:
            return self.reconstruct_translation_from_words(text, cached_words)
        
        if len(cached_words) >= len(set(words)) * 0.5:
            uncached_text = ' '.join(uncached_words)
            uncached_translation = self.translate_uncached_words(uncached_text, source_lang, target_lang)
            
            if uncached_translation:
                uncached_word_translations = uncached_translation.split()
                
                for i, word in enumerate(uncached_words):
                    if i < len(uncached_word_translations):
                        self.save_word_to_cache(word, source_lang, target_lang, uncached_word_translations[i])
                        cached_words[word] = uncached_word_translations[i]
                
                return self.reconstruct_translation_from_words(text, cached_words)
        
        return None
    
    def translate_uncached_words(self, text, source_lang, target_lang):
        try:
            prompt = f"Переведи эти слова с {self.get_language_name(source_lang)} на {self.get_language_name(target_lang)}, выведи только переводы через пробел: {text}"
            
            response = g4f.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                timeout=15
            )
            
            return response.strip() if response else None
        except:
            return None
    
    def reconstruct_translation_from_words(self, original_text, word_translations):
        result = original_text.lower()
        
        for word in word_translations:
            if word in word_translations:
                pattern = r'\b' + re.escape(word) + r'\b'
                result = re.sub(pattern, word_translations[word], result)
        
        return result
    
    def detect_language(self, text):
        cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        chinese_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        arabic_count = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
        
        if cyrillic_count > len(text) * 0.3:
            return 'ru'
        elif chinese_count > 0:
            return 'zh'
        elif arabic_count > len(text) * 0.3:
            return 'ar'
        elif any(char in text for char in ['ä', 'ö', 'ü', 'ß']):
            return 'de'
        elif any(word in text.lower() for word in ['the', 'and', 'is', 'are', 'you', 'this']):
            return 'en'
        elif any(word in text.lower() for word in ['le', 'la', 'et', 'est', 'une', 'des']):
            return 'fr'
        elif any(word in text.lower() for word in ['el', 'la', 'y', 'es', 'una', 'los']):
            return 'es'
        else:
            return 'en'
    
    def get_language_name(self, lang_code):
        return self.languages.get(lang_code, lang_code.upper())
    
    def create_translation_prompt(self, text, source_lang, target_lang):
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        
        return f"""Ты профессиональный переводчик с многолетним опытом. Твоя задача - сделать точный и естественный перевод.

ИСХОДНЫЙ ЯЗЫК: {source_name}
ЦЕЛЕВОЙ ЯЗЫК: {target_name}
ТЕКСТ ДЛЯ ПЕРЕВОДА: "{text}"

ТРЕБОВАНИЯ:
- Перевод должен быть максимально точным и естественным
- Сохрани стиль и тон оригинального текста
- Учти культурные особенности целевого языка
- Переведи идиомы и фразеологизмы адекватно
- Соблюди грамматические правила целевого языка

ВЫВЕДИ ТОЛЬКО ФИНАЛЬНЫЙ ПЕРЕВОД БЕЗ КОММЕНТАРИЕВ!

ПЕРЕВОД:"""
    
    def try_model(self, model, messages, timeout=20):
        try:
            response = g4f.ChatCompletion.create(
                model=model,
                messages=messages,
                timeout=timeout
            )
            return response.strip() if response and response.strip() else None
        except Exception as e:
            print(f"Ошибка модели {model}: {str(e)}")
            return None
    
    def translate(self, text, source_lang='auto', target_lang='en'):
        if not text or not text.strip():
            return "Пустой текст"
        
        if source_lang == 'auto':
            source_lang = self.detect_language(text)
        
        cached = self.get_from_cache(text, source_lang, target_lang)
        if cached:
            print("Found in full cache!")
            return cached
        
        smart_translation = self.smart_translate_with_word_cache(text, source_lang, target_lang)
        if smart_translation:
            print("Used word cache!")
            self.save_to_cache(text, source_lang, target_lang, smart_translation)
            return smart_translation
        
        print("Full AI translation...")
        prompt = self.create_translation_prompt(text, source_lang, target_lang)
        messages = [{"role": "user", "content": prompt}]
        
        models = ["gpt-4", "gpt-3.5-turbo", "gpt-4o-mini"]
        
        futures = []
        for model in models[:2]:
            future = self.executor.submit(self.try_model, model, messages)
            futures.append((future, model))
        
        for future, model in futures:
            try:
                result = future.result(timeout=25)
                if result and len(result) > 3:
                    result = self.clean_translation(result)
                    self.save_to_cache(text, source_lang, target_lang, result)
                    
                    self.cache_words_from_translation(text, result, source_lang, target_lang)
                    
                    return result
            except Exception as e:
                print(f"Ошибка при получении результата от {model}: {str(e)}")
                continue
        
        try:
            simple_prompt = f"Переведи с {self.get_language_name(source_lang)} на {self.get_language_name(target_lang)}: {text}"
            response = g4f.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": simple_prompt}],
                timeout=30
            )
            
            if response:
                result = self.clean_translation(response.strip())
                self.save_to_cache(text, source_lang, target_lang, result)
                
                self.cache_words_from_translation(text, result, source_lang, target_lang)
                
                return result
            else:
                return "Не удалось получить перевод"
                
        except Exception as e:
            return f"Ошибка перевода: {str(e)}"
    
    def cache_words_from_translation(self, original_text, translation, source_lang, target_lang):
        original_words = self.extract_words(original_text)
        translated_words = self.extract_words(translation)
        
        min_len = min(len(original_words), len(translated_words))
        for i in range(min_len):
            self.save_word_to_cache(original_words[i], source_lang, target_lang, translated_words[i])
        
        print(f"Cached {min_len} word pairs")
    
    def clean_translation(self, translation):
        prefixes = [
            "ПЕРЕВОД:", "Перевод:", "Translation:", "TRANSLATION:",
            "Результат:", "РЕЗУЛЬТАТ:", "Ответ:", "ОТВЕТ:"
        ]
        
        for prefix in prefixes:
            if translation.startswith(prefix):
                translation = translation[len(prefix):].strip()
        
        if translation.startswith('"') and translation.endswith('"'):
            translation = translation[1:-1]
        
        return translation.strip()

translator = UniversalTranslator()

@app.route('/')
def index():
    return render_template('index.html', languages=translator.languages)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        
        text = data.get('text', '').strip()
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'en')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Пустой текст'
            })
        
        if len(text) > 5000:
            return jsonify({
                'success': False,
                'error': 'Текст слишком длинный (максимум 5000 символов)'
            })
        
        translation = translator.translate(text, source_lang, target_lang)
        
        if source_lang == 'auto':
            detected_lang = translator.detect_language(text)
        else:
            detected_lang = source_lang
        
        return jsonify({
            'success': True,
            'translation': translation,
            'detected_language': detected_lang,
            'source_language_name': translator.get_language_name(detected_lang),
            'target_language_name': translator.get_language_name(target_lang)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка сервера: {str(e)}'
        })

@app.route('/languages')
def get_languages():
    return jsonify(translator.languages)

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'cache_size': len(translator.cache),
        'word_cache_size': len(translator.word_cache),
        'supported_languages': len(translator.languages),
        'total_cached_items': len(translator.cache) + len(translator.word_cache)
    })

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    if not os.path.exists('static'):
        os.makedirs('static')

    print(f"languages: {len(translator.languages)}")
    print("http://localhost:5000")
    webbrowser.open("http://localhost:5000", new=2)
    
    app.run(host='0.0.0.0', port=5000, debug=True)