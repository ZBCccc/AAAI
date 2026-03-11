import logging
import requests
import base64
import os
from typing import Dict, Optional
from volcenginesdkarkruntime import Ark

logger = logging.getLogger("LLMManager")

# 文件扩展名到MIME类型的映射
IMAGE_MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
}

def _get_image_mime_type(image_path: str) -> str:
    """根据文件扩展名获取MIME类型"""
    ext = os.path.splitext(image_path)[1].lower()
    return IMAGE_MIME_TYPES.get(ext, 'image/jpeg')

class LLMManager:
    """LLM管理器，支持多种大语言模型服务"""

    def __init__(self, config: Dict):
        self.config = config
        self.llm_config = config.get('llm', {})
        self.enabled = self.llm_config.get('enabled', False)
        
    def is_enabled(self) -> bool:
        """检查LLM功能是否启用"""
        return self.enabled
    
    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """将图片编码为base64格式"""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"图片编码失败: {str(e)}")
            return None
    
    def _call_ollama(self, model: str, prompt: str, image_path: Optional[str] = None) -> Optional[str]:
        """调用Ollama本地模型"""
        try:
            url = f"{self.llm_config['ollama']['base_url']}/api/generate"
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            # 如果有图片，添加图片数据（多模态）
            if image_path:
                image_base64 = self._encode_image_to_base64(image_path)
                if image_base64:
                    payload["images"] = [image_base64]
            
            # 从配置中获取超时时间，默认为60秒
            timeout = self.llm_config.get('ollama', {}).get('timeout', 60)
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except Exception as e:
            logger.error(f"Ollama调用失败: {str(e)}")
            return None
    
    def _call_openai(self, model: str, prompt: str, image_path: Optional[str] = None) -> Optional[str]:
        """调用OpenAI API"""
        try:
            import openai

            openai_config = self.llm_config.get('openai', {})
            client = openai.OpenAI(
                api_key=openai_config.get('api_key'),
                base_url=openai_config.get('base_url')
            )

            messages = []

            if image_path:
                # 多模态消息
                image_base64 = self._encode_image_to_base64(image_path)
                if image_base64:
                    mime_type = _get_image_mime_type(image_path)
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            }
                        ]
                    })
                else:
                    messages.append({"role": "user", "content": prompt})
            else:
                # 纯文本消息
                messages.append({"role": "user", "content": prompt})

            # 从配置中获取max_tokens，默认为4096
            max_tokens = openai_config.get('max_tokens', 4096)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI调用失败: {str(e)}")
            return None
    
    def _call_claude(self, model: str, prompt: str, image_path: Optional[str] = None) -> Optional[str]:
        """调用Claude API"""
        try:
            import anthropic

            claude_config = self.llm_config.get('claude', {})
            client = anthropic.Anthropic(
                api_key=claude_config.get('api_key')
            )

            messages = []

            if image_path:
                # 多模态消息
                image_base64 = self._encode_image_to_base64(image_path)
                if image_base64:
                    mime_type = _get_image_mime_type(image_path)
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_base64
                                }
                            }
                        ]
                    })
                else:
                    messages.append({"role": "user", "content": prompt})
            else:
                # 纯文本消息
                messages.append({"role": "user", "content": prompt})

            # 从配置中获取max_tokens，默认为4096
            max_tokens = claude_config.get('max_tokens', 4096)
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages
            )

            return response.content[0].text  # type: ignore[union-attr]

        except Exception as e:
            logger.error(f"Claude调用失败: {str(e)}")
            return None
    
    def _call_doubao(self, model: str, prompt: str, image_path: Optional[str] = None) -> Optional[str]:
        """调用豆包API"""
        try:
            doubao_config = self.llm_config.get('doubao', {})
            api_key = doubao_config.get('api_key') or os.environ.get('ARK_API_KEY')
            base_url = doubao_config.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3')
            
            if not api_key:
                logger.error("豆包API密钥未配置")
                return None

            client = Ark(
                base_url=base_url,
                api_key=api_key
            )

            messages = []

            if image_path:
                # 多模态消息
                if image_path.startswith(('http://', 'https://')):
                    # 如果是URL，直接使用
                    image_url = image_path
                else:
                    # 如果是本地文件路径，转换为base64
                    image_base64 = self._encode_image_to_base64(image_path)
                    if image_base64:
                        mime_type = _get_image_mime_type(image_path)
                        image_url = f'data:{mime_type};base64,{image_base64}'
                    else:
                        image_url = None

                if image_url:
                    messages.append({
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': image_url
                                }
                            }
                        ]
                    })
                else:
                    messages.append({'role': 'user', 'content': prompt})
            else:
                # 纯文本消息
                messages.append({'role': 'user', 'content': prompt})
            
            # 支持应用层加密
            extra_headers = doubao_config.get('extra_headers', {'x-is-encrypted': 'true'})
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                extra_headers=extra_headers,
                thinking={
                    # "type": "disabled", # 不使用深度思考能力
                    "type": "enabled", # 使用深度思考能力
                    # "type": "auto", # 模型自行判断是否使用深度思考能力
                },
            )
            
            return response.choices[0].message.content  # type: ignore[union-attr]

        except Exception as e:
            logger.error(f"豆包调用失败: {str(e)}")
            return None
    
    def _call_custom_api(self, provider: str, model: str, prompt: str, image_path: Optional[str] = None) -> Optional[str]:
        """调用自定义API（千问等）"""
        try:
            provider_config = self.llm_config.get(provider, {})
            url = provider_config.get('api_url')
            api_key = provider_config.get('api_key')
            
            if not url or not api_key:
                logger.error(f"{provider}配置不完整")
                return None

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': model,
                'messages': []
            }

            if image_path:
                # 多模态消息
                image_base64 = self._encode_image_to_base64(image_path)
                if image_base64:
                    mime_type = _get_image_mime_type(image_path)
                    payload['messages'].append({
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:{mime_type};base64,{image_base64}'
                                }
                            }
                        ]
                    })
                else:
                    payload['messages'].append({'role': 'user', 'content': prompt})
            else:
                # 纯文本消息
                payload['messages'].append({'role': 'user', 'content': prompt})

            # 从当前provider配置中获取超时时间，默认60秒
            timeout = provider_config.get('timeout', 60)
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
        except Exception as e:
            logger.error(f"{provider}调用失败: {str(e)}")
            return None
    
    def process_text(self, text: str) -> Optional[str]:
        """处理文本内容（使用文字模型）"""
        if not self.is_enabled():
            return None
        
        try:
            text_config = self.llm_config.get('text_model', {})
            provider = text_config.get('provider')
            model = text_config.get('model')
            prompt_template = text_config.get('prompt', '请分析以下内容：{content}')
            
            if not provider or not model:
                logger.error("文字模型配置不完整")
                return None

            prompt = prompt_template.format(content=text)
            
            if provider == 'ollama':
                return self._call_ollama(model, prompt)
            elif provider == 'openai':
                return self._call_openai(model, prompt)
            elif provider == 'claude':
                return self._call_claude(model, prompt)
            elif provider == 'doubao':
                return self._call_doubao(model, prompt)
            else:
                # 自定义API提供商
                return self._call_custom_api(provider, model, prompt)
                
        except Exception as e:
            logger.error(f"文本处理失败: {str(e)}")
            return None
    
    def process_image(self, image_path: str) -> Optional[str]:
        """处理图片内容（使用多模态模型）"""
        if not self.is_enabled():
            return None
        
        try:
            vision_config = self.llm_config.get('vision_model', {})
            provider = vision_config.get('provider')
            model = vision_config.get('model')
            prompt_template = vision_config.get('prompt', '请分析这张图片中的内容，特别是如果这是一道题目，请提供详细的解答。')
            
            if not provider or not model:
                logger.error("多模态模型配置不完整")
                return None

            if provider == 'ollama':
                return self._call_ollama(model, prompt_template, image_path)
            elif provider == 'openai':
                return self._call_openai(model, prompt_template, image_path)
            elif provider == 'claude':
                return self._call_claude(model, prompt_template, image_path)
            elif provider == 'doubao':
                return self._call_doubao(model, prompt_template, image_path)
            else:
                # 自定义API提供商
                return self._call_custom_api(provider, model, prompt_template, image_path)
                
        except Exception as e:
            logger.error(f"图片处理失败: {str(e)}")
            return None
    
    def check_availability(self) -> bool:
        """检查LLM服务可用性"""
        if not self.is_enabled():
            return False
        
        try:
            # 检查文字模型提供商
            text_config = self.llm_config.get('text_model', {})
            text_provider = text_config.get('provider')
            
            # 检查多模态模型提供商
            vision_config = self.llm_config.get('vision_model', {})
            vision_provider = vision_config.get('provider')
            
            # 获取需要检查的提供商列表
            providers_to_check = set()
            if text_provider:
                providers_to_check.add(text_provider)
            if vision_provider:
                providers_to_check.add(vision_provider)
            
            # 检查每个提供商的可用性
            for provider in providers_to_check:
                if not self._check_provider_availability(provider):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"LLM可用性检查失败: {str(e)}")
            return False
    
    def _check_provider_availability(self, provider: str) -> bool:
        """检查特定提供商的可用性"""
        try:
            if provider == 'ollama':
                return self._check_ollama_availability()
            elif provider == 'openai':
                return self._check_openai_availability()
            elif provider == 'claude':
                return self._check_claude_availability()
            elif provider == 'doubao':
                return self._check_doubao_availability()
            else:
                # 自定义API提供商
                return self._check_custom_api_availability(provider)
        except Exception as e:
            logger.error(f"{provider}可用性检查失败: {str(e)}")
            return False
    
    def _check_ollama_availability(self) -> bool:
        """检查Ollama服务可用性"""
        try:
            base_url = self.llm_config.get('ollama', {}).get('base_url', 'http://localhost:11434')
            # 从配置中获取超时时间，默认为5秒（健康检查用较短超时）
            timeout = self.llm_config.get('ollama', {}).get('timeout', 60)
            # 健康检查使用较短的超时时间
            health_timeout = min(timeout, 10)  # 最多10秒
            response = requests.get(f"{base_url}/api/tags", timeout=health_timeout)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama连接失败: {str(e)}")
            return False
    
    def _check_openai_availability(self) -> bool:
        """检查OpenAI API可用性"""
        try:
            api_key = self.llm_config.get('openai', {}).get('api_key')
            if not api_key or api_key == 'your_openai_api_key':
                logger.error("OpenAI API密钥未配置")
                return False
            return True
        except Exception as e:
            logger.error(f"OpenAI配置检查失败: {str(e)}")
            return False
    
    def _check_claude_availability(self) -> bool:
        """检查Claude API可用性"""
        try:
            api_key = self.llm_config.get('claude', {}).get('api_key')
            if not api_key or api_key == 'your_claude_api_key':
                logger.error("Claude API密钥未配置")
                return False
            return True
        except Exception as e:
            logger.error(f"Claude配置检查失败: {str(e)}")
            return False
    
    def _check_doubao_availability(self) -> bool:
        """检查豆包API可用性"""
        try:
            doubao_config = self.llm_config.get('doubao', {})
            api_key = doubao_config.get('api_key') or os.environ.get('ARK_API_KEY')
            
            if not api_key:
                logger.error("豆包API密钥未配置")
                return False

            return True
        except Exception as e:
            logger.error(f"豆包配置检查失败: {str(e)}")
            return False
    
    def _check_custom_api_availability(self, provider: str) -> bool:
        """检查自定义API可用性"""
        try:
            provider_config = self.llm_config.get(provider, {})
            api_key = provider_config.get('api_key')
            api_url = provider_config.get('api_url')
            
            if not api_key or not api_url:
                logger.error(f"{provider}配置不完整")
                return False

            return True
        except Exception as e:
            logger.error(f"{provider}配置检查失败: {str(e)}")
            return False

    def validate_config(self) -> bool:
        """验证LLM配置"""
        if not self.llm_config:
            logger.error("LLM配置为空")
            return False

        if not self.llm_config.get('enabled', False):
            logger.info("LLM功能未启用")
            return True  # 未启用不算错误

        # 检查文字模型配置
        text_config = self.llm_config.get('text_model', {})
        if not text_config.get('provider') or not text_config.get('model'):
            logger.warning("文字模型配置不完整")
            return False

        # 检查多模态模型配置
        vision_config = self.llm_config.get('vision_model', {})
        if not vision_config.get('provider') or not vision_config.get('model'):
            logger.warning("多模态模型配置不完整")
            return False

        logger.info("LLM配置验证通过")
        return True