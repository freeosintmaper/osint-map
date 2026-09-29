import re
import json
import sys
import urllib.request
import time
import random
import math
import os
from html import unescape
from collections import Counter

CHANNELS = [
    "GeneralStaffZSU", "operativnoZSU",
    "ukrpravda_news", "uniannet",
    "DeepStateUA", "OsintFlow",
    "kharkiv_typical", "dnepr_typical", "odesa_typical",
    "kherson_typical", "donbass_realii",
    "kyivindependent_official",
    "informnapalm",
    "rybar", "voenkorKotenok", "wargonzo",
    "readovkanews", "lost_armour",
    "boris_rozhin", "epoddubny", "RVvoenkor", "dva_majors",
]

CHANNEL_COUNTRY = {
    "GeneralStaffZSU": "UA", "operativnoZSU": "UA",
    "ukrpravda_news": "UA", "uniannet": "UA", "DeepStateUA": "UA",
    "OsintFlow": "UA",
    "kharkiv_typical": "UA", "dnepr_typical": "UA", "odesa_typical": "UA",
    "kherson_typical": "UA", "donbass_realii": "UA",
    "kyivindependent_official": "UA",
    "informnapalm": "OSINT",
    "rybar": "RU", "voenkorKotenok": "RU", "wargonzo": "RU",
    "readovkanews": "RU", "lost_armour": "RU",
    "boris_rozhin": "RU", "epoddubny": "RU", "RVvoenkor": "RU",
    "dva_majors": "RU",
}

SPEAKER_CAPITALS = {
    "зеленськ": [50.4501, 30.5234, "Киев", "UA"],
    "зеленск": [50.4501, 30.5234, "Киев", "UA"],
    "зеленский": [50.4501, 30.5234, "Киев", "UA"],
    "офіс президента": [50.4501, 30.5234, "Киев", "UA"],
    "офис президента": [50.4501, 30.5234, "Киев", "UA"],
    "оп зе": [50.4501, 30.5234, "Киев", "UA"],
    "кабмін україн": [50.4501, 30.5234, "Киев", "UA"],
    "кабмин украин": [50.4501, 30.5234, "Киев", "UA"],
    "верховна рада": [50.4501, 30.5234, "Киев", "UA"],
    "верховная рада": [50.4501, 30.5234, "Киев", "UA"],
    "раді заявили": [50.4501, 30.5234, "Киев", "UA"],
    "в раде заявили": [50.4501, 30.5234, "Киев", "UA"],
    "минобороны украины": [50.4501, 30.5234, "Киев", "UA"],
    "міністерство оборони україн": [50.4501, 30.5234, "Киев", "UA"],
    "минобороны украин": [50.4501, 30.5234, "Киев", "UA"],
    "генштаб зсу": [50.4501, 30.5234, "Киев", "UA"],
    "генштаб вс": [50.4501, 30.5234, "Киев", "UA"],
    "сбу заявила": [50.4501, 30.5234, "Киев", "UA"],
    "сбу заявил": [50.4501, 30.5234, "Киев", "UA"],
    "київ заявив": [50.4501, 30.5234, "Киев", "UA"],
    "киев заявил": [50.4501, 30.5234, "Киев", "UA"],
    "україна заявила": [50.4501, 30.5234, "Киев", "UA"],
    "украина заявила": [50.4501, 30.5234, "Киев", "UA"],
    "українська влада": [50.4501, 30.5234, "Киев", "UA"],
    "украинские власти": [50.4501, 30.5234, "Киев", "UA"],
    "путін": [55.7558, 37.6173, "Москва", "RU"],
    "путин": [55.7558, 37.6173, "Москва", "RU"],
    "кремль": [55.7558, 37.6173, "Москва", "RU"],
    "кремл": [55.7558, 37.6173, "Москва", "RU"],
    "песков": [55.7558, 37.6173, "Москва", "RU"],
    "лавров": [55.7558, 37.6173, "Москва", "RU"],
    "шойгу": [55.7558, 37.6173, "Москва", "RU"],
    "захарова": [55.7558, 37.6173, "Москва", "RU"],
    "госдума": [55.7558, 37.6173, "Москва", "RU"],
    "дума заявила": [55.7558, 37.6173, "Москва", "RU"],
    "совфед": [55.7558, 37.6173, "Москва", "RU"],
    "минобороны рф": [55.7558, 37.6173, "Москва", "RU"],
    "министерство обороны рф": [55.7558, 37.6173, "Москва", "RU"],
    "москва заявила": [55.7558, 37.6173, "Москва", "RU"],
    "россия заявила": [55.7558, 37.6173, "Москва", "RU"],
    "россія заявила": [55.7558, 37.6173, "Москва", "RU"],
    "російська влада": [55.7558, 37.6173, "Москва", "RU"],
    "российские власти": [55.7558, 37.6173, "Москва", "RU"],
    "байден": [38.9072, -77.0369, "Вашингтон", "US"],
    "трамп": [38.9072, -77.0369, "Вашингтон", "US"],
    "белый дом": [38.9072, -77.0369, "Вашингтон", "US"],
    "білий дім": [38.9072, -77.0369, "Вашингтон", "US"],
    "госдеп": [38.9072, -77.0369, "Вашингтон", "US"],
    "сша заявили": [38.9072, -77.0369, "Вашингтон", "US"],
    "сша заявила": [38.9072, -77.0369, "Вашингтон", "US"],
    "варшав": [52.2297, 21.0122, "Варшава", "PL"],
    "польща заявила": [52.2297, 21.0122, "Варшава", "PL"],
    "польша заявила": [52.2297, 21.0122, "Варшава", "PL"],
    "польська влада": [52.2297, 21.0122, "Варшава", "PL"],
    "шольц": [52.5200, 13.4050, "Берлин", "DE"],
    "берлін заявив": [52.5200, 13.4050, "Берлин", "DE"],
    "берлин заявил": [52.5200, 13.4050, "Берлин", "DE"],
    "німеччина заявила": [52.5200, 13.4050, "Берлин", "DE"],
    "германия заявила": [52.5200, 13.4050, "Берлин", "DE"],
    "лондон заявил": [51.5074, -0.1278, "Лондон", "GB"],
    "британ": [51.5074, -0.1278, "Лондон", "GB"],
    "макрон": [48.8566, 2.3522, "Париж", "FR"],
    "париж заявил": [48.8566, 2.3522, "Париж", "FR"],
    "франція заявила": [48.8566, 2.3522, "Париж", "FR"],
    "пекін заявив": [39.9042, 116.4074, "Пекин", "CN"],
    "пекин заявил": [39.9042, 116.4074, "Пекин", "CN"],
    "китай заявил": [39.9042, 116.4074, "Пекин", "CN"],
    "эрдоган": [39.9334, 32.8597, "Анкара", "TR"],
    "анкара заявила": [39.9334, 32.8597, "Анкара", "TR"],
    "брюссель": [50.8503, 4.3517, "Брюссель", "BE"],
    "єврокомісія": [50.8503, 4.3517, "Брюссель", "BE"],
    "еврокомиссия": [50.8503, 4.3517, "Брюссель", "BE"],
}

POLITICAL_MARKERS = [
    "заявил", "заявила", "заявили", "заявив", "заявила", "заявили",
    "заява", "заяву", "заявления", "заяву",
    "предложил", "предложила", "предложили", "предложил", "запропонував",
    "сказал", "сказала", "сказали", "сообщил", "сообщила",
    "підкреслив", "подчеркнул", "зазначив", "отметил",
    "прокомментировал", "прокоментував",
    "обсуждает", "обсуждают", "обговорює",
    "планирует", "планируют", "планує",
    "визит", "візит", "встреча", "зустріч",
    "переговоры", "переговори", "саммит",
    "интервью", "інтерв'ю", "пресс-конференц",
    "призвал", "призвала", "призвали", "закликав",
    "отреагировал", "відреагував",
]

ABBREVIATIONS = {
    "мена", "mena", "сша", "оон", "нато", "ес", "eu", "вс", "пво", "рлс", "зрк",
    "бпла", "бпа", "ттх", "орб", "орг", "мто", "асу", "гпс", "гпр", "су", "мк",
    "пи", "пр", "рсзо", "опк", "кндр", "кнр", "рф", "уа", "usa", "nato", "un",
    "азия", "африка", "европа",
}

SUMMARY_WORDS = [
    "оперативная информация", "оперативна інформація",
    "оперативка", "брифинг", "брифінг",
    "за минувшие сутки", "за добу", "за прошедшие сутки", "протягом доби",
    "бойових зіткнень", "боевых столкновений",
    "итоги", "підсумки",
    "обстановка на фронте", "ситуация на фронте", "ситуація на фронті",
    "фронтовая сводка", "фронтове зведення",
    "збито/подавлено", "сбито/подавлено", "збито / подавлено",
    "хроника", "хроніка", "дронопорт", "дронопорти",
    "специальной военной операции", "спеціальної воєнної операції",
]

TRANSLIT_ALIASES = {
    "киев": [50.4501, 30.5234, "Киев", "UA"],
    "київ": [50.4501, 30.5234, "Киев", "UA"],
    "kyiv": [50.4501, 30.5234, "Киев", "UA"],
    "kiev": [50.4501, 30.5234, "Киев", "UA"],
    "харьков": [49.9935, 36.2304, "Харьков", "UA"],
    "харків": [49.9935, 36.2304, "Харьков", "UA"],
    "kharkiv": [49.9935, 36.2304, "Харьков", "UA"],
    "одесса": [46.4775, 30.7326, "Одесса", "UA"],
    "одеса": [46.4775, 30.7326, "Одесса", "UA"],
    "odesa": [46.4775, 30.7326, "Одесса", "UA"],
    "odessa": [46.4775, 30.7326, "Одесса", "UA"],
    "днепр": [48.4647, 35.0462, "Днепр", "UA"],
    "дніпро": [48.4647, 35.0462, "Днепр", "UA"],
    "dnipro": [48.4647, 35.0462, "Днепр", "UA"],
    "днепропетровск": [48.4647, 35.0462, "Днепр", "UA"],
    "дніпропетровськ": [48.4647, 35.0462, "Днепр", "UA"],
    "запорожье": [47.8388, 35.1396, "Запорожье", "UA"],
    "запоріжжя": [47.8388, 35.1396, "Запорожье", "UA"],
    "zaporizhzhia": [47.8388, 35.1396, "Запорожье", "UA"],
    "zaporizhia": [47.8388, 35.1396, "Запорожье", "UA"],
    "херсон": [46.6354, 32.6169, "Херсон", "UA"],
    "kherson": [46.6354, 32.6169, "Херсон", "UA"],
    "николаев": [46.9750, 31.9946, "Николаев", "UA"],
    "миколаїв": [46.9750, 31.9946, "Николаев", "UA"],
    "mykolaiv": [46.9750, 31.9946, "Николаев", "UA"],
    "nikolaev": [46.9750, 31.9946, "Николаев", "UA"],
    "донецк": [48.0159, 37.8029, "Донецк", "UA"],
    "донецьк": [48.0159, 37.8029, "Донецк", "UA"],
    "donetsk": [48.0159, 37.8029, "Донецк", "UA"],
    "луганск": [48.5740, 39.3078, "Луганск", "UA"],
    "луганськ": [48.5740, 39.3078, "Луганск", "UA"],
    "luhansk": [48.5740, 39.3078, "Луганск", "UA"],
    "lugansk": [48.5740, 39.3078, "Луганск", "UA"],
    "львов": [49.8397, 24.0297, "Львов", "UA"],
    "львів": [49.8397, 24.0297, "Львов", "UA"],
    "lviv": [49.8397, 24.0297, "Львов", "UA"],
    "сумы": [50.9077, 34.7981, "Сумы", "UA"],
    "суми": [50.9077, 34.7981, "Сумы", "UA"],
    "sumy": [50.9077, 34.7981, "Сумы", "UA"],
    "чернигов": [51.4982, 31.2893, "Чернигов", "UA"],
    "чернігів": [51.4982, 31.2893, "Чернигов", "UA"],
    "chernihiv": [51.4982, 31.2893, "Чернигов", "UA"],
    "полтава": [49.5883, 34.5514, "Полтава", "UA"],
    "poltava": [49.5883, 34.5514, "Полтава", "UA"],
    "винница": [49.2331, 28.4682, "Винница", "UA"],
    "вінниця": [49.2331, 28.4682, "Винница", "UA"],
    "vinnytsia": [49.2331, 28.4682, "Винница", "UA"],
    "житомир": [50.2547, 28.6587, "Житомир", "UA"],
    "zhytomyr": [50.2547, 28.6587, "Житомир", "UA"],
    "черкассы": [49.4444, 32.0598, "Черкассы", "UA"],
    "черкаси": [49.4444, 32.0598, "Черкассы", "UA"],
    "cherkasy": [49.4444, 32.0598, "Черкассы", "UA"],
    "ровно": [50.6199, 26.2516, "Ровно", "UA"],
    "рівне": [50.6199, 26.2516, "Ровно", "UA"],
    "rivne": [50.6199, 26.2516, "Ровно", "UA"],
    "луцк": [50.7472, 25.3254, "Луцк", "UA"],
    "луцьк": [50.7472, 25.3254, "Луцк", "UA"],
    "lutsk": [50.7472, 25.3254, "Луцк", "UA"],
    "ужгород": [48.6208, 22.2879, "Ужгород", "UA"],
    "uzhhorod": [48.6208, 22.2879, "Ужгород", "UA"],
    "тернополь": [49.5535, 25.5948, "Тернополь", "UA"],
    "тернопіль": [49.5535, 25.5948, "Тернополь", "UA"],
    "ternopil": [49.5535, 25.5948, "Тернополь", "UA"],
    "хмельницкий": [49.4229, 26.9871, "Хмельницкий", "UA"],
    "хмельницький": [49.4229, 26.9871, "Хмельницкий", "UA"],
    "ивано-франковск": [48.9226, 24.7111, "Ивано-Франковск", "UA"],
    "івано-франківськ": [48.9226, 24.7111, "Ивано-Франковск", "UA"],
    "черновцы": [48.2917, 25.9354, "Черновцы", "UA"],
    "чернівці": [48.2917, 25.9354, "Черновцы", "UA"],
    "кропивницкий": [48.5079, 32.2623, "Кропивницкий", "UA"],
    "кіровоград": [48.5079, 32.2623, "Кропивницкий", "UA"],
    "кривой рог": [47.9105, 33.3918, "Кривой Рог", "UA"],
    "кривий ріг": [47.9105, 33.3918, "Кривой Рог", "UA"],
    "мариуполь": [47.0951, 37.5413, "Мариуполь", "UA"],
    "маріуполь": [47.0951, 37.5413, "Мариуполь", "UA"],
    "mariupol": [47.0951, 37.5413, "Мариуполь", "UA"],
    "мелитополь": [46.8489, 35.3654, "Мелитополь", "UA"],
    "мелітополь": [46.8489, 35.3654, "Мелитополь", "UA"],
    "бердянск": [46.7554, 36.7886, "Бердянск", "UA"],
    "бердянськ": [46.7554, 36.7886, "Бердянск", "UA"],
    "бахмут": [48.5953, 37.9999, "Бахмут", "UA"],
    "bakhmut": [48.5953, 37.9999, "Бахмут", "UA"],
    "авдеевка": [48.1395, 37.7418, "Авдеевка", "UA"],
    "авдіївка": [48.1395, 37.7418, "Авдеевка", "UA"],
    "avdiivka": [48.1395, 37.7418, "Авдеевка", "UA"],
    "соледар": [48.6906, 38.0755, "Соледар", "UA"],
    "soledar": [48.6906, 38.0755, "Соледар", "UA"],
    "купянск": [49.7103, 37.6156, "Купянск", "UA"],
    "куп'янськ": [49.7103, 37.6156, "Купянск", "UA"],
    "kupiansk": [49.7103, 37.6156, "Купянск", "UA"],
    "изюм": [49.2080, 37.2757, "Изюм", "UA"],
    "ізюм": [49.2080, 37.2757, "Изюм", "UA"],
    "краматорск": [48.7389, 37.5848, "Краматорск", "UA"],
    "kramatorsk": [48.7389, 37.5848, "Краматорск", "UA"],
    "славянск": [48.8531, 37.6126, "Славянск", "UA"],
    "слов'янськ": [48.8531, 37.6126, "Славянск", "UA"],
    "константиновка": [48.5277, 37.7136, "Константиновка", "UA"],
    "костянтинівка": [48.5277, 37.7136, "Константиновка", "UA"],
    "покровск": [48.2811, 37.1764, "Покровск", "UA"],
    "покровськ": [48.2811, 37.1764, "Покровск", "UA"],
    "северодонецк": [48.9487, 38.4924, "Северодонецк", "UA"],
    "сіверськодонецьк": [48.9487, 38.4924, "Северодонецк", "UA"],
    "белая церковь": [49.7962, 30.1117, "Белая Церковь", "UA"],
    "біла церква": [49.7962, 30.1117, "Белая Церковь", "UA"],
    "москва": [55.7558, 37.6173, "Москва", "RU"],
    "moscow": [55.7558, 37.6173, "Москва", "RU"],
    "санкт-петербург": [59.9311, 30.3609, "Санкт-Петербург", "RU"],
    "питер": [59.9311, 30.3609, "Санкт-Петербург", "RU"],
    "спб": [59.9311, 30.3609, "Санкт-Петербург", "RU"],
    "белгород": [50.5952, 36.5873, "Белгород", "RU"],
    "belgorod": [50.5952, 36.5873, "Белгород", "RU"],
    "курск": [51.7304, 36.1926, "Курск", "RU"],
    "kursk": [51.7304, 36.1926, "Курск", "RU"],
    "брянск": [53.2435, 34.3639, "Брянск", "RU"],
    "bryansk": [53.2435, 34.3639, "Брянск", "RU"],
    "воронеж": [51.6720, 39.1843, "Воронеж", "RU"],
    "voronezh": [51.6720, 39.1843, "Воронеж", "RU"],
    "ростов-на-дону": [47.2225, 39.7188, "Ростов-на-Дону", "RU"],
    "ростов": [47.2225, 39.7188, "Ростов-на-Дону", "RU"],
    "rostov": [47.2225, 39.7188, "Ростов-на-Дону", "RU"],
    "краснодар": [45.0355, 38.9753, "Краснодар", "RU"],
    "krasnodar": [45.0355, 38.9753, "Краснодар", "RU"],
    "крым": [45.3453, 34.4997, "Крым", "RU"],
    "crimea": [45.3453, 34.4997, "Крым", "RU"],
    "севастополь": [44.6166, 33.5254, "Севастополь", "RU"],
    "sevastopol": [44.6166, 33.5254, "Севастополь", "RU"],
    "симферополь": [44.9521, 34.1024, "Симферополь", "RU"],
    "simferopol": [44.9521, 34.1024, "Симферополь", "RU"],
    "ульяновск": [54.3142, 48.4031, "Ульяновск", "RU"],
    "липецк": [52.6031, 39.5708, "Липецк", "RU"],
    "тамбов": [52.7212, 41.4523, "Тамбов", "RU"],
    "смоленск": [54.7826, 32.0453, "Смоленск", "RU"],
    "тверь": [56.8587, 35.9176, "Тверь", "RU"],
    "псков": [57.8194, 28.3318, "Псков", "RU"],
    "новгород": [58.5215, 31.2755, "Новгород", "RU"],
    "мурманск": [68.9585, 33.0827, "Мурманск", "RU"],
    "архангельск": [64.5393, 40.5182, "Архангельск", "RU"],
    "астрахань": [46.3497, 48.0408, "Астрахань", "RU"],
    "челябинск": [55.1644, 61.4368, "Челябинск", "RU"],
    "екатеринбург": [56.8389, 60.6057, "Екатеринбург", "RU"],
    "омск": [54.9885, 73.3242, "Омск", "RU"],
    "новосибирск": [55.0084, 82.9357, "Новосибирск", "RU"],
    "иркутск": [52.2871, 104.3051, "Иркутск", "RU"],
    "хабаровск": [48.4827, 135.0838, "Хабаровск", "RU"],
    "волгоград": [48.7080, 44.5133, "Волгоград", "RU"],
    "саратов": [51.5336, 46.0343, "Саратов", "RU"],
    "самара": [53.1959, 50.1061, "Самара", "RU"],
    "казань": [55.8304, 49.0661, "Казань", "RU"],
    "нижний новгород": [56.3269, 44.0059, "Нижний Новгород", "RU"],
    "тула": [54.1961, 37.6182, "Тула", "RU"],
    "калуга": [54.5138, 36.2612, "Калуга", "RU"],
    "рязань": [54.6269, 39.6916, "Рязань", "RU"],
    "пенза": [53.2007, 45.0046, "Пенза", "RU"],
    "оренбург": [51.7727, 55.0988, "Оренбург", "RU"],
    "тюмень": [57.1522, 65.5272, "Тюмень", "RU"],
    "кемерово": [55.3547, 86.0873, "Кемерово", "RU"],
    "ставрополь": [45.0428, 41.9734, "Ставрополь", "RU"],
    "владивосток": [43.1155, 131.8855, "Владивосток", "RU"],
}

STRONG_EVENT_WORDS = [
    "удар", "обстр", "взрыв", "вибух", "прилёт", "приліт",
    "бпла", "дрон", "ракет", "пво", "штурм",
    "уразили", "уражено", "поразили", "поражено",
    "бои", "бої", "бой", "бій", "боях",
    "наступлен", "наступ", "прорыв", "прорив",
    "атака", "атакувал", "атакуют", "атакували",
    "продвижен", "просуванн", "заняли", "зайняли",
    "освободил", "звільнили", "контроль над",
    "тревога", "тривога", "опасность", "небезпека",
    "попадание", "влучання", "детонация", "детонація",
    "strike", "struck", "attack", "attacked", "shelling", "shelled",
    "drone", "missile", "air defense", "air raid", "explosion",
    "destroyed", "damaged", "hit", "targeted", "launched",
    "offensive", "advance", "captured", "liberated", "repelled",
]

EVENT_PATTERNS = [
    r'удар\w*\s+(?:по|на|в)\s+', r'ударил\w*\s+(?:по|на|в)\s+',
    r'ударили\s+по\s+', r'під\s+ударом', r'под\s+ударом',
    r'под\s+атакой', r'під\s+атакою', r'подверг\w*\s+атаке',
    r'зазнав\w*\s+удар', r'обстрел\w*\s+', r'обстріл\w*\s+',
    r'обстрелял\w*\s+', r'обстрілял\w*\s+',
    r'взрыв\w*\s+(?:в|на|по)\s+', r'вибух\w*\s+(?:у|в|на)\s+',
    r'прилёт\w*\s+(?:в|по|на)\s+', r'приліт\w*\s+(?:в|у|по|на)\s+',
    r'атак\w*\s+(?:на|в|по)\s+', r'атакувал\w*\s+', r'атакуют\s+',
    r'уражено\s+(?:в|у|на)\s+', r'поражено\s+(?:в|на)\s+',
    r'уразили\s+', r'поразили\s+',
    r'бпла\s+(?:над|на|в|курс)', r'дрон\w*\s+(?:над|на|в|курс)',
    r'\bв\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}уражен\w*',
    r'\bв\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}поражен\w*',
    r'\bв\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}удар\w*',
    r'\bу\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}уражен\w*',
    r'\bу\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}влучан\w*',
    r'\bна\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}удар\w*',
    r'\bв\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}вибух\w*',
    r'\bв\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}взрыв\w*',
    r'\bв\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}прил[её]т\w*',
    r'\bу\s+[а-яёa-z\-]+\s+(?:\S+\s+){0,4}приліт\w*',
    r'в\s+районе\s+', r'у\s+районі\s+',
    r'на\s+подступах\s+к\s+', r'на\s+підступах\s+до\s+',
    r'штурм\w*\s+', r'бои\s+', r'бої\s+',
    r'продвижен\w*\s+', r'просуванн\w*\s+', r'наступлен\w*\s+',
    r'заняли\s+', r'зайняли\s+', r'освободил\w*\s+', r'звільнили\s+',
    r'strike\s+on\s+', r'struck\s+', r'attack\s+on\s+',
    r'shelling\s+of\s+', r'drone\s+attack\s+on\s+',
    r'missile\s+strike\s+on\s+',
]

SOURCE_VERBS = [
    r'атаковали\s+с', r'атакуют\s+с', r'атакували\s+з',
    r'запустили\s+с', r'запускают\s+с', r'запустили\s+з',
    r'вылетели\s+с', r'вылетают\s+с', r'вилетіли\s+з',
    r'прилетели\s+с', r'курс\s+с', r'курсом\s+с',
    r'с\s+территории', r'з\s+території',
    r'с\s+направления', r'з\s+напрямку',
    r'\w+ском\s+направлени', r'\w+скому\s+направлени',
    r'\w+ском\s+напрямку', r'\w+скому\s+напрямку',
]

CANCEL_WORDS = ["отбой", "отменена", "отменён", "отменен",
                "завершена", "завершён", "завершен",
                "прекращена", "прекращён", "прекращен",
                "окончена", "угроза миновала", "опасность миновала",
                "відбій", "скасована", "завершено"]

MILITARY_TERMS = ["рлс", "зрк", "с-300", "с-400", "с-500", "бук ", "панцирь",
                  "тор ", "тюльпан", "град ", "ураган", "смерч",
                  "искандер", "кинжал", "калибр", "шахед", "герань",
                  "ланцет", "точка-у", "тос-", "оса ", "стрела",
                  "шилка", "тунгуска", "радиолокацион", "комплекс",
                  "установк", "нпз", "завод", "підприємств",
                  "ошбр", "всу", "полк", "бригад", "батальон", "рота", "взвод",
                  "спутник", "магазин", "мастерск", "здании", "здание"]

STOP_SETTLEMENTS = {
    "безопасное", "красное", "мирное", "новое", "тихое", "ясное",
    "победа", "дружба", "правда", "восток", "запад", "север", "юг",
    "искра", "заря", "маяк", "свобода", "россия", "украина",
    "северный", "южный", "западный", "восточный", "центральное",
    "новый", "старый", "малый", "большой", "верхний", "нижний",
    "дальний", "ближний", "дальнее", "ближнее", "веселое", "весёлое",
    "радостное", "светлое", "теплое", "тёплое", "глубокое",
    "широкое", "высокое", "низкое", "голубое", "синее",
    "зорька", "звезда", "солнце", "луна", "небо",
    "граница", "граничное", "пограничное", "приморское",
    "лесное", "степное", "речное", "озерное", "горное",
    "зеленое", "зелёное", "белое", "черное", "чёрное",
    "терек", "бук", "тор", "оса", "стрела", "искандер", "кинжал",
    "калибр", "шахед", "герань", "ланцет", "панцирь", "тюльпан",
    "град", "ураган", "смерч", "тунгуска", "шилка", "с-300", "с-400",
    "точка", "печора", "акация", "гиацинт", "пион", "мена",
    "азов", "азовсталь", "азовск", "русский", "руський", "дронопорт",
    "игра", "игры", "игре", "игру", "игрой",
    "победа", "мир", "война", "бой", "сражение",
    "правда", "ложь", "свобода", "воля",
    "заря", "звезда", "солнце", "луна", "небо", "рассвет", "закат",
    "дружба", "любовь", "надежда", "вера",
    "ленин", "сталин", "революция",
    "молодость", "юность",
    "безопасное", "красное", "мирное", "новое", "тихое", "ясное",
    "слово", "фраза", "текст", "буква", "цифра",
    "дело", "работа", "жизнь", "смерть",
    "утро", "день", "ночь", "вечер",
    "дом", "город", "село", "деревня",
}

SETTLEMENTS_BY_NAME = {}


def is_summary(text):
    tl = text[:250].lower()
    for w in SUMMARY_WORDS:
        if w in tl:
            return True
    return False


def detect_political(text):
    tl = text.lower()
    for key, coords in SPEAKER_CAPITALS.items():
        if key in tl:
            return (coords[0], coords[1]), coords[2], coords[3]
    return None, None, None


def has_political_marker(text):
    tl = text.lower()
    for w in POLITICAL_MARKERS:
        if w in tl:
            return True
    return False


def load_settlements():
    global SETTLEMENTS_BY_NAME
    path = 'data/settlements.js'
    if not os.path.exists(path):
        print("  ⚠️ data/settlements.js не найден", file=sys.stderr)
        return
    print("Загружаю базу населённых пунктов...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    json_str = content.replace('window.SETTLEMENTS = ', '').rstrip(';').rstrip()
    data = json.loads(json_str)
    skipped = 0
    for s in data:
        name_low = s['name'].lower()
        if name_low in STOP_SETTLEMENTS or name_low in ABBREVIATIONS:
            skipped += 1
            continue
        SETTLEMENTS_BY_NAME.setdefault(name_low, []).append(
            (s['lat'], s['lng'], s['country'], s['name'], s.get('population', 0))
        )
    print(f"  Загружено {len(data)} записей, пропущено: {skipped}")


def fetch_channel(channel):
    url = f"https://t.me/s/{channel}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  Ошибка загрузки @{channel}: {e}", file=sys.stderr)
        return ""


def extract_media(block):
    """Извлекает URL фото и видео из HTML-блока поста."""
    photo_url = None
    video_url = None

    m = re.search(r"tgme_widget_message_photo_wrap[^>]*style=\"[^\"]*url\('([^']+)'\)", block)
    if not m:
        m = re.search(r"tgme_widget_message_photo[^>]*style=\"[^\"]*url\('([^']+)'\)", block)
    if m:
        photo_url = m.group(1)

    m = re.search(r'<video[^>]*src="([^"]+)"', block)
    if m:
        video_url = m.group(1)
    else:
        m = re.search(r"tgme_widget_message_video_thumb[^>]*style=\"[^\"]*url\('([^']+)'\)", block)
        if m:
            video_url = m.group(1)

    return photo_url, video_url


def extract_posts(html):
    posts = []
    blocks = re.split(r'<div class="tgme_widget_message_wrap[^"]*"', html)
    for block in blocks[1:]:
        date_match = re.search(r'<time datetime="([^"]+)"', block)
        date_str = date_match.group(1) if date_match else ""
        text_match = re.search(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*</div>',
            block, re.DOTALL
        )
        if not text_match:
            continue
        text = text_match.group(1)
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = unescape(text).strip()
        id_match = re.search(r'data-post="([^"]+)"', block)
        url = f"https://t.me/{id_match.group(1)}" if id_match else ""

        photo_url, video_url = extract_media(block)

        if len(text) > 20:
            posts.append({
                "text": text,
                "date": date_str,
                "url": url,
                "photo_url": photo_url,
                "video_url": video_url
            })
    return posts


def has_strong_word_near(text, phrase, window=250):
    tl = text.lower()
    idx = tl.find(phrase.lower())
    if idx < 0:
        return False
    full = tl[max(0, idx-window):idx+len(phrase)+window]
    for w in STRONG_EVENT_WORDS:
        if w in full:
            return True
    return False


def has_event_pattern_near(text, phrase, window=250):
    tl = text.lower()
    idx = tl.find(phrase.lower())
    if idx < 0:
        return False
    before = tl[max(0, idx-window):idx]
    after = tl[idx+len(phrase):idx+len(phrase)+window]
    full = before + " " + after
    for pat in EVENT_PATTERNS:
        if re.search(pat, full):
            return True
    return False


def has_source_verb_near(text, phrase, window=60):
    tl = text.lower()
    idx = tl.find(phrase.lower())
    if idx < 0:
        return False
    full = tl[max(0, idx-window):idx+len(phrase)+window]
    for pat in SOURCE_VERBS:
        if re.search(pat, full):
            return True
    return False


def is_military_term_context(text, phrase):
    tl = text.lower()
    idx = tl.find(phrase.lower())
    if idx < 0:
        return False
    before = tl[max(0, idx-30):idx]
    after = tl[idx+len(phrase):idx+len(phrase)+30]
    for term in MILITARY_TERMS:
        if term in before or term in after:
            return True
    if ('«' in before[-3:] or '“' in before[-3:]) and ('»' in after[:3] or '”' in after[:3]):
        return True
    return False


def find_alias(text, channel_country):
    tl = text.lower()
    had_alias = False
    for key in sorted(TRANSLIT_ALIASES.keys(), key=lambda k: -len(k)):
        if key not in tl:
            continue
        had_alias = True
        coords = TRANSLIT_ALIASES[key]
        alias_country = coords[3]

        if channel_country == alias_country:
            if has_source_verb_near(text, key, window=60):
                continue
            if not has_strong_word_near(text, key, window=250):
                continue
            if is_military_term_context(text, key):
                continue
            return (coords[0], coords[1]), coords[2], coords[3], True

        if has_source_verb_near(text, key, window=60):
            continue
        if not has_event_pattern_near(text, key, window=250):
            continue
        if is_military_term_context(text, key):
            continue
        return (coords[0], coords[1]), coords[2], coords[3], True
    return None, None, None, had_alias


def find_best_city(text, channel_country):
    if not SETTLEMENTS_BY_NAME:
        return None, None, None

    tl = text.lower()
    words = re.findall(r'[а-яёa-zа-їієґ0-9\-]+', tl)
    if not words:
        return None, None, None

    candidates = []
    N = len(words)

    for size in (3, 2, 1):
        for i in range(N - size + 1):
            phrase = ' '.join(words[i:i+size])
            if phrase not in SETTLEMENTS_BY_NAME:
                continue
            if phrase in ABBREVIATIONS:
                continue
            if is_military_term_context(text, phrase):
                continue

            coords_list = SETTLEMENTS_BY_NAME[phrase]

            if channel_country in ("UA", "RU"):
                filtered = [c for c in coords_list if c[2] == channel_country]
                if not filtered:
                    continue
                best = max(filtered, key=lambda x: x[4])
                is_own_country = True
            else:
                best = max(coords_list, key=lambda x: x[4])
                is_own_country = False

            lat, lng, country, orig, population = best

            if is_own_country:
                if has_source_verb_near(text, phrase, window=60):
                    continue
                if not has_strong_word_near(text, phrase, window=250):
                    continue
            else:
                if has_source_verb_near(text, phrase, window=60):
                    continue
                if not has_event_pattern_near(text, phrase, window=250):
                    continue

            pos_in_text = tl.find(phrase)
            if pos_in_text < 0:
                pos_in_text = 0

            score = 0
            if pos_in_text < 150:
                score += 20
            if population > 0:
                pop_bonus = math.log10(population) - 3
                score += max(0, pop_bonus) * 3
            score -= pos_in_text * 0.05

            candidates.append((score, orig, lat, lng, country))

    if not candidates:
        return None, None, None

    candidates.sort(key=lambda x: -x[0])
    best_score, best_name, best_lat, best_lng, best_country = candidates[0]
    return (best_lat, best_lng), best_name, best_country


def is_cancellation(text):
    tl = text.lower()
    has_cancel = any(c in tl for c in CANCEL_WORDS)
    if not has_cancel:
        return False
    return True


def classify_event(text):
    tl = text.lower()
    if is_cancellation(text):
        return None
    if any(w in tl for w in ["тревога", "тривога", "alert", "сирена",
                             "воздушная тревога", "повітряна тривога",
                             "опасность", "небезпека", "угроза", "загроза",
                             "air raid"]):
        return "Air Raid Alert"
    if any(w in tl for w in ["удар", "обстр", "взрыв", "вибух", "прилёт", "приліт",
                             "ракет", "пво", "уразили", "уражено", "поразили",
                             "поражено", "бпла", "дрон", "шахед",
                             "попадание", "влучання", "детонация", "детонація",
                             "strike", "struck", "shelling", "shelled",
                             "missile", "drone", "explosion", "hit"]):
        return "Military Strike"
    if any(w in tl for w in ["наступление", "наступ", "атака", "attack", "прорыв", "штурм",
                             "offensive", "advance"]):
        return "Military Offensive"
    if any(w in tl for w in ["бои", "battle", "fight", "бой", "бій", "боях", "позиции"]):
        return "Military Operation"
    return None


def make_dedup_key(ev):
    if ev.get("url"):
        return ev["url"]
    return ev["channel"] + "|" + ev.get("description", "")[:80]


def jitter_coords(lat, lng, radius_km):
    deg_lat_per_km = 1.0 / 111.0
    deg_lng_per_km = 1.0 / (111.0 * math.cos(math.radians(lat)) + 0.0001)
    dlat = random.uniform(-radius_km, radius_km) * deg_lat_per_km
    dlng = random.uniform(-radius_km, radius_km) * deg_lng_per_km
    return lat + dlat, lng + dlng


def radius_for_count(count):
    if count <= 3:
        return 1.5
    elif count <= 10:
        return 3.0
    elif count <= 20:
        return 5.0
    else:
        return 8.0


def main():
    load_settlements()

    raw_events = []
    seen_texts = set()
    seen_dedup = set()
    duplicates = 0
    stats = {}
    no_match = 0
    skipped_summary = 0
    political_count = 0

    for channel in CHANNELS:
        print(f"Парсим @{channel}...")
        html = fetch_channel(channel)
        if not html:
            stats[channel] = 0
            continue
        posts = extract_posts(html)
        print(f"  Найдено постов: {len(posts)}")
        matched = 0

        channel_country = CHANNEL_COUNTRY.get(channel, "OSINT")

        for post in posts:
            text = post["text"]
            key = text[:80]
            if key in seen_texts:
                continue
            seen_texts.add(key)

            pol_coords, pol_city, pol_country = detect_political(text)
            if pol_coords and has_political_marker(text):
                ev = {
                    "id": len(raw_events) + 1,
                    "url": post["url"] or f"https://t.me/s/{channel}",
                    "date": post["date"],
                    "event_type": "Political Development",
                    "location": pol_city,
                    "country": pol_country,
                    "lat": pol_coords[0],
                    "lng": pol_coords[1],
                    "confidence": "MEDIUM",
                    "description": text[:200],
                    "channel": channel,
                    "photo_url": post.get("photo_url"),
                    "video_url": post.get("video_url"),
                }
                dedup = make_dedup_key(ev)
                if dedup not in seen_dedup:
                    seen_dedup.add(dedup)
                    raw_events.append(ev)
                    matched += 1
                    political_count += 1
                continue

            if is_summary(text):
                skipped_summary += 1
                continue

            event_type = classify_event(text)
            if not event_type:
                continue

            coords, city, country, had_alias = find_alias(text, channel_country)

            if not coords and had_alias:
                no_match += 1
                continue

            if not coords:
                coords, city, country = find_best_city(text, channel_country)

            if not coords:
                no_match += 1
                continue

            matched += 1

            ev = {
                "id": len(raw_events) + 1,
                "url": post["url"] or f"https://t.me/s/{channel}",
                "date": post["date"],
                "event_type": event_type,
                "location": city,
                "country": country,
                "lat": coords[0],
                "lng": coords[1],
                "confidence": "MEDIUM",
                "description": text[:200],
                "channel": channel,
                "photo_url": post.get("photo_url"),
                "video_url": post.get("video_url"),
            }

            dedup = make_dedup_key(ev)
            if dedup in seen_dedup:
                duplicates += 1
                continue
            seen_dedup.add(dedup)

            raw_events.append(ev)

        stats[channel] = matched
        print(f"  Совпало: {matched}")
        time.sleep(1)

    coord_counter = Counter()
    for ev in raw_events:
        coord_key = (round(ev["lat"], 3), round(ev["lng"], 3))
        coord_counter[coord_key] += 1

    print(f"\n🔀 Применяю jitter к {len(raw_events)} событиям...")
    for ev in raw_events:
        coord_key = (round(ev["lat"], 3), round(ev["lng"], 3))
        count = coord_counter[coord_key]
        radius = radius_for_count(count)
        ev["lat"], ev["lng"] = jitter_coords(ev["lat"], ev["lng"], radius)

    output = "window.TG_DATA = " + json.dumps({"events": raw_events}, ensure_ascii=False) + ";"
    with open("data/telegram-events.js", "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n✅ Итого: {len(raw_events)} событий")
    print(f"   Из них политических: {political_count}")
    print(f"   Пропущено сводок: {skipped_summary}")
    print(f"   Отброшено дубликатов: {duplicates}")
    print(f"   Постов без совпадений по н.п.: {no_match}")

    print("\n📊 Статистика по каналам:")
    for ch, count in sorted(stats.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  @{ch}: {count}")

    print("\n📍 Топ-15 населённых пунктов:")
    city_counter = Counter(ev["location"] for ev in raw_events)
    for city, count in city_counter.most_common(15):
        print(f"  {city}: {count}")


if __name__ == "__main__":
    main()
