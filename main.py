# библиотека для бекенда
from flask import Flask, request, jsonify
# 2 класса для работы с базой данных
from data.shopunit import ShopUnit
from data.historyunit import HistoryUnit
# функция для работы с базой данных
from data import db_session
# библиотека для регулярных библиотек
import re
# библиотека для работы с временем и датой
from datetime import datetime

# настройка сервера
app = Flask(__name__)
app.config['SECRET_KEY'] = 'my special the best secret key'
# инициализация БД
db_session.global_init("db/shopunits.sqlite")


def recursion_add(recursion_add_id):
    """
    Вспомогательная функция для метода "/nodes/<string:id>", она рекурсивно
    возвращает элементы
    :param recursion_add_id: uuid элемента
    :return: dict
    """
    # открываем сессии для работы с БД
    session = db_session.create_session()
    # ищем по id в таблице ShopUnit объект
    root = session.query(ShopUnit).filter(ShopUnit.id == recursion_add_id).first()
    # словарь с ответом
    ans = {"id": recursion_add_id,
           "name": root.name,
           "date": root.date,
           "parentId": root.parentId,
           "type": root.type,
           "price": root.price,
           "children": root.children}
    # если категория мы выполняем дополнительные действия
    if root.type == "CATEGORY":
        # заменяем в словаре поле "children" на массив
        ans["children"] = []
        # в цикле проходимся по id детей
        for children_id in root.children.split(";"):
            # запускаем такую же функцию для рекурсивного поиска объектов
            to_add = recursion_add(children_id)
            # добавляем объект в поле "children" в словарь с ответом
            ans["children"].append(to_add)
    # закрываем сессию работы с БД
    session.close()
    # возвращаем ответ
    return ans


def recursion_del(recursion_del_id):
    """
    Вспомогательная функция для удаления вложенных элементов(например товары
    в категории)
    :param recursion_del_id: uuid элемента
    """
    # открываем сессии для работы с БД
    session = db_session.create_session()
    # ищем по id в таблице ShopUnit объект
    to_delete = session.query(ShopUnit).filter(ShopUnit.id == recursion_del_id).first()
    # если у объекта есть дети, то мы их удаляем
    if to_delete.children:
        # в цикле проходимся по id детей
        for item_id in to_delete.children.split(";"):
            # рекурсивно удаляем их
            recursion_del(item_id)
    # в цикле проходимся по id записей истории изменений объекта
    for statistic_id in to_delete.history_id.split(";"):
        # ищем по id в таблице HistoryUnit объект
        statistic_to_delete = session.query(HistoryUnit).filter(HistoryUnit.id == statistic_id).first()
        # удаляем его из БД
        session.delete(statistic_to_delete)
    # удаляем изначальный объект
    session.delete(to_delete)
    # сохраняем состояние БД
    session.commit()
    # закрываем сессию
    session.close()


def seconds_time(date):
    """
    Функция для улучшения читаемости и уменьшения кода
    :param date: class timedelta
    :return:
    """
    # переводим разницу во времени из timedelta в секунды
    return date.days * 24 * 60 * 60 + date.seconds


def update_time(item, date):
    """
    Рекурсивная функция, которая вызывается при добавлении/изменении нового
    товара/категории. Она обновляет всем родителям время и сумму если это
    возможно.
    :param item: class ShopUnit
    :param date: дата для обновления
    """
    # открываем сессии для работы с БД
    session = db_session.create_session()
    # ищем по item.parentId в таблице ShopUnit предка для item
    parent = session.query(ShopUnit).filter(ShopUnit.id == item.parentId).first()
    # обновляем для него дату
    parent.date = date
    # объявляем 2 переменных для перерасчета средней стоимости категории
    full_cost, count = 0, 0
    # проходимся по id детей
    for child_id in parent.children.split(";"):
        # ищем по id в таблице ShopUnit ребенка
        child = session.query(ShopUnit).filter(ShopUnit.id == child_id).first()
        # добавляем к полной стоимости родителя полную стоимость ребенка
        full_cost += child.full_cost
        # добавляем к количеству товаров родителя их количество у ребенка
        count += child.count
    # перерасчитываем стоимость родителя
    parent.price = full_cost // count if full_cost > 0 else None
    # обновляем полную стоимость родителя
    parent.full_cost = full_cost
    # обновляем количество товаров
    parent.count = count
    # сохраняем состояние БД
    session.commit()
    # если у родителя тоже есть родитель
    if parent.parentId is not None:
        # сохраняем в переменную родителя, чтобы можно было закрыть сессию и вернуть
        # рекурсивно эту функцию с родителем, не занимаю лишнюю память
        to_send = parent
        # закрываем сессию
        session.close()
        # возвращаем рекурсивно эту функцию с родителем и датой для обновления
        return update_time(to_send, date)
    # закрываем сессию
    session.close()


def all_categories(item):
    """
    Рекурсивная функция, которая возвращает всех родителей элемента
    :param item: class ShopUnit
    :return: list
    """
    # если у элемента есть родитель
    if item.parentId:
        # открываем сессию для работы с БД
        session = db_session.create_session()
        # ищем по item.id в таблице ShopUnit родителя
        parent = session.query(ShopUnit).filter(ShopUnit.id == item.parentId).first()
        # закрываем сессию
        session.close()
        # возвращаем список с id родителя и рекурсивно вызываем функцию для поиска
        # следующих id родителей
        return [item.parentId] + all_categories(parent)
    # возвращаем пустой массив, так как родителей больше нет
    return []


def recursion_update(item):
    """
    Рекурсивная функция, которая пересчитывает цену для родителя после удаления
    элементов и сохраняет историю.
    :param item: class ShopUnit
    """
    # открываем сессию для работы с БД
    session = db_session.create_session()
    # объявляем переменные для перерасчета стоимости
    full_cost, count = 0, 0
    # проходимся по id детей
    for child_id in item.children.split(";"):
        # ищем по id в таблице ShopUnit ребенка
        child = session.query(ShopUnit).filter(ShopUnit.id == child_id).first()
        # добавляем к полной стоимости родителя полную стоимость ребенка
        full_cost += child.full_cost
        # добавляем к количеству товаров родителя количество товаров ребенка
        count += child.count
    # обновляем полную стоимость
    item.full_cost = full_cost
    # обновляем количество товаров
    item.count = count
    # обновляем цену
    item.price = item.full_cost // item.count if item.full_cost > 0 else None
    # создаем массив с id записей статистики
    history = item.history_id.split(";")
    # если цена не совпадает с ценой последней записи, то мы создаем новую
    if str(item.price) != str(session.query(HistoryUnit).filter(HistoryUnit.id == int(history[-1])).first().price):
        # создание объекта статистики
        history_unit = HistoryUnit()
        # указание имени
        history_unit.name = item.name
        # указание даты
        history_unit.date = item.date
        # указание родителя
        history_unit.parentId = item.parentId
        # указание цены объекта
        history_unit.price = item.price
        # добавление к объекту в историю изменений id новой записи
        item.history_id = ";".join(history + [str(session.query(HistoryUnit).all()[-1].id + 1)])
        # добавляем в БД новую запись со статистикой
        session.add(history_unit)
    # сохраняем состояние сессии
    session.commit()
    # если есть родитель, возвращаем рекурсивно эту функцию
    if item.parentId:
        # ищем предка по id в таблице ShopUnit
        parent = session.query(ShopUnit).filter(ShopUnit.id == item.parentId).first()
        # закрываем сессию
        session.close()
        # возвращаем рекурсивно эту функцию с предком
        return recursion_update(parent)
    # закрываем сессию
    session.close()


# он не нужен по факту
@app.route('/', methods=['GET', 'POST'])
def run():
    return 0, 404


@app.route('/imports', methods=['GET', 'POST'])
def imports():
    """
    Добавление/изменение товаров/категорий. Принимает на вход json с items и
    updateDate
    param items: dict
    param updateDate: str
    """
    # открываем сессию для работы с БД
    session = db_session.create_session()
    # получаем из json дату
    updateDate = request.json.get("updateDate")
    # получаем из json элементы для добавления/обновления
    items = request.json.get("items")
    # создаем множество категорий, которые нужно будет обновить
    categories = set()
    # проходимся по элементам
    for item in items:
        # пытаемся найти объект по id в таблице ShopUnit
        shopUnit = session.query(ShopUnit).filter(ShopUnit.id == item.get("id")).first()
        # флаг новый элемент или нет
        flag_add = False
        # если мы не нашли объект
        if shopUnit is None:
            # создаем новый объект
            shopUnit = ShopUnit()
            # ставим флаг, что новый элемент
            flag_add = True
        # перебираем параметры, которые есть в элементе
        for param in item.keys():
            # если параметр это id, то обновляем его
            if param == "id":
                shopUnit.id = item.get("id")
            # если параметр это name, то обновляем его
            elif param == "name":
                shopUnit.name = item.get("name")
            # если параметр это parentId, то обновляем его
            elif param == "parentId":
                shopUnit.parentId = item.get("parentId")
            # если параметр это type, то обновляем его
            elif param == "type":
                shopUnit.type = item.get("type")
            # если параметр это price, то обновляем её
            elif param == "price":
                shopUnit.price = int(item.get("price"))
        # если тип объекта категория, то мы поле дети делаем пустым
        if shopUnit.type == "CATEGORY":
            shopUnit.children = ""
        # иначе ставим количество товаров 1 и полную цену, равную цене товара
        else:
            shopUnit.count = 1
            shopUnit.full_cost = shopUnit.price
        # обновляем дату
        shopUnit.date = updateDate
        # ищем предка по parentId в таблице ShopUnit
        parent = session.query(ShopUnit).filter(ShopUnit.id == item.get("parentId")).first()
        # если он есть, то добавляем ему объект в ребенка
        if parent:
            parent.children = ";".join((parent.children.split(";") if len(parent.children) > 0 else []) + [shopUnit.id])
        # если новый объект
        if flag_add:
            # создаем новую запись статистики
            history_unit = HistoryUnit()
            # указываем имя
            history_unit.name = shopUnit.name
            # указываем дату
            history_unit.date = shopUnit.date
            # указываем id предка
            history_unit.parentId = shopUnit.parentId
            # указываем цену
            history_unit.price = shopUnit.price
            # добавляем новому объекту в историю id новой записи статистики,
            # равный id последней записи + 1
            if len(session.query(HistoryUnit).all()) >= 1:
                shopUnit.history_id = f"{session.query(HistoryUnit).all()[-1].id + 1}"
            # если записей нет, то id будет 1
            else:
                shopUnit.history_id = f"{1}"
            # добавляем в БД новый объект
            session.add(shopUnit)
            # добавляем в БД запись статистики
            session.add(history_unit)
        # если объект не новый
        else:
            # создаем новую запись статистики
            history_unit = HistoryUnit()
            # указываем имя
            history_unit.name = shopUnit.name
            # указываем дату
            history_unit.date = shopUnit.date
            # указываем id предка
            history_unit.parentId = shopUnit.parentId
            # указываем цену
            history_unit.price = shopUnit.price
            # добавляем в историю обновлений id записи статистики
            shopUnit.history_id = ";".join(
                shopUnit.history_id.split(";") + [str(session.query(HistoryUnit).all()[-1].id + 1)])
            # добавляем запись статистики в БД
            session.add(history_unit)
        # сохраняем состояние БД
        session.commit()
        # если есть предок
        if shopUnit.parentId is not None:
            # проходимся по всем полученным предкам данного объекта
            for category in all_categories(shopUnit):
                # если этот предок уже есть в множестве, то мы останавливаем цикл
                # потому что это значит, что и остальные есть
                if category in categories:
                    break
                # добавляем предка в множество
                categories.add(category)
            # запускаем функцию обновления времени и цен
            update_time(shopUnit, updateDate)
    # проходимся по всем id категорий для обновления
    for category_id in categories:
        # ищем категорию по id в таблице ShopUnit
        category = session.query(ShopUnit).filter(ShopUnit.id == category_id).first()
        # создаем новую запись статистики
        history_unit = HistoryUnit()
        # указываем имя
        history_unit.name = category.name
        # указываем дату
        history_unit.date = category.date
        # указываем id родителя
        history_unit.parentId = category.parentId
        # указываем цену
        history_unit.price = category.price
        # добавляем в историю id статистики
        category.history_id = ";".join(
            category.history_id.split(";") + [str(session.query(HistoryUnit).all()[-1].id + 1)])
        # добавим запись статистики в БД
        session.add(history_unit)
        # сохраняем состояние БД
        session.commit()
    # сохраняем состояние БД
    session.commit()
    # закрываем сессию
    session.close()
    return "ok", 200


@app.route('/nodes/<string:nodes_id>', methods=['GET', 'POST'])
def nodes(nodes_id):
    """
    Метод для получения информации об элементе по идентификатору
    :param nodes_id: uuid элемента
    :return: dict
    """
    # поиск по регулярному выражению
    reg_ans = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", nodes_id)
    # если ничего нет, то id не совпадает с шаблоном
    if reg_ans is None:
        return "Validation Failed", 400
    # создание сессии для работы с БД
    session = db_session.create_session()
    # поиск начальной категории/товара
    root = session.query(ShopUnit).filter(ShopUnit.id == nodes_id).first()
    # если не нашли начальную категорию/товар
    if root is None:
        return "Item not found", 404
    # ответ
    ans = {"id": nodes_id,
           "name": root.name,
           "date": root.date,
           "parentId": root.parentId,
           "type": root.type,
           "price": root.price,
           "children": root.children}
    # если начальный объект это категория
    if root.type == "CATEGORY":
        # заменяем поле детей на массив
        ans["children"] = []
        # проходимся по массиву id детей
        for nodes_id in root.children.split(";"):
            # добавляем в поле детей информацию о них
            ans["children"].append(recursion_add(nodes_id))
    # закрываем сессию
    session.close()
    # возвращаем ответ
    return ans, 200


@app.route('/sales', methods=['GET', 'POST'])
def sales():
    """
    Получение скидок за последние 24 часа от введенной даты
    param date: str
    :return: list
    """
    # получение даты из запроса
    date = request.args.get("date", default="228", type=str)
    # поиск регулярным выражением по 2 шаблонам(потому что я так и не понял,
    # как должна выглядеть дата)
    reg_ans = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", date)
    reg_ans1 = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d*Z", date)
    # превращаем дату в class datetime
    date = datetime.fromisoformat(date[:-1])
    # если дата не подходит к двум шаблонам, то возвращаем ошибку
    if reg_ans is None and reg_ans1 is None:
        return "Validation Failed", 400
    # создаем массив с ответом
    ans = []
    # создаем сессию для работы с БД
    session = db_session.create_session()
    # перебираем все существующие объекты в таблице ShopUnit
    for item in session.query(ShopUnit).all():
        # если тип объекта "категория", то пропускаем
        if item.type == "CATEGORY":
            continue
        # записываем дату элемента в переменную
        item_date = date.fromisoformat(item.date[:-1])
        # если разница во времени меньше 24 часов, то мы добавляем
        # в массив словарь с ответом
        if 0 <= seconds_time(date - item_date) <= 60 * 60 * 24:
            ans.append({"id": item.id,
                        "name": item.name,
                        "date": item.date,
                        "parentId": item.parentId,
                        "price": item.price,
                        "type": item.type})
    # закрываем сессию для работы с БД
    session.close()
    # отправляем массив с ответом
    return jsonify(ans), 200


@app.route('/node/<string:statistic_id>/statistic', methods=['GET', 'POST'])
def node(statistic_id):
    """
    Получение статистики по элементу в промежутке времени
    :param statistic_id: uuid элемента
    :return: list
    """
    # берем дату начала из запроса
    date_start = request.args.get("dateStart", default="228", type=str)
    # берем дату конца из запроса
    date_end = request.args.get("dateEnd", default="228", type=str)
    # регулярные выражения для проверки по шаблону id, date_start, date_end
    reg_ans_id = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", statistic_id)
    reg_ans_date_start = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", date_start)
    reg_ans_date_start1 = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d*Z", date_start)
    reg_ans_date_end = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", date_end)
    reg_ans_date_end1 = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d*Z", date_end)
    # если хоть что-то не подходит
    if reg_ans_id is None and \
            reg_ans_date_start is None and \
            reg_ans_date_start1 is None and \
            reg_ans_date_end is None and \
            reg_ans_date_end1 is None:
        return "Validation Failed", 400
    # перевод date_start в class datetime
    date_start = datetime.fromisoformat(date_start[:-1])
    # перевод date_end в class datetime
    date_end = datetime.fromisoformat(date_end[:-1])
    # создание сессии для работы с БД
    session = db_session.create_session()
    # ищем объект для статистики по id в таблице ShopUnit
    unit_to_statistic = session.query(ShopUnit).filter(ShopUnit.id == statistic_id).first()
    # если не нашли, то отправляем
    if unit_to_statistic is None:
        return "Item not found", 404
    # выбираем все записи статистики
    all_statistic = session.query(HistoryUnit).all()
    # преобразуем поле с индексами статистики в массив
    unit_statistic_items = list(map(int, unit_to_statistic.history_id.split(";")))
    # создаем переменную для массива
    ans = []
    # проходимся по всем записям статистики
    for statistic_item in all_statistic:
        # проверяем есть ли id элемента статистики в массиве с id статистики
        if statistic_item.id in unit_statistic_items:
            # преобразуем поле даты в класс datetime
            statistic_item_date = datetime.fromisoformat(statistic_item.date[:-1])
            # если разница во времени с начальной датой больше 0 и разница во
            # времени с датой конца больше 0(от даты конца отнимаю дату
            # статистики, поэтому разница больше 0), то добавляем ответ
            if seconds_time(statistic_item_date - date_start) >= 0 and \
                    seconds_time(date_end - statistic_item_date) >= 0:
                ans.append({
                    "id": unit_to_statistic.id,
                    "name": statistic_item.name,
                    "date": statistic_item.date,
                    "parentId": unit_to_statistic.parentId,
                    "price": statistic_item.price,
                    "type": unit_to_statistic.type
                })
    # отправляем ответ
    return jsonify(ans)


@app.route('/delete/<string:delete_id>', methods=['GET', 'POST', 'DELETE'])
def delete(delete_id):
    """
    Удаление элемента и всех его дочерних элементов с изменением цены родителей.
    :param delete_id: uuid элемента
    """
    # проверяем id на соответствие с шаблоном
    reg_ans = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", delete_id)
    # если не подошел, то отправляем ошибку
    if reg_ans is None:
        return "Validation Failed", 400
    # создаем сессию для работы с БД
    session = db_session.create_session()
    # ищем по id объект для удаления в таблице ShopUnit
    to_delete = session.query(ShopUnit).filter(ShopUnit.id == delete_id).first()
    # если не нашли, то отправляем ошибку
    if to_delete is None:
        return "Item not found", 404
    # если у объекта для удаления есть дети, то мы проходимся по ним и запускаем
    # рекурсивную функцию удаления
    if to_delete.children:
        for item_id in to_delete.children.split(";"):
            recursion_del(item_id)
    # если у объекта для удаления есть родитель, то удаляем из его детей данный объект
    if to_delete.parentId:
        # ищем по id родителя в таблице ShopUnit
        parent = session.query(ShopUnit).filter(ShopUnit.id == to_delete.parentId).first()
        # поле с детьми преобразуем в массив
        children = parent.children.split(";")
        # удаляем из него наш объект
        children.pop(children.index(to_delete.id))
        # обновляем родителя поле детей
        parent.children = ";".join(children)
        # сохраняем состояние БД
        session.commit()
        # запускаем рекурсивную функцию обновления цены
        recursion_update(parent)
    # перебираем id статистики из истории
    for statistic_id in to_delete.history_id.split(";"):
        # находим запись статистики по id в таблице HistoryUnit
        statistic_to_delete = session.query(HistoryUnit).filter(HistoryUnit.id == statistic_id).first()
        # удаляем из БД
        session.delete(statistic_to_delete)
    # удаляем из БД наш начальный объект
    session.delete(to_delete)
    # сохраняем состояние БД
    session.commit()
    # закрываем сессию для работы м БД
    session.close()
    return "ok", 200


def main():
    """
    Стартовая функция, запускает сервер на хосте 0.0.0.0 и порту 8000
    """
    # # для запуска на heroku
    # app.run(port=int(os.environ.get("PORT")), host='0.0.0.0')
    # запуск на хосте 0.0.0.0 и порте 8000
    # app.run(port=8000, host="0.0.0.0")
    # # запуск локального сервера
    app.run()


if __name__ == '__main__':
    # запуск бекенда
    main()
