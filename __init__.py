import argostranslate.package
import argostranslate.translate
import traceback
import os
import threading
from pathlib import Path

class ArgosTranslateManager:
    """Gestore per le operazioni di traduzione con Argos Translate"""
    
    # Mappa completa delle lingue supportate con i loro nomi completi
    LANGUAGE_MAP = {
        "auto": "Auto-detect",
        "en": "English",
        "ar": "Arabic (العربية)",
        "az": "Azerbaijani (Azərbaycan)",
        "ca": "Catalan (Català)",
        "zh": "Chinese (中文)",
        "cs": "Czech (Čeština)",
        "da": "Danish (Dansk)",
        "nl": "Dutch (Nederlands)",
        "eo": "Esperanto",
        "fi": "Finnish (Suomi)",
        "fr": "French (Français)",
        "de": "German (Deutsch)",
        "el": "Greek (Ελληνικά)",
        "he": "Hebrew (עברית)",
        "hi": "Hindi (हिन्दी)",
        "hu": "Hungarian (Magyar)",
        "id": "Indonesian (Bahasa Indonesia)",
        "ga": "Irish (Gaeilge)",
        "it": "Italian (Italiano)",
        "ja": "Japanese (日本語)",
        "ko": "Korean (한국어)",
        "lv": "Latvian (Latviešu)",
        "lt": "Lithuanian (Lietuvių)",
        "ms": "Malay (Bahasa Melayu)",
        "no": "Norwegian (Norsk)",
        "fa": "Persian (فارسی)",
        "pl": "Polish (Polski)",
        "pt": "Portuguese (Português)",
        "ro": "Romanian (Română)",
        "ru": "Russian (Русский)",
        "sk": "Slovak (Slovenčina)",
        "sl": "Slovenian (Slovenščina)",
        "es": "Spanish (Español)",
        "sv": "Swedish (Svenska)",
        "th": "Thai (ไทย)",
        "tr": "Turkish (Türkçe)",
        "uk": "Ukrainian (Українська)",
        "vi": "Vietnamese (Tiếng Việt)",
    }
    
    # Lock per thread safety durante il download
    _download_lock = threading.Lock()
    _downloading = set()
    
    @classmethod
    def get_language_list(cls):
        """Restituisce la lista delle lingue per il menu dropdown con nomi completi"""
        return [f"{code} - {name}" for code, name in cls.LANGUAGE_MAP.items()]
    
    @classmethod
    def get_language_code_from_display(cls, display_name):
        """Estrae il codice lingua dal nome visualizzato"""
        if " - " in display_name:
            return display_name.split(" - ")[0]
        return display_name
    
    @classmethod
    def get_language_display_names(cls):
        """Restituisce la lista dei nomi visualizzati delle lingue"""
        return [f"{code}: {name}" for code, name in cls.LANGUAGE_MAP.items()]
    
    @classmethod
    def simple_language_detect(cls, text):
        """Semplice rilevamento della lingua basato su caratteri comuni"""
        if not text or len(text.strip()) < 3:
            return "en"
        
        text_lower = text.lower()
        
        # Controllo per cirillico (russo, ucraino)
        if any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in text):
            if any(word in text_lower for word in ["що", "але", "або", "який", "яка", "яке"]):
                return "uk"  # Ucraino
            return "ru"  # Russo
        
        # Controllo per caratteri cinesi/giapponesi/coreani
        if any(ord(char) >= 0x4E00 and ord(char) <= 0x9FFF for char in text):
            return "zh"  # Cinese
        
        if any(ord(char) >= 0x3040 and ord(char) <= 0x309F for char in text):
            return "ja"  # Hiragana giapponese
        
        if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7AF for char in text):
            return "ko"  # Coreano
        
        # Controllo per arabo
        if any(ord(char) >= 0x0600 and ord(char) <= 0x06FF for char in text):
            return "ar"
        
        # Controllo per ebraico
        if any(ord(char) >= 0x0590 and ord(char) <= 0x05FF for char in text):
            return "he"
        
        # Controllo per greco
        if any(ord(char) >= 0x0370 and ord(char) <= 0x03FF for char in text):
            return "el"
        
        # Controllo per thai
        if any(ord(char) >= 0x0E00 and ord(char) <= 0x0E7F for char in text):
            return "th"
        
        # Controlli per lingue europee con caratteri speciali
        if any(char in text for char in "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"):
            if any(word in text_lower for word in ["il", "la", "le", "di", "da", "in", "con", "per", "che", "non", "una", "uno"]):
                return "it"  # Italiano
            elif any(word in text_lower for word in ["el", "la", "los", "las", "de", "del", "en", "con", "por", "que", "no", "es", "un", "una"]):
                return "es"  # Spagnolo
            elif any(word in text_lower for word in ["le", "la", "les", "de", "du", "des", "en", "dans", "avec", "pour", "que", "ne", "un", "une"]):
                return "fr"  # Francese
            elif any(word in text_lower for word in ["der", "die", "das", "den", "dem", "des", "ein", "eine", "und", "oder", "nicht", "ist"]):
                return "de"  # Tedesco
            elif any(word in text_lower for word in ["o", "a", "os", "as", "de", "do", "da", "em", "com", "por", "que", "não", "um", "uma"]):
                return "pt"  # Portoghese
        
        # Controlli per lingue nordiche
        if any(word in text_lower for word in ["och", "att", "är", "den", "det", "en", "ett", "för", "på", "av"]):
            return "sv"  # Svedese
        
        if any(word in text_lower for word in ["og", "at", "er", "den", "det", "en", "et", "for", "på", "av"]):
            return "no"  # Norvegese
        
        if any(word in text_lower for word in ["og", "at", "er", "den", "det", "en", "et", "for", "på", "af"]):
            return "da"  # Danese
        
        # Default inglese
        return "en"
    
    @classmethod
    def ensure_translation_package(cls, source_lang, target_lang):
        """Assicura che il pacchetto di traduzione sia installato, scaricandolo se necessario"""
        if source_lang == "auto":
            return True  # Non possiamo pre-scaricare per auto-detect
        
        if source_lang == target_lang:
            return True  # Non serve traduzione
        
        package_key = f"{source_lang}-{target_lang}"
        
        # Evita download multipli simultanei dello stesso pacchetto
        with cls._download_lock:
            if package_key in cls._downloading:
                print(f"Package {package_key} is already being downloaded, waiting...")
                return False
            
            try:
                # Controlla se il pacchetto è già installato
                installed_languages = argostranslate.translate.get_installed_languages()
                source_language = next((lang for lang in installed_languages if lang.code == source_lang), None)
                target_language = next((lang for lang in installed_languages if lang.code == target_lang), None)
                
                if source_language and target_language:
                    translation = source_language.get_translation(target_language)
                    if translation:
                        return True  # Pacchetto già installato e funzionante
                
                # Aggiorna l'indice dei pacchetti
                print(f"Updating package index...")
                argostranslate.package.update_package_index()
                
                # Ottieni i pacchetti disponibili
                available_packages = argostranslate.package.get_available_packages()
                
                # Trova il pacchetto per la traduzione richiesta
                target_package = next(
                    (pkg for pkg in available_packages 
                     if pkg.from_code == source_lang and pkg.to_code == target_lang),
                    None
                )
                
                if target_package is None:
                    print(f"No translation package available from '{source_lang}' to '{target_lang}'")
                    return False
                
                if target_package.is_installed():
                    print(f"Package {source_lang}->{target_lang} is already installed")
                    return True
                
                # Marca come in download
                cls._downloading.add(package_key)
                
                # Scarica e installa il pacchetto
                print(f"Downloading translation package: {source_lang} -> {target_lang}")
                print(f"Package size: ~{target_package.size // 1024 // 1024}MB (this may take a while...)")
                
                download_path = target_package.download()
                argostranslate.package.install_from_path(download_path)
                
                print(f"Successfully installed package: {source_lang} -> {target_lang}")
                return True
                
            except Exception as e:
                print(f"Error downloading package {source_lang}->{target_lang}: {e}")
                traceback.print_exc()
                return False
            finally:
                # Rimuovi dalla lista dei download in corso
                cls._downloading.discard(package_key)
    
    @classmethod
    def translate_text(cls, text, source_lang="auto - Auto-detect", target_lang="en - English"):
        """Traduce il testo usando Argos Translate, scaricando i pacchetti se necessario"""
        if not text or not text.strip():
            return text
        
        try:
            # Estrai i codici lingua dai nomi visualizzati
            source_code = cls.get_language_code_from_display(source_lang)
            target_code = cls.get_language_code_from_display(target_lang)
            
            # Auto-rilevamento se necessario
            if source_code == "auto":
                detected_lang = cls.simple_language_detect(text)
                print(f"Auto-detected language: {detected_lang} ({cls.LANGUAGE_MAP.get(detected_lang, 'Unknown')})")
                source_code = detected_lang
            
            # Se è già nella lingua target, restituisci il testo originale
            if source_code == target_code:
                print(f"Text is already in target language ({target_code})")
                return text
            
            # Assicura che il pacchetto di traduzione sia installato
            if not cls.ensure_translation_package(source_code, target_code):
                print(f"Could not ensure translation package for {source_code}->{target_code}")
                return text
            
            # Ottieni le lingue installate (refresh dopo possibile download)
            installed_languages = argostranslate.translate.get_installed_languages()
            
            # Trova le lingue sorgente e target
            source_language = next((lang for lang in installed_languages if lang.code == source_code), None)
            target_language = next((lang for lang in installed_languages if lang.code == target_code), None)
            
            if source_language is None:
                print(f"Source language '{source_code}' not available after package check")
                return text
            
            if target_language is None:
                print(f"Target language '{target_code}' not available after package check")
                return text
            
            # Ottieni la traduzione
            translation = source_language.get_translation(target_language)
            
            if translation is None:
                print(f"No translation model available from '{source_code}' to '{target_code}'")
                return text
            
            # Esegui la traduzione
            translated_text = translation.translate(text)
            print(f"Translated ({source_code}->{target_code}): {text[:50]}{'...' if len(text) > 50 else ''}")
            
            return translated_text
            
        except Exception as e:
            print(f"Translation error: {e}")
            traceback.print_exc()
            return text

# NODI ORIGINALI
class AT_CLIPTextTranslate:
    @classmethod
    def INPUT_TYPES(s):
        language_list = ArgosTranslateManager.get_language_list()
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True}),
                "clip": ("CLIP", ),
                "source_language": (language_list, {"default": "auto - Auto-detect"}),
                "target_language": (language_list, {"default": "en - English"})
            }
        }
    
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "encode"
    CATEGORY = "🌐 DrStone71"
    
    def encode(self, clip, text, source_language="auto - Auto-detect", target_language="en - English"):
        if text.strip():
            text = ArgosTranslateManager.translate_text(text, source_language, target_language)
        
        tokens = clip.tokenize(text)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        return ([[cond, {"pooled_output": pooled}]], )

class AT_PromptTextTranslate:
    @classmethod
    def INPUT_TYPES(s):
        language_list = ArgosTranslateManager.get_language_list()
        return {
            "required": {
                "prompt": ("STRING", {"default": "prompt", "multiline": True}),
                "source_language": (language_list, {"default": "auto - Auto-detect"}),
                "target_language": (language_list, {"default": "en - English"})
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "get_value"
    CATEGORY = "🌐 DrStone71"
    
    def get_value(self, prompt, source_language="auto - Auto-detect", target_language="en - English"):
        if prompt.strip():
            prompt = ArgosTranslateManager.translate_text(prompt, source_language, target_language)
        return (prompt,)

class AT_TextTranslate:
    """Nodo dedicato solo alla traduzione di testo"""
    @classmethod
    def INPUT_TYPES(s):
        language_list = ArgosTranslateManager.get_language_list()
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True}),
                "source_language": (language_list, {"default": "auto - Auto-detect"}),
                "target_language": (language_list, {"default": "en - English"})
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_text",)
    FUNCTION = "translate"
    CATEGORY = "🌐 DrStone71"
    
    def translate(self, text, source_language="auto - Auto-detect", target_language="en - English"):
        translated_text = ArgosTranslateManager.translate_text(text, source_language, target_language)
        return (translated_text,)

class AT_LanguagePackageManager:
    """Nodo per gestire i pacchetti di lingua"""
    @classmethod
    def INPUT_TYPES(s):
        language_list = ArgosTranslateManager.get_language_list()
        # Rimuovi 'auto' dalla lista per questo nodo
        language_list_no_auto = [lang for lang in language_list if not lang.startswith("auto")]
        return {
            "required": {
                "source_language": (language_list_no_auto, {"default": "it - Italian (Italiano)"}),
                "target_language": (language_list_no_auto, {"default": "en - English"}),
                "action": (["check", "install"], {"default": "check"})
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "manage_package"
    CATEGORY = "🌐 DrStone71"
    
    def manage_package(self, source_language, target_language, action="check"):
        try:
            # Estrai i codici lingua dai nomi visualizzati
            source_code = ArgosTranslateManager.get_language_code_from_display(source_language)
            target_code = ArgosTranslateManager.get_language_code_from_display(target_language)
            
            if action == "check":
                # Controlla se il pacchetto è installato
                installed_languages = argostranslate.translate.get_installed_languages()
                source_lang = next((lang for lang in installed_languages if lang.code == source_code), None)
                target_lang = next((lang for lang in installed_languages if lang.code == target_code), None)
                
                if source_lang and target_lang:
                    translation = source_lang.get_translation(target_lang)
                    if translation:
                        return (f"Package {source_code}->{target_code} is installed and ready",)
                    else:
                        return (f"Languages available but no translation model for {source_code}->{target_code}",)
                else:
                    return (f"Package {source_code}->{target_code} is NOT installed",)
            
            elif action == "install":
                # Installa il pacchetto
                success = ArgosTranslateManager.ensure_translation_package(source_code, target_code)
                if success:
                    return (f"Successfully installed package {source_code}->{target_code}",)
                else:
                    return (f"Failed to install package {source_code}->{target_code}",)
            
        except Exception as e:
            return (f"Error: {str(e)}",)

# NODI AVANZATI
class AT_UniversalTextTranslate:
    """Nodo universale per traduzione che supporta sia output di testo che conditioning"""
    
    @classmethod
    def INPUT_TYPES(s):
        language_list = ArgosTranslateManager.get_language_list()
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True}),
                "source_language": (language_list, {"default": "auto - Auto-detect"}),
                "target_language": (language_list, {"default": "en - English"}),
                "output_type": (["text_only", "conditioning_only", "both"], {"default": "both"})
            },
            "optional": {
                "clip": ("CLIP",),  # Optional per permettere conditioning
            }
        }
    
    RETURN_TYPES = ("STRING", "CONDITIONING")
    RETURN_NAMES = ("translated_text", "conditioning")
    FUNCTION = "translate_and_encode"
    CATEGORY = "🌐 DrStone71"
    
    def translate_and_encode(self, text, source_language="auto - Auto-detect", 
                           target_language="en - English", output_type="both", clip=None):
        
        # Traduci il testo
        translated_text = ""
        if text.strip():
            translated_text = ArgosTranslateManager.translate_text(text, source_language, target_language)
        else:
            translated_text = text
        
        # Prepara gli output
        conditioning_output = None
        
        if output_type in ["conditioning_only", "both"] and clip is not None:
            # Genera conditioning solo se CLIP è fornito
            tokens = clip.tokenize(translated_text)
            cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
            conditioning_output = [[cond, {"pooled_output": pooled}]]
        
        # Restituisci sempre entrambi gli output, anche se uno è None
        return (translated_text, conditioning_output)

class AT_CLIPTextTranslateAdvanced:
    """Versione avanzata del nodo CLIP con più opzioni"""
    
    @classmethod
    def INPUT_TYPES(s):
        language_list = ArgosTranslateManager.get_language_list()
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True}),
                "clip": ("CLIP",),
                "source_language": (language_list, {"default": "auto - Auto-detect"}),
                "target_language": (language_list, {"default": "en - English"}),
            },
            "optional": {
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1}),
                "pass_through_original": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("CONDITIONING", "STRING")
    RETURN_NAMES = ("conditioning", "translated_text")
    FUNCTION = "encode"
    CATEGORY = "🌐 DrStone71"
    
    def encode(self, clip, text, source_language="auto - Auto-detect", 
               target_language="en - English", strength=1.0, pass_through_original=False):
        
        original_text = text
        translated_text = text
        
        if text.strip():
            translated_text = ArgosTranslateManager.translate_text(text, source_language, target_language)
        
        # Se pass_through_original è True, usa il testo originale per l'encoding
        final_text = original_text if pass_through_original else translated_text
        
        tokens = clip.tokenize(final_text)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        
        # Applica strength se diverso da 1.0
        if strength != 1.0:
            cond = cond * strength
        
        conditioning = [[cond, {"pooled_output": pooled}]]
        
        return (conditioning, translated_text)

class AT_CombineConditioning:
    """Combina conditioning da testi in lingue diverse"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "conditioning_1": ("CONDITIONING",),
                "conditioning_2": ("CONDITIONING",),
                "method": (["average", "weighted", "concatenate"], {"default": "weighted"}),
                "weight_1": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.1}),
                "weight_2": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.1}),
            }
        }
    
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "combine"
    CATEGORY = "🌐 DrStone71"
    
    def combine(self, conditioning_1, conditioning_2, method="weighted", weight_1=0.7, weight_2=0.3):
        import torch
        
        # Estrai i tensori conditioning
        cond_1 = conditioning_1[0][0]
        pooled_1 = conditioning_1[0][1].get("pooled_output", None)
        
        cond_2 = conditioning_2[0][0]
        pooled_2 = conditioning_2[0][1].get("pooled_output", None)
        
        if method == "average":
            combined_cond = (cond_1 + cond_2) / 2
            combined_pooled = (pooled_1 + pooled_2) / 2 if pooled_1 is not None and pooled_2 is not None else None
            
        elif method == "weighted":
            # Normalizza i pesi
            total_weight = weight_1 + weight_2
            w1 = weight_1 / total_weight
            w2 = weight_2 / total_weight
            
            combined_cond = cond_1 * w1 + cond_2 * w2
            combined_pooled = (pooled_1 * w1 + pooled_2 * w2) if pooled_1 is not None and pooled_2 is not None else None
            
        elif method == "concatenate":
            combined_cond = torch.cat([cond_1, cond_2], dim=1)  # Concatena lungo la dimensione dei token
            combined_pooled = (pooled_1 + pooled_2) / 2 if pooled_1 is not None and pooled_2 is not None else None
        
        result = {"pooled_output": combined_pooled} if combined_pooled is not None else {}
        
        return ([[combined_cond, result]],)

class AT_ConditionalTranslate:
    """Traduce solo se la lingua rilevata è diversa dal target"""
    
    @classmethod
    def INPUT_TYPES(s):
        language_list = ArgosTranslateManager.get_language_list()
        # Rimuovi auto-detect per questo nodo
        language_list_no_auto = [lang for lang in language_list if not lang.startswith("auto")]
        
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True}),
                "clip": ("CLIP",),
                "target_language": (language_list_no_auto, {"default": "en - English"}),
                "always_translate": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("CONDITIONING", "STRING", "STRING")
    RETURN_NAMES = ("conditioning", "final_text", "detected_language")
    FUNCTION = "conditional_translate"
    CATEGORY = "🌐 DrStone71"
    
    def conditional_translate(self, text, clip, target_language="en - English", always_translate=False):
        if not text.strip():
            tokens = clip.tokenize(text)
            cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
            return ([[cond, {"pooled_output": pooled}]], text, "unknown")
        
        # Rileva la lingua
        detected_lang = ArgosTranslateManager.simple_language_detect(text)
        target_code = ArgosTranslateManager.get_language_code_from_display(target_language)
        
        final_text = text
        
        # Traduci solo se necessario
        if always_translate or detected_lang != target_code:
            final_text = ArgosTranslateManager.translate_text(
                text, f"{detected_lang} - {ArgosTranslateManager.LANGUAGE_MAP.get(detected_lang, 'Unknown')}", 
                target_language
            )
        
        # Genera conditioning
        tokens = clip.tokenize(final_text)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        conditioning = [[cond, {"pooled_output": pooled}]]
        
        detected_display = f"{detected_lang} - {ArgosTranslateManager.LANGUAGE_MAP.get(detected_lang, 'Unknown')}"
        
        return (conditioning, final_text, detected_display)

# Mappatura completa dei nodi
NODE_CLASS_MAPPINGS = {
    # Nodi originali
    "CLIP Text Encode (Translate)": AT_CLIPTextTranslate,
    "Prompt Text (Translate)": AT_PromptTextTranslate,
    "Text Translate": AT_TextTranslate,
    "Language Package Manager": AT_LanguagePackageManager,
    
    # Nodi avanzati
    "Universal Text Translate": AT_UniversalTextTranslate,
    "CLIP Text Translate Advanced": AT_CLIPTextTranslateAdvanced,
    "Combine Conditioning": AT_CombineConditioning,
    "Conditional Translate": AT_ConditionalTranslate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    # Nodi originali
    "AT_CLIPTextTranslate": "CLIP Text Encode (Translate)",
    "AT_PromptTextTranslate": "Prompt Text (Translate)",
    "AT_TextTranslate": "Text Translate",
    "AT_LanguagePackageManager": "Language Package Manager",
    
    # Nodi avanzati
    "AT_UniversalTextTranslate": "Universal Text Translate",
    "AT_CLIPTextTranslateAdvanced": "CLIP Text Translate Advanced", 
    "AT_CombineConditioning": "Combine Conditioning",
    "AT_ConditionalTranslate": "Conditional Translate",
}
