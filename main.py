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
import time
from collections import defaultdict
import atexit

app = Flask(__name__)

class OptimizedUniversalTranslator:
    def __init__(self):
        self.cache_file = 'translation_cache.json'
        self.word_cache_file = 'word_cache.json'

        self.cache = {}
        self.word_cache = {}
        self.cache_dirty = False
        self.word_cache_dirty = False

        self._load_initial_cache()

        self.pending_words = defaultdict(list)
        self.batch_lock = threading.Lock()
        self.batch_timer = None
        self.batch_delay = 0.3 
        
        self.cache_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=3)  
        self.languages = self._load_languages()

        self._setup_cache_autosave()

        atexit.register(self._save_all_cache)
        
    def _load_initial_cache(self):
        self.cache = self._load_cache_from_disk(self.cache_file)
        self.word_cache = self._load_cache_from_disk(self.word_cache_file)
        print(f" * Загружен кэш: {len(self.cache)} переводов, {len(self.word_cache)} слов")
        
    def _load_cache_from_disk(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки кэша {filename}: {e}")
                return {}
        return {}

    def _setup_cache_autosave(self):
        def autosave():
            while True:
                time.sleep(120)  # 2М
                if self.cache_dirty or self.word_cache_dirty:
                    self._save_cache_to_disk()
                    
        autosave_thread = threading.Thread(target=autosave, daemon=True)
        autosave_thread.start()
        
    def _save_cache_to_disk(self):
        try:
            if self.cache_dirty:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=2)
                self.cache_dirty = False
                
            if self.word_cache_dirty:
                with open(self.word_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.word_cache, f, ensure_ascii=False, indent=2)
                self.word_cache_dirty = False
                
            print(" * Кэш сохранен")
        except Exception as e:
            print(f" * Ошибка сохранения кэша: {e}")
            
    def _save_all_cache(self):
        self.cache_dirty = True
        self.word_cache_dirty = True
        self._save_cache_to_disk()

    def _load_languages(self):
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

    def _get_cache_key(self, text, source_lang, target_lang):
        text_hash = hashlib.md5(text.strip().lower().encode()).hexdigest()[:16]  
        return f"{source_lang}_{target_lang}:{text_hash}"
    
    def _get_word_cache_key(self, word, source_lang, target_lang):
        word_hash = hashlib.md5(word.strip().lower().encode()).hexdigest()[:16]
        return f"w_{source_lang}_{target_lang}:{word_hash}"
    
    def _get_from_cache(self, text, source_lang, target_lang):
        key = self._get_cache_key(text, source_lang, target_lang)
        return self.cache.get(key)
    
    def _save_to_cache(self, text, source_lang, target_lang, translation):
        key = self._get_cache_key(text, source_lang, target_lang)
        with self.cache_lock:
            self.cache[key] = translation
            self.cache_dirty = True
    
    def _get_word_from_cache(self, word, source_lang, target_lang):
        key = self._get_word_cache_key(word, source_lang, target_lang)
        return self.word_cache.get(key)
    
    def _save_word_to_cache(self, word, source_lang, target_lang, translation):
        key = self._get_word_cache_key(word, source_lang, target_lang)
        with self.cache_lock:
            self.word_cache[key] = translation
            self.word_cache_dirty = True
    
    def _extract_words(self, text):
        words = []
        word = ""
        for char in text.lower():
            if char.isalnum():
                word += char
            else:
                if word:
                    words.append(word)
                    word = ""
        if word:
            words.append(word)
        return words
    
    def _batch_translate_words(self, lang_pair):
        source_lang, target_lang = lang_pair
        
        with self.batch_lock:
            words_to_translate = self.pending_words[lang_pair].copy()
            self.pending_words[lang_pair].clear()
            
        if not words_to_translate:
            return
            
        print(f" * Batch перевод {len(words_to_translate)} слов: {source_lang}->{target_lang}")
        
        uncached_words = []
        for word in words_to_translate:
            if not self._get_word_from_cache(word, source_lang, target_lang):
                uncached_words.append(word)
        
        if not uncached_words:
            return
            
        words_text = " ".join(uncached_words[:50]) 
        
        try:
            prompt = f"Переведи эти слова с {self._get_language_name(source_lang)} на {self._get_language_name(target_lang)}. Выведи только переводы через пробел: {words_text}"
            
            response = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo",  
                messages=[{"role": "user", "content": prompt}],
                timeout=10 
            )
            
            if response:
                translated_words = response.strip().split()

                for i, word in enumerate(uncached_words):
                    if i < len(translated_words):
                        self._save_word_to_cache(word, source_lang, target_lang, translated_words[i])
                        
                print(f" * Сохранено {min(len(uncached_words), len(translated_words))} переводов слов")
                
        except Exception as e:
            print(f" * Ошибка batch перевода: {e}")
    
    def _schedule_batch_translation(self, words, source_lang, target_lang):
        lang_pair = (source_lang, target_lang)
        
        with self.batch_lock:
            self.pending_words[lang_pair].extend(words)
            
            if self.batch_timer:
                self.batch_timer.cancel()
            
            self.batch_timer = threading.Timer(
                self.batch_delay, 
                self._batch_translate_words, 
                args=[lang_pair]
            )
            self.batch_timer.start()
    
    def _smart_translate_with_word_cache(self, text, source_lang, target_lang):
        words = self._extract_words(text)
        unique_words = list(set(words))
        
        cached_words = {}
        uncached_words = []

        for word in unique_words:
            cached_translation = self._get_word_from_cache(word, source_lang, target_lang)
            if cached_translation:
                cached_words[word] = cached_translation
            else:
                uncached_words.append(word)
        
        cache_ratio = len(cached_words) / len(unique_words) if unique_words else 0
        print(f" * Слов в кэше: {len(cached_words)}/{len(unique_words)} ({cache_ratio:.1%})")
        
        if uncached_words:
            self._schedule_batch_translation(uncached_words, source_lang, target_lang)

        if cache_ratio >= 0.6:  
            return self._reconstruct_from_cache(text.lower(), cached_words)
        
        return None
    
    def _reconstruct_from_cache(self, text, word_translations):
        result = text
        for word, translation in word_translations.items():
            result = result.replace(word, translation)
        return result
    
    def detect_language(self, text):
        text_lower = text.lower()
        
        if any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in text[:100]): 
            return 'ru'
        elif any(ord(c) >= 0x4e00 and ord(c) <= 0x9fff for c in text[:100]):
            return 'zh'
        elif any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in text[:100]):
            return 'ar'
        elif any(char in text_lower for char in ['ä', 'ö', 'ü', 'ß']):
            return 'de'
        elif ' the ' in text_lower or ' and ' in text_lower or text_lower.startswith('the '):
            return 'en'
        elif ' le ' in text_lower or ' la ' in text_lower or ' et ' in text_lower:
            return 'fr'
        elif ' el ' in text_lower or ' la ' in text_lower or ' es ' in text_lower:
            return 'es'
        else:
            return 'en'
    
    def _get_language_name(self, lang_code):
        return self.languages.get(lang_code, lang_code.upper())
    
    def _create_optimized_prompt(self, text, source_lang, target_lang):
        return f"Переведи с {self._get_language_name(source_lang)} на {self._get_language_name(target_lang)}: {text}"
    
    def _try_fast_model(self, text, source_lang, target_lang):
        try:
            prompt = self._create_optimized_prompt(text, source_lang, target_lang)
            
            response = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo",  
                messages=[{"role": "user", "content": prompt}],
                timeout=8 
            )
            
            return self._clean_translation(response.strip()) if response else None
            
        except Exception as e:
            print(f" * Быстрая модель не сработала: {e}")
            return None
    
    def translate(self, text, source_lang='auto', target_lang='en'):
        if not text or not text.strip():
            return "Пустой текст"
        
        text = text.strip()
        
        if source_lang == 'auto':
            source_lang = self.detect_language(text)
        
        cached = self._get_from_cache(text, source_lang, target_lang)
        if cached:
            print(" *  Найден в полном кэше!")
            return cached
        
        smart_translation = self._smart_translate_with_word_cache(text, source_lang, target_lang)
        if smart_translation:
            print(" * Собран из кэша слов")
            self._save_to_cache(text, source_lang, target_lang, smart_translation)
            return smart_translation
        

        
        translation = self._try_fast_model(text, source_lang, target_lang)
        
        if not translation and len(text) < 1000:
            try:
                response = g4f.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": f"Переведи: {text}"}],
                    timeout=15
                )
                translation = self._clean_translation(response.strip()) if response else None
            except:
                pass
        
        if translation:
            self._save_to_cache(text, source_lang, target_lang, translation)
            self._cache_words_from_translation(text, translation, source_lang, target_lang)
            return translation
        
        return "Не удалось получить перевод"
    
    def _cache_words_from_translation(self, original_text, translation, source_lang, target_lang):
        original_words = self._extract_words(original_text)
        translated_words = self._extract_words(translation)
        
        min_len = min(len(original_words), len(translated_words))
        cached_count = 0
        
        for i in range(min_len):
            if len(original_words[i]) > 2 and len(translated_words[i]) > 1:  # Только значимые слова
                self._save_word_to_cache(original_words[i], source_lang, target_lang, translated_words[i])
                cached_count += 1
        
        if cached_count > 0:
            print(f" * Закэшировано {cached_count} пар слов")
    
    def _clean_translation(self, translation):
        prefixes = ["перевод:", "translation:", "результат:", "ответ:"]
        translation_lower = translation.lower()
        
        for prefix in prefixes:
            if translation_lower.startswith(prefix):
                translation = translation[len(prefix):].strip()
                break
        
        if translation.startswith('"') and translation.endswith('"'):
            translation = translation[1:-1]
        
        return translation.strip()

translator = OptimizedUniversalTranslator()

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
        
        start_time = time.time()
        translation = translator.translate(text, source_lang, target_lang)
        end_time = time.time()
        
        if source_lang == 'auto':
            detected_lang = translator.detect_language(text)
        else:
            detected_lang = source_lang
        
        return jsonify({
            'success': True,
            'translation': translation,
            'detected_language': detected_lang,
            'source_language_name': translator._get_language_name(detected_lang),
            'target_language_name': translator._get_language_name(target_lang),
            'processing_time': f"{(end_time - start_time):.2f}s"  # Время обработки для отладки
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
        'total_cached_items': len(translator.cache) + len(translator.word_cache),
        'pending_batches': len(translator.pending_words)
    })

@app.route('/cache-stats')
def cache_stats():
    return jsonify({
        'full_cache_size': len(translator.cache),
        'word_cache_size': len(translator.word_cache), #
        'cache_dirty': translator.cache_dirty,
        'word_cache_dirty': translator.word_cache_dirty,
        'pending_word_batches': {str(k): len(v) for k, v in translator.pending_words.items()}
    })

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    if not os.path.exists('static'):
        os.makedirs('static')

    os.system("cls")
    print(f" * Languages: {len(translator.languages)}")
    print(" * Website url: http://localhost:5000")
    
    webbrowser.open("http://localhost:5000", new=1)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
