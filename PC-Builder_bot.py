import asyncio  # Модуль для асинхронного программирования
import logging  # Система логирования
from aiogram import Bot, Dispatcher, types, F   # Основные компоненты библиотеки aiogram
from aiogram.filters import CommandStart    # Специальный фильтр для обработки команды /start
import os   # Работа с операционной системой
from dotenv import load_dotenv  # Загрузка переменных окружения
from aiogram.fsm.state import State, StatesGroup    # Компоненты Finite State Machine (FSM)
from aiogram.fsm.context import FSMContext  # Контекст машины состояний
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder  # Набор утилит для построения клавиатур
import sqlite3 as sq    # Библиотека для взаимодействия с базой данных
from typing import Dict, List, Optional    # Аннотации типов

# Загрузка переменных окружения
load_dotenv()

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Получение токена бота из окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Прверка наличия API
if not BOT_TOKEN:
    logging.error('Не найден BOT_TOKEN в файле .env')
    exit()

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Минимальные бюджеты для компонентов
MIN_BUDGETS = {
    'cpu': 2699,
    'motherboard': 4499,
    'ram': 450,
    'cooling_system': 299,
    'psu': 899,
    'case': 1899,
    'gpu': 5499,
    'ssd': 950,
    'nvme': 1699,
    'hdd': 4699
}

# Определяем состояния FSM
class Form(StatesGroup):
    MAIN_MENU = State()    # Главное меню
    CHOOSING_TYPE = State()    # Выбор типа ПК
    WAITING_FOR_BUDGET = State()    # Ожидание ввода бюджета
    SHOW_NEXT_PC = State()    # Вывод альтернативной сборки ПК
    CONFIGURATION_START = State()   # Запуск режима конфигурации ПК
    CPU_BRAND_SELECTION = State()   # Выбор производителя процессора
    AUTO_BUILD_RESULT = State()    # Вывод результата подбора комплектующих

class PCBuilder:
    @staticmethod
    def get_cpu_brands() -> List[str]:
        """Получить список производителей процессоров"""
        with sq.connect("PC.db") as con:
            cur = con.cursor()
            cur.execute("SELECT DISTINCT manufacturer FROM cpu")
            return [row[0] for row in cur.fetchall()]

    @staticmethod
    def find_best_ready_pc(profile_type: str, budget: int) -> Optional[Dict]:
        """Найти лучший готовый ПК по типу и бюджету"""
        with sq.connect("PC.db") as con:
            con.row_factory = sq.Row
            cur = con.cursor()

            cur.execute("SELECT * FROM pc_profiles WHERE type=?", (profile_type,))
            profile = cur.fetchone()

            if not profile:
                return None

            conditions = [
                "cores >= ?",
                "ram >= ?",
                "ssd >= ?",
                "price <= ?"
            ]
            params = [
                profile['min_cpu_cores'],
                profile['min_ram'],
                profile['min_ssd_gb'],
                budget
            ]

            if profile['gpu_required']:
                conditions.append("video_card_type LIKE '%Discrete%'")

            query = f"""
                SELECT * FROM pc 
                WHERE {" AND ".join(conditions)}  
                ORDER BY price DESC, rating DESC 
                LIMIT 1
            """

            cur.execute(query, params)
            return cur.fetchone()

    @staticmethod
    def find_next_ready_pc(profile_type: str, budget: int, exclude_names: List[str]) -> Optional[Dict]:
        """Найти следующий подходящий ПК"""
        with sq.connect("PC.db") as con:
            con.row_factory = sq.Row
            cur = con.cursor()

            cur.execute("SELECT * FROM pc_profiles WHERE type=?", (profile_type,))
            profile = cur.fetchone()

            if not profile:
                return None

            conditions = [
                "cores >= ?",
                "ram >= ?",
                "ssd >= ?",
                "price <= ?"
            ]
            params = [
                profile['min_cpu_cores'],
                profile['min_ram'],
                profile['min_ssd_gb'],
                budget
            ]

            if profile['gpu_required']:
                conditions.append("video_card_type LIKE '%Discrete%'")

            if exclude_names:
                conditions.append(f"pc_name NOT IN ({','.join(['?'] * len(exclude_names))})")
                params.extend(exclude_names)

            query = f"""
                SELECT * FROM pc 
                WHERE {" AND ".join(conditions)} 
                ORDER BY price DESC, rating DESC 
                LIMIT 1
            """
            cur.execute(query, params)
            return cur.fetchone()

    @staticmethod
    def format_pc_info(pc: Dict) -> str:
        """Форматирование информации о ПК"""
        return (
                f"💻 *{pc['pc_name']}*\n\n"
                f"⚙️ *Характеристики:*\n"
                f"- Процессор: {pc['processor']} ({pc['cores']} ядер, {pc['threads']} потоков)\n"
                f"- Видеокарта: {pc['video_card_type']} {pc['video_card_model']} ({pc['video_memory']} ГБ)\n"
                f"- Память: {pc['ram']} ГБ {pc['ram_type']}\n"
                f"- Накопитель: SSD {pc['ssd']} ГБ" + (f", HDD {pc['hdd']} ГБ" if pc['hdd'] else "") + "\n"
                f"- ОС: {pc['os']}\n\n"
                f"⭐ Рейтинг: {pc['rating']}/5\n"
                f"💰 Цена: {pc['price']} ₽"
        )


    @staticmethod
    def get_budget_distribution(pc_type: str, total_budget: int) -> Dict[str, float]:
        """Распределение бюджета по компонентам в зависимости от типа ПК"""
        distributions = {
            'Игровой компьютер': {
                'cpu': 0.2,  # Процессор
                'gpu': 0.3,  # Видеокарта
                'motherboard': 0.09,  # Материнская плата
                'ram': 0.1,  # Оперативная память
                'cooling_system': 0.04,  # Система охлаждения
                'nvme': 0.05,  # NVMe накопитель
                'hdd': 0.05,  # HDD
                'psu': 0.1,  # Блок питания
                'case': 0.07  # Корпус
            },
            'Компьютер для работы с графикой': {
                'cpu': 0.25,  # Процессор
                'gpu': 0.25,  # Видеокарта
                'motherboard': 0.09,  # Материнская плата
                'ram': 0.1,  # Оперативная память
                'cooling_system': 0.03,  # Система охлаждения
                'nvme': 0.06,  # NVMe накопитель
                'hdd': 0.05,  # HDD
                'psu': 0.1,  # Блок питания
                'case': 0.07  # Корпус
            },
            'Офисный компьютер': {
                'cpu': 0.2,  # Процессор
                'gpu': 0.05,  # Видеокарта (минимальная)
                'motherboard': 0.1,  # Материнская плата
                'ram': 0.15,  # Оперативная память
                'cooling_system': 0.1,  # Система охлаждения
                'ssd': 0.2,  # SSD
                'psu': 0.1,  # Блок питания
                'case': 0.1  # Корпус
            },
            'Сервер': {
                'cpu': 0.21,  # Процессор
                'gpu': 0.02,  # Видеокарта (минимальная)
                'motherboard': 0.10,  # Материнская плата
                'ram': 0.19,  # Оперативная память
                'cooling_system': 0.1,  # Система охлаждения
                'nvme': 0.1,  # NVMe накопитель
                'hdd': 0.1,  # HDD
                'psu': 0.1,  # Блок питания
                'case': 0.07  # Корпус
            },
            'Домашний компьютер': {
                'cpu': 0.17,  # Процессор
                'gpu': 0.15,  # Видеокарта
                'motherboard': 0.1,  # Материнская плата
                'ram': 0.15,  # Оперативная память
                'cooling_system': 0.1,  # Система охлаждения
                'nvme': 0.1,  # NVMe накопитель
                'hdd': 0.05,  # HDD
                'psu': 0.1,  # Блок питания
                'case': 0.1  # Корпус
            },
            'Компьютер для программирования': {
                'cpu': 0.25,  # Процессор
                'gpu': 0.1,  # Видеокарта
                'motherboard': 0.1,  # Материнская плата
                'ram': 0.13,  # Оперативная память
                'cooling_system': 0.07,  # Система охлаждения
                'ssd': 0.1,  # SSD
                'nvme': 0.1,  # NVMe накопитель
                'psu': 0.1,  # Блок питания
                'case': 0.05  # Корпус
            }
        }

        # Получаем распределение для указанного типа или используем по умолчанию
        distribution = distributions.get(pc_type, {
            'cpu': 0.2,  # Процессор
            'gpu': 0.2,  # Видеокарта
            'motherboard': 0.1,  # Материнская плата
            'ram': 0.1,  # Оперативная память
            'cooling_system': 0.07,  # Система охлаждения
            'nvme': 0.1,  # NVMe накопитель
            'hdd': 0.08,  # HDD
            'psu': 0.1,  # Блок питания
            'case': 0.05  # Корпус
        })

        # Рассчитываем бюджет для каждого компонента
        component_budgets = {comp: int(total_budget * perc)
                             for comp, perc in distribution.items()}

        # Применяем минимальные бюджеты
        for component, min_price in MIN_BUDGETS.items():
            if component in component_budgets and component_budgets[component] < min_price:
                # Перераспределяем из менее важных компонентов
                needed = min_price - component_budgets[component]
                if component != 'hdd':
                    component_budgets['hdd'] = max(0, component_budgets.get('hdd', 0) - needed * 0.7)
                if component != 'case':
                    component_budgets['case'] = max(0, component_budgets.get('case', 0) - needed * 0.3)
                component_budgets[component] = min_price

        # Динамическая адаптация для дорогих сборок
        if total_budget > 100000:
            scale = min(1.5, total_budget / 100000)
            for comp in ['cpu', 'gpu', 'ram', 'nvme']:
                if comp in component_budgets:
                    component_budgets[comp] = int(component_budgets[comp] * scale)

            # Уменьшаем менее важные компоненты
            for comp in ['hdd', 'case']:
                if comp in component_budgets:
                    component_budgets[comp] = int(component_budgets[comp] * 0.8)

        # Корректировка для специфичных типов ПК
        if pc_type in ['Офисный компьютер', 'Сервер']:
            component_budgets['gpu'] = min(component_budgets.get('gpu', 0), 5000)
            if 'nvme' in component_budgets:
                component_budgets['nvme'] = min(component_budgets['nvme'], 10000)
                component_budgets['ssd'] = component_budgets.get('ssd', 0) + component_budgets['nvme'] // 2

        if pc_type == 'Игровой компьютер':
            component_budgets['nvme'] = max(component_budgets.get('nvme', 0), 15000)
            if component_budgets.get('ssd', 0) > 5000:
                component_budgets['ssd'] -= 3000

        return component_budgets

    @staticmethod
    def auto_build_pc(pc_type: str, total_budget: int, cpu_brand: str = None) -> Optional[Dict]:
        """Автоматический подбор ПК с проверкой совместимости всех компонентов"""
        def get_safe(row, key, default=None):
            """Безопасное получение значения из строки БД"""
            if hasattr(row, 'keys') and key in row.keys():
                return row[key]
            return default

        component_budgets = PCBuilder.get_budget_distribution(pc_type, total_budget)
        components = {}
        remaining_budget = total_budget
        total_power = 0
        warnings = []

        try:
            with sq.connect("PC.db") as con:
                con.row_factory = sq.Row
                cur = con.cursor()

                # 1. Подбор процессора (сначала DDR5, потом DDR4)
                for ram_type in ['DDR5', 'DDR4']:
                    cpu_query = """
                        SELECT * FROM cpu 
                        WHERE price <= ? 
                        AND (? IS NULL OR manufacturer = ?)
                        AND ram_type LIKE '%' || ? || '%'
                        ORDER BY cores DESC, clock_frequency DESC, price ASC
                        LIMIT 1
                    """
                    cur.execute(cpu_query, (
                        component_budgets['cpu'],
                        cpu_brand,
                        cpu_brand,
                        ram_type
                    ))
                    cpu = cur.fetchone()
                    if not cpu:
                        continue

                    # 2. Подбор материнской платы
                    socket = get_safe(cpu, 'socket')
                    mb_query = """
                        SELECT * FROM motherboard 
                        WHERE socket = ? 
                        AND ram_type LIKE '%' || ? || '%'
                        AND price <= ?
                        ORDER BY max_ram_freq DESC, price ASC
                        LIMIT 1
                    """
                    cur.execute(mb_query, (
                        socket,
                        ram_type,
                        component_budgets['motherboard']
                    ))
                    mb = cur.fetchone()
                    if not mb:
                        continue

                    # 3. Подбор оперативной памяти
                    max_freq = get_safe(mb, 'max_ram_freq', 3200)
                    ram_modules = 2 if total_budget > 50000 else 1
                    ram_query = """
                        SELECT * FROM ram 
                        WHERE ram_type LIKE '%' || ? || '%'
                        AND clock_freq <= ?
                        AND price <= ?
                        AND moduls_in_set <= ?
                        ORDER BY amount DESC, price ASC
                        LIMIT 1
                    """
                    cur.execute(ram_query, (
                        ram_type,
                        max_freq,
                        component_budgets['ram'],
                        ram_modules
                    ))
                    ram = cur.fetchone()
                    if not ram:
                        continue

                    # Сохранение подобранных компонентов
                    components.update({
                        'cpu': dict(cpu),
                        'motherboard': dict(mb),
                        'ram': dict(ram)
                    })
                    remaining_budget -= (cpu['price'] + mb['price'] + ram['price'])
                    total_power += (get_safe(cpu, 'energy', 65) + get_safe(mb, 'energy', 30) +
                                    get_safe(ram, 'energy', 5) * get_safe(ram, 'moduls_in_set', 1))
                    break
                else:
                    warnings.append("Не удалось подобрать совместимые CPU, MB и RAM")
                    return None

                # 4. Подбор системы охлаждения
                cooling_query = """
                    SELECT * FROM cooling_system 
                    WHERE socket LIKE '%' || ? || '%'
                    AND price <= ?
                    AND power_dissipation >= ?
                    ORDER BY power_dissipation ASC, price ASC
                    LIMIT 3
                """
                cpu_tdp = get_safe(components['cpu'], 'heat_gen', 65)
                cur.execute(cooling_query, (
                    components['cpu']['socket'],
                    component_budgets['cooling_system'],
                    cpu_tdp * 1.2  # 20% запас
                ))
                potential_coolers = [dict(row) for row in cur.fetchall()]

                # 5. Подбор видеокарты (если требуется)
                if pc_type in ['Игровой компьютер', 'Компьютер для работы с графикой']:
                    gpu_query = """
                        SELECT * FROM gpu 
                        WHERE price <= ?
                        AND con_interface IN (
                            SELECT pcie_v FROM motherboard 
                            WHERE motherboard_name = ?
                        )
                        ORDER BY gpu_memory DESC, price ASC
                        LIMIT 1
                    """
                    cur.execute(gpu_query, (
                        component_budgets['gpu'],
                        components['motherboard']['motherboard_name']
                    ))
                    gpu = cur.fetchone()
                    if gpu:
                        components['gpu'] = dict(gpu)
                        remaining_budget -= gpu['price']
                        total_power += get_safe(gpu, 'energy', 150)
                    else:
                        warnings.append("Не удалось подобрать совместимую видеокарту")

                # 6. Подбор накопителей
                # NVMe (приоритетный)
                if component_budgets.get('nvme', 0) > 0:
                    nvme_query = """
                        SELECT * FROM ssd 
                        WHERE connection_interface LIKE '%NVMe%'
                        AND price <= ?
                        ORDER BY capacity DESC, max_data_transfer_rate DESC
                        LIMIT 1
                    """
                    cur.execute(nvme_query, (
                        min(component_budgets['nvme'], remaining_budget),
                    ))
                    nvme = cur.fetchone()
                    if nvme:
                        components['nvme'] = dict(nvme)
                        remaining_budget -= nvme['price']
                        total_power += get_safe(nvme, 'energy', 5)

                # SSD (если остался бюджет)
                if component_budgets.get('ssd', 0) > 0 and remaining_budget > 0:
                    ssd_query = """
                        SELECT * FROM ssd 
                        WHERE connection_interface LIKE '%SATA%'
                        AND price <= ?
                        ORDER BY capacity DESC, max_data_transfer_rate DESC
                        LIMIT 1
                    """
                    cur.execute(ssd_query, (
                        min(component_budgets['ssd'], remaining_budget),
                    ))
                    ssd = cur.fetchone()
                    if ssd:
                        components['ssd'] = dict(ssd)
                        remaining_budget -= ssd['price']
                        total_power += get_safe(ssd, 'energy', 5)

                # HDD (если остался бюджет)
                if component_budgets.get('hdd', 0) > 0 and remaining_budget > 0:
                    hdd_query = """
                        SELECT * FROM storage 
                        WHERE storage_type = 'HDD'
                        AND price <= ?
                        ORDER BY capacity DESC
                        LIMIT 1
                    """
                    cur.execute(hdd_query, (
                        min(component_budgets['hdd'], remaining_budget),
                    ))
                    hdd = cur.fetchone()
                    if hdd:
                        components['hdd'] = dict(hdd)
                        remaining_budget -= hdd['price']
                        total_power += get_safe(hdd, 'energy', 7)

                # 7. Подбор блока питания
                required_power = ((total_power + 100) // 50) * 50  # Округляем до 50 Вт

                # Увеличиваем запас мощности
                if pc_type == 'Игровой компьютер':
                    required_power = max(required_power * 1.3, 650)
                elif pc_type == 'Компьютер для работы с графикой':
                    required_power = max(required_power * 1.2, 550)
                else:
                    required_power = max(required_power, 450)

                psu_budget = max(component_budgets['psu'], MIN_BUDGETS['psu'])
                if remaining_budget > psu_budget:
                    psu_budget = min(psu_budget + remaining_budget // 2, remaining_budget)

                psu_query = """
                    SELECT * FROM psu 
                    WHERE power >= ? 
                    AND price <= ?
                    ORDER BY 
                        CASE
                            WHEN certificate = 'N' THEN 1
                            WHEN certificate IN ('Standart', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Titanium') THEN 0
                        END,
                        price ASC
                    LIMIT 1
                """
                cur.execute(psu_query, (required_power, psu_budget))
                psu = cur.fetchone()

                if not psu:
                    # Пробуем найти любой подходящий БП
                    cur.execute("""
                        SELECT * FROM psu 
                        WHERE power >= ? 
                        ORDER BY price ASC 
                        LIMIT 1
                    """, (required_power,))
                    psu = cur.fetchone()

                if psu:
                    components['psu'] = dict(psu)
                    remaining_budget -= psu['price']
                else:
                    warnings.append("Не удалось подобрать блок питания с требуемой мощностью")

                # 8. Подбор корпуса с учетом всех ограничений
                case_query = """
                    SELECT * FROM cases 
                    WHERE price <= ? 
                    AND motherboard_form LIKE '%' || ? || '%'
                    {gpu_condition}
                    {cooler_condition}
                    ORDER BY rating DESC, price ASC
                    LIMIT 1
                """

                # Условия для корпуса
                conditions = {
                    'gpu_condition': "",
                    'cooler_condition': ""
                }
                params = [component_budgets['case'], components['motherboard']['form_factor']]

                # Условие для длины видеокарты
                if 'gpu' in components:
                    gpu_length = get_safe(components['gpu'], 'length', 300)
                    conditions['gpu_condition'] = "AND gpu_length >= ?"
                    params.append(gpu_length)

                # Условие для системы охлаждения
                if potential_coolers:
                    cooler_type = get_safe(potential_coolers[0], 'type', 'air').lower()
                    if cooler_type == 'liquid':
                        conditions['cooler_condition'] = "AND lcs_sup = 'Y'"
                    else:
                        cooler_height = get_safe(potential_coolers[0], 'height', 160)
                        conditions['cooler_condition'] = "AND cooler_height >= ?"
                        params.append(cooler_height)

                # Формируем окончательный запрос
                final_case_query = case_query.format(**conditions)
                cur.execute(final_case_query, params)
                case = cur.fetchone()

                if case:
                    components['case'] = dict(case)
                    remaining_budget -= case['price']

                    # Выбор окончательного кулера с учетом корпуса
                    selected_cooler = None
                    for cooler in potential_coolers:
                        cooler_type = get_safe(cooler, 'type', 'air').lower()
                        if cooler_type == 'liquid':
                            if get_safe(case, 'lcs_sup') == 'Y':
                                selected_cooler = cooler
                                break
                        else:
                            cooler_height = get_safe(cooler, 'height', 160)
                            case_max_height = get_safe(case, 'cooler_height', 200)
                            if cooler_height <= case_max_height:
                                selected_cooler = cooler
                                break

                    if selected_cooler:
                        components['cooling_system'] = selected_cooler
                        remaining_budget -= selected_cooler['price']
                    else:
                        warnings.append("Не удалось подобрать совместимую систему охлаждения")
                else:
                    warnings.append("Не удалось подобрать совместимый корпус")

                # Проверяем минимально необходимые компоненты
                required_components = ['cpu', 'motherboard', 'ram', 'psu']
                if not all(comp in components for comp in required_components):
                    warnings.append("Не удалось подобрать все необходимые компоненты")
                    return None

                if warnings:
                    components['warnings'] = warnings

                return components

        except Exception as e:
            logging.error(f"Ошибка при сборке ПК: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def format_configuration(components: Dict, pc_type: str, budget: int) -> str:
        """Форматирование информации о конфигурации"""
        # Функция для безопасного получения цены компонента
        def get_price(component):
            if isinstance(component, dict):
                return component.get('price', 0)
            elif isinstance(component, list) and component and isinstance(component[0], dict):
                return sum(item.get('price', 0) for item in component)
            return 0

        total_price = sum(get_price(comp) for comp in components.values())
        used_budget_percent = (total_price / budget) * 100

        response = [
            f"💻 *{pc_type}* | Бюджет: {budget} ₽",
            f"💰 *Общая стоимость: {total_price} ₽ ({used_budget_percent:.1f}% бюджета)*",
            "",
            "⚙️ *Конфигурация:*",
            "",
            f"🔹 *Процессор:* {components['cpu']['manufacturer']} {components['cpu']['cpu_name']}",
            f"   - Ядер/потоков: {components['cpu']['cores']}/{components['cpu']['threads']}",
            f"   - Частота: {components['cpu']['clock_frequency']} ГГц",
            f"   - TDP: {components['cpu'].get('heat_gen', '?')}W",
            f"   - Цена: {components['cpu']['price']} ₽",
            "",
            f"🔹 *Материнская плата:* {components['motherboard']['manufacturer']} {components['motherboard']['motherboard_name']}",
            f"   - Форм-фактор: {components['motherboard']['form_factor']}",
            f"   - Сокет: {components['motherboard']['socket']}",
            f"   - Чипсет: {components['motherboard']['chipset']}",
            f"   - Цена: {components['motherboard']['price']} ₽",
            "",
            f"🔹 *Оперативная память:* {components['ram']['manufacturer']} {components['ram']['ram_name']}",
            f"   - Объем: {components['ram']['amount']} ГБ",
            f"   - Тип: {components['ram']['ram_type']}",
            f"   - Частота: {components['ram']['clock_freq']} МГц",
            f"   - Цена: {components['ram']['price']} ₽",
        ]

        if 'cooling_system' in components:
            cooling = components['cooling_system']
            if isinstance(cooling, dict):
                response.extend([
                    "",
                    f"🔹 *Охлаждение:* {cooling['manufacturer']} {cooling['cs_name']}",
                    f"   - Тип: {cooling['type']}",
                    f"   - Рассеиваемая мощность: {cooling.get('power_dissipation', '?')}W",
                    f"   - Цена: {cooling['price']} ₽"
                ])
            elif isinstance(cooling, list) and cooling:
                # Если система охлаждения - список, берем первый элемент
                cooling = cooling[0]
                response.extend([
                    "",
                    f"🔹 *Охлаждение:* {cooling['manufacturer']} {cooling['cs_name']}",
                    f"   - Тип: {cooling['type']}",
                    f"   - Рассеиваемая мощность: {cooling.get('power_dissipation', '?')}W",
                    f"   - Цена: {cooling['price']} ₽"
                ])

        if 'gpu' in components:
            gpu = components['gpu']
            response.extend([
                "",
                f"🔹 *Видеокарта:* {gpu['manufacturer']} {gpu['gpu_name']}",
                f"   - Видеопамять: {gpu['gpu_memory']} ГБ {gpu.get('memory_type', '')}",
                f"   - GPU: {gpu['gpu']} @ {gpu['gpu_freq']} МГц",
                f"   - TDP: {gpu.get('energy', '?')}W",
                f"   - Цена: {gpu['price']} ₽"
            ])

        # Накопители
        storage_info = []
        if 'nvme' in components:
            nvme = components['nvme']
            storage_info.append(
                f"\n🔹 *NVMe SSD:* {nvme['manufacturer']} {nvme['storage_name']}\n"
                f"   - Объём: {nvme['capacity']}GB\n"
                f"   - Скорость: {nvme['max_data_transfer_rate']} MB/s\n"
                f"   - Цена: {nvme['price']} ₽"
            )

        if 'ssd' in components:
            ssd = components['ssd']
            storage_info.append(
                f"\n🔹 *SATA SSD:* {ssd['manufacturer']} {ssd['storage_name']}\n"
                f"   - Объём: {ssd['capacity']}GB\n"
                f"   - Скорость: {ssd['max_data_transfer_rate']} MB/s\n"
                f"   - Цена: {ssd['price']} ₽"
            )

        if 'hdd' in components:
            hdd = components['hdd']
            storage_info.append(
                f"\n🔹 *HDD:* {hdd['manufacturer']} {hdd['storage_name']}\n"
                f"   - Объём: {hdd['capacity']}GB\n"
                f"   - Скорость: {hdd.get('spindle_speed', '?')} RPM\n"
                f"   - Цена: {hdd['price']} ₽"
            )

        if not storage_info:
            storage_info.append("\n🔹 *Накопитель:* Не подобран")
        response.extend(storage_info)

        # Блок питания
        if 'psu' in components:
            psu = components['psu']
            response.extend([
                "",
                f"🔹 *Блок питания:* {psu['manufacturer']} {psu['psu_name']}",
                f"   - Мощность: {psu['power']}W",
                f"   - Сертификат: {psu.get('certificate', 'нет')}",
                f"   - Цена: {psu['price']} ₽"
            ])

        # Корпус
        if 'case' in components:
            case = components['case']
            compatibility = ""
            if 'motherboard' in components:
                mb_form = components['motherboard']['form_factor']
                case_forms = case.get('motherboard_form', '')
                if mb_form and case_forms:
                    compatible = mb_form in case_forms
                    compatibility = "✅ Совместим" if compatible else "⚠️ Требуется проверка"
                else:
                    compatibility = "ℹ️ Неизвестно"

            response.extend([
                "",
                f"🔹 *Корпус:* {case['manufacturer']} {case['case_name']}",
                f"   - Форм-фактор: {case['form_factor']}",
                f"   - Совместимость: {compatibility}",
                f"   - Цена: {case['price']} ₽"
            ])
        else:
            response.extend(["", "🔹 *Корпус:* Не подобран"])

        response.extend([
            "",
            "Вы можете:",
            "🔸 Собрать новую конфигурацию",
            "🔸 Вернуться в главное меню"
        ])

        return "\n".join(response)


# Обработка команды "/start"
@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    kb = [
        [types.KeyboardButton(text='Подобрать готовый ПК')],
        [types.KeyboardButton(text='Подобрать комплектующие')]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    welcome_text = (
        "🖥️ *Добро пожаловать в бот для подбора ПК!*\n\n"
        "Я помогу вам:\n"
        "🔹 Подобрать готовый компьютер\n"
        "🔹 Собрать систему из комплектующих\n\n"
        "Выберите опцию:"
    )

    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(Form.MAIN_MENU)


# Обработчик кнопки "Вернуться в главное меню"
@dp.message(F.text == '🏠 Вернуться в главное меню')
async def back_handler(message: types.Message, state: FSMContext):
    # Очищаем все данные состояния
    await state.clear()
    await start_handler(message, state)


# Обработчик кнопки "Подобрать готовый ПК"
@dp.message(Form.MAIN_MENU, F.text == 'Подобрать готовый ПК')
async def ready_pc_handler(message: types.Message, state: FSMContext):
    kb = [
        [types.KeyboardButton(text='Игровой компьютер')],
        [types.KeyboardButton(text='Домашний компьютер')],
        [types.KeyboardButton(text='Офисный компьютер')],
        [types.KeyboardButton(text='Сервер')],
        [types.KeyboardButton(text='Компьютер для программирования')],
        [types.KeyboardButton(text='Компьютер для работы с графикой')],
        [types.KeyboardButton(text='Вернуться в главное меню')]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(
        "Выберите тип готового компьютера:",
        reply_markup=keyboard
    )
    await state.set_state(Form.CHOOSING_TYPE)


# Обработчик выбора типа готового ПК
@dp.message(Form.CHOOSING_TYPE, F.text.in_([
    'Игровой компьютер', 'Домашний компьютер', 'Офисный компьютер',
    'Сервер', 'Компьютер для программирования', 'Компьютер для работы с графикой'
]))
async def select_ready_pc_type(message: types.Message, state: FSMContext):
    await state.update_data(selected_type=message.text)
    await message.answer(
        f"Вы выбрали {message.text}. Введите ваш бюджет в рублях:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Form.WAITING_FOR_BUDGET)


# Обработчик кнопки "Подобрать комплектующие"
@dp.message(Form.MAIN_MENU, F.text == 'Подобрать комплектующие')
async def components_handler(message: types.Message, state: FSMContext):
    kb = [
        [types.KeyboardButton(text='Игровой компьютер')],
        [types.KeyboardButton(text='Домашний компьютер')],
        [types.KeyboardButton(text='Офисный компьютер')],
        [types.KeyboardButton(text='Сервер')],
        [types.KeyboardButton(text='Компьютер для программирования')],
        [types.KeyboardButton(text='Компьютер для работы с графикой')],
        [types.KeyboardButton(text='Вернуться в главное меню')]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(
        "Для какого типа ПК будем подбирать комплектующие?",
        reply_markup=keyboard
    )
    await state.set_state(Form.CONFIGURATION_START)


# Обработчик выбора типа ПК для подбора комплектующих
@dp.message(Form.CONFIGURATION_START, F.text.in_([
    'Игровой компьютер', 'Домашний компьютер', 'Офисный компьютер',
    'Сервер', 'Компьютер для программирования', 'Компьютер для работы с графикой'
]))
async def select_pc_type_for_components(message: types.Message, state: FSMContext):
    await state.update_data(selected_type=message.text)

    brands = PCBuilder.get_cpu_brands()
    if not brands:
        await message.answer("Не удалось загрузить производителей процессоров")
        return

    builder = ReplyKeyboardBuilder()
    for brand in brands:
        builder.add(types.KeyboardButton(text=brand))
    builder.add(types.KeyboardButton(text='Без предпочтений'))
    builder.add(types.KeyboardButton(text='Назад'))
    builder.adjust(2)

    await message.answer(
        "Выберите предпочитаемого производителя процессора:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(Form.CPU_BRAND_SELECTION)


# Обработчик выбора производителя процессора
@dp.message(Form.CPU_BRAND_SELECTION)
async def process_cpu_brand_selection(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await components_handler(message, state)
        return

    cpu_brand = None if message.text == 'Без предпочтений' else message.text
    await state.update_data(cpu_brand=cpu_brand)

    await message.answer(
        "Введите ваш бюджет в рублях:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Form.WAITING_FOR_BUDGET)


# Обработчик бюджета
@dp.message(Form.WAITING_FOR_BUDGET)
async def process_budget(message: types.Message, state: FSMContext):
    try:
        budget = int(message.text)
        if budget <= 0:
            raise ValueError

        data = await state.get_data()

        # Определяем тип подбора (готовый ПК или комплектующие)
        if 'cpu_brand' in data:  # Если есть выбор процессора - это подбор комплектующих
            pc_type = data['selected_type']
            cpu_brand = data['cpu_brand']

            components = PCBuilder.auto_build_pc(pc_type, budget, cpu_brand)

            if not components:
                await message.answer("Не удалось подобрать конфигурацию. Попробуйте увеличить бюджет.")
                return

            await state.update_data(components=components, budget=budget)
            await show_configuration(message, state)

        else:  # Подбор готового ПК
            selected_type = data['selected_type']
            # Используем метод find_best_ready_pc для поиска оптимальной конфигурации
            best_pc = PCBuilder.find_best_ready_pc(selected_type, budget)

            if not best_pc:
                await message.answer("Не найдено подходящих ПК. Попробуйте изменить параметры.")
                return

            # Форматируем информацию о ПК с использованием метода format_pc_info
            response = PCBuilder.format_pc_info(best_pc)

            # Создаем клавиатуру с кнопкой покупки (если есть ссылка)
            builder = InlineKeyboardBuilder()
            if 'link' in best_pc.keys() and best_pc['link']:
                builder.row(types.InlineKeyboardButton(
                    text="🛒 Купить", url=best_pc['link']
                ))

            # Клавиатура для навигации
            show_more_kb = [
                [types.KeyboardButton(text='Показать ещё вариант')],
                [types.KeyboardButton(text='🏠 Вернуться в главное меню')]
            ]
            keyboard = types.ReplyKeyboardMarkup(keyboard=show_more_kb, resize_keyboard=True)

            # Отправляем сообщение с информацией о ПК и кнопками
            await message.answer(response, reply_markup=builder.as_markup(), parse_mode="Markdown")
            await message.answer("Выберите действие:", reply_markup=keyboard)

            # Сохраняем данные в состоянии
            await state.update_data(
                shown_pcs=[best_pc['pc_name']],
                budget=budget,
                pc_type=selected_type
            )
            await state.set_state(Form.SHOW_NEXT_PC)

    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму бюджета (целое число больше 0).")


# Вывод конфигурации
async def show_configuration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    components = data['components']
    pc_type = data['selected_type']
    budget = data['budget']

    response = PCBuilder.format_configuration(components, pc_type, budget)

    # Клавиатура с тремя кнопками
    kb = [
        [types.KeyboardButton(text='🔗 Ссылки на покупку')],
        [types.KeyboardButton(text='🔄 Собрать новую конфигурацию')],
        [types.KeyboardButton(text='🏠 Вернуться в главное меню')]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(Form.AUTO_BUILD_RESULT)


# Вывод ссылок
@dp.message(Form.AUTO_BUILD_RESULT, F.text == '🔗 Ссылки на покупку')
async def show_purchase_links(message: types.Message, state: FSMContext):
    data = await state.get_data()
    components = data['components']

    builder = InlineKeyboardBuilder()

    # Добавляем ссылки только для тех компонентов, где они есть
    for comp_type, comp in components.items():
        if comp.get('link'):
            name = {
                'cpu': 'Процессор',
                'gpu': 'Видеокарта',
                'ram': 'Память',
                'storage': 'Накопитель',
                'motherboard': 'Материнская плата',
                'psu': 'Блок питания',
                'case': 'Корпус'
            }.get(comp_type, comp_type)

            builder.add(types.InlineKeyboardButton(
                text=f"Купить {name}",
                url=comp['link']
            ))

    builder.adjust(1)  # По одной кнопке в строке

    if builder.buttons:
        await message.answer(
            "Ссылки для покупки компонентов:",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer("Извините, ссылки на покупку недоступны для этой конфигурации")


# Обработчик кнопки "Собрать новую конфигурацию"
@dp.message(Form.AUTO_BUILD_RESULT, F.text == '🔄 Собрать новую конфигурацию')
async def rebuild_configuration(message: types.Message, state: FSMContext):
    await components_handler(message, state)  # Возврат к выбору типа ПК


# Обработчик кнопки "Вернуться в главное меню"
@dp.message(Form.AUTO_BUILD_RESULT, F.text == '🏠 Вернуться в главное меню')
async def back_to_main_from_config(message: types.Message, state: FSMContext):
    await start_handler(message, state)  # Полный сброс к началу


# Обработчик кнопки "Показать еще вариант"
@dp.message(Form.SHOW_NEXT_PC, F.text == 'Показать ещё вариант')
async def show_next_pc_handler(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        shown_pcs = data.get('shown_pcs', [])
        pc_type = data['pc_type']
        budget = data['budget']

        next_pc = PCBuilder.find_next_ready_pc(pc_type, budget, shown_pcs)

        if not next_pc:
            await message.answer("❌ Больше вариантов нет. Попробуйте изменить бюджет.")
            return

        response = PCBuilder.format_pc_info(next_pc)

        builder = InlineKeyboardBuilder()
        if 'link' in next_pc.keys() and next_pc['link']:
            builder.row(types.InlineKeyboardButton(
                text="🛒 Купить", url=next_pc['link']
            ))

        await message.answer(response, reply_markup=builder.as_markup(), parse_mode="Markdown")
        await state.update_data(shown_pcs=shown_pcs + [next_pc['pc_name']])

    except Exception as e:
        logging.error(f"Ошибка при поиске следующего ПК: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте снова.")


# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())