from flask import Flask, request, jsonify
from data.shopunit import ShopUnit
from data.historyunit import HistoryUnit
from data import db_session
import re
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my special the best secret key'
db_session.global_init("db/shopunits.sqlite")


def recursion_add(id):
    session = db_session.create_session()
    root = session.query(ShopUnit).filter(ShopUnit.id == id).first()
    ans = {"id": id,
           "name": root.name,
           "date": root.date,
           "parentId": root.parentId,
           "type": root.type,
           "price": root.price,
           "children": root.children}
    if root.type == "CATEGORY":
        ans["children"] = []
        for id in root.children.split(";"):
            to_add = recursion_add(id)
            ans["children"].append(to_add)
    session.close()
    return ans


def recursion_del(id):
    session = db_session.create_session()
    to_delete = session.query(ShopUnit).filter(ShopUnit.id == id).first()
    if to_delete.children:
        for item_id in to_delete.children.split(";"):
            recursion_del(item_id)
    for statistic_id in to_delete.history_id.split(";"):
        statistic_to_delete = session.query(HistoryUnit).filter(HistoryUnit.id == statistic_id).first()
        session.delete(statistic_to_delete)
    session.delete(to_delete)
    session.commit()
    session.close()


def seconds_time(date):
    return date.days * 24 * 60 * 60 + date.seconds


def update_time(item, date):
    session = db_session.create_session()
    parent = session.query(ShopUnit).filter(ShopUnit.id == item.parentId).first()
    parent.date = date
    full_cost = 0
    count = 0
    if parent.children:
        for child_id in parent.children.split(";"):
            child = session.query(ShopUnit).filter(ShopUnit.id == child_id).first()
            full_cost += child.full_cost
            count += child.count
    parent.price = full_cost // count if full_cost > 0 else None
    parent.full_cost = full_cost
    parent.count = count
    session.commit()
    if parent.parentId is not None:
        to_send = parent
        session.close()
        return update_time(to_send, date)


def all_categories(item):
    if item.parentId:
        session = db_session.create_session()
        parent = session.query(ShopUnit).filter(ShopUnit.id == item.parentId).first()
        session.close()
        return [item.parentId] + all_categories(parent)
    return []


def recursion_update(item):
    session = db_session.create_session()
    full_cost, count = 0, 0
    for child_id in item.children.split(";"):
        child = session.query(ShopUnit).filter(ShopUnit.id == child_id).first()
        full_cost += child.full_cost
        count += child.count
    item.full_cost = full_cost
    item.count = count
    item.price = item.full_cost // item.count if item.full_cost > 0 else None
    history = item.history_id.split(";")
    if str(item.price) != str(session.query(HistoryUnit).filter(HistoryUnit.id == int(history[-1])).first().price):
        history_unit = HistoryUnit()
        history_unit.name = item.name
        history_unit.date = item.date
        history_unit.parentId = item.parentId
        history_unit.price = item.price
        item.history_id = ";".join(history + [str(session.query(HistoryUnit).all()[-1].id + 1)])
        session.add(history_unit)
    session.commit()
    if item.parentId:
        parent = session.query(ShopUnit).filter(ShopUnit.id == item.parentId).first()
        session.close()
        return recursion_update(parent)
    session.close()


@app.route('/', methods=['GET', 'POST'])
def run():
    return 0


@app.route('/imports', methods=['GET', 'POST'])
def imports():
    session = db_session.create_session()
    updateDate = request.json.get("updateDate")
    items = request.json.get("items")
    categories = set()
    for item in items:
        shopUnit = session.query(ShopUnit).filter(ShopUnit.id == item.get("id")).first()
        flag_add = False
        if shopUnit is None:
            shopUnit = ShopUnit()
            flag_add = True
        for param in item.keys():
            if param == "id":
                shopUnit.id = item.get("id")
            elif param == "name":
                shopUnit.name = item.get("name")
            elif param == "parentId":
                shopUnit.parentId = item.get("parentId")
            elif param == "type":
                shopUnit.type = item.get("type")
            elif param == "price":
                shopUnit.price = int(item.get("price"))
        if shopUnit.type == "CATEGORY":
            shopUnit.children = ""
        else:
            shopUnit.count = 1
            shopUnit.full_cost = shopUnit.price
        shopUnit.date = updateDate
        parent = session.query(ShopUnit).filter(ShopUnit.id == item.get("parentId")).first()
        if parent:
            parent.children = ";".join((parent.children.split(";") if len(parent.children) > 0 else []) + [shopUnit.id])
        if flag_add:
            history_unit = HistoryUnit()
            history_unit.name = shopUnit.name
            history_unit.date = shopUnit.date
            history_unit.parentId = shopUnit.parentId
            history_unit.price = shopUnit.price
            try:
                shopUnit.history_id = f"{session.query(HistoryUnit).all()[-1].id + 1}"
            except Exception:
                shopUnit.history_id = f"{1}"
            session.add(shopUnit)
            session.add(history_unit)
        elif shopUnit.price:
            history_unit = HistoryUnit()
            history_unit.name = shopUnit.name
            history_unit.date = shopUnit.date
            history_unit.parentId = shopUnit.parentId
            history_unit.price = shopUnit.price
            shopUnit.history_id = ";".join(shopUnit.history_id.split(";") + [str(session.query(HistoryUnit).all()[-1].id + 1)])
            session.add(history_unit)
        session.commit()
        if shopUnit.parentId is not None:
            for category in all_categories(shopUnit):
                if category in categories:
                    break
                categories.add(category)
            update_time(shopUnit, updateDate)
    for category_id in categories:
        category = session.query(ShopUnit).filter(ShopUnit.id == category_id).first()
        history_unit = HistoryUnit()
        history_unit.name = category.name
        history_unit.date = category.date
        history_unit.parentId = category.parentId
        history_unit.price = category.price
        category.history_id = ";".join(category.history_id.split(";") + [str(session.query(HistoryUnit).all()[-1].id + 1)])
        session.add(history_unit)
        session.commit()
    session.commit()
    session.close()
    return "ok", 200


@app.route('/nodes/<string:id>', methods=['GET', 'POST'])
def nodes(id):
    reg_ans = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", id)
    if reg_ans is None:
        return "Validation Failed", 400
    session = db_session.create_session()
    root = session.query(ShopUnit).filter(ShopUnit.id == id).first()
    if root is None:
        return "Item not found", 404
    ans = {"id": id,
           "name": root.name,
           "date": root.date,
           "parentId": root.parentId,
           "type": root.type,
           "price": root.price,
           "children": root.children}
    if root.type == "CATEGORY":
        ans["children"] = []
        for id in root.children.split(";"):
            to_add = recursion_add(id)
            ans["children"].append(to_add)
    session.close()
    return ans, 200


@app.route('/sales', methods=['GET', 'POST'])
def sales():
    date = request.args.get("date", default="228", type=str)
    reg_ans = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", date)
    reg_ans1 = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d*Z", date)
    date = datetime.fromisoformat(date[:-1])
    if reg_ans is None and reg_ans1 is None:
        return "Validation Failed", 400
    ans = []
    session = db_session.create_session()
    for item in session.query(ShopUnit).all():
        if item.type == "CATEGORY":
            continue
        item_date = date.fromisoformat(item.date[:-1])
        if 0 <= seconds_time(date - item_date) <= 60 * 60 * 24:
            ans.append({"id": item.id,
                        "name": item.name,
                        "date": item.date,
                        "parentId": item.parentId,
                        "price": item.price,
                        "type": item.type})
    session.close()
    return jsonify(ans), 200


@app.route('/node/<string:id>/statistic', methods=['GET', 'POST'])
def node(id):
    date_start = request.args.get("dateStart", default="228", type=str)
    date_end = request.args.get("dateEnd", default="228", type=str)
    reg_ans_id = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", id)
    reg_ans_date_start = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", date_start)
    reg_ans_date_start1 = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d*Z", date_start)
    reg_ans_date_end = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", date_end)
    reg_ans_date_end1 = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d*Z", date_end)
    if reg_ans_id is None and \
            reg_ans_date_start is None and \
            reg_ans_date_start1 is None and \
            reg_ans_date_end is None and \
            reg_ans_date_end1 is None:
        return "Validation Failed", 400
    date_start = datetime.fromisoformat(date_start[:-1])
    date_end = datetime.fromisoformat(date_end[:-1])
    session = db_session.create_session()
    unit_to_statistic = session.query(ShopUnit).filter(ShopUnit.id == id).first()
    if unit_to_statistic is None:
        return "Item not found", 404
    all_statistic = session.query(HistoryUnit).all()
    unit_statistic_items = list(map(int, unit_to_statistic.history_id.split(";")))
    ans = []
    for statistic_item in all_statistic:
        if statistic_item.id in unit_statistic_items:
            statistic_item_date = datetime.fromisoformat(statistic_item.date[:-1])
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
    return jsonify(ans)


@app.route('/delete/<string:id>', methods=['GET', 'POST', 'DELETE'])
def delete(id):
    reg_ans = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", id)
    if reg_ans is None:
        return "Validation Failed", 400
    session = db_session.create_session()
    to_delete = session.query(ShopUnit).filter(ShopUnit.id == id).first()
    if to_delete is None:
        return "Item not found", 404
    if to_delete.children:
        for item_id in to_delete.children.split(";"):
            recursion_del(item_id)
    if to_delete.parentId:
        parent = session.query(ShopUnit).filter(ShopUnit.id == to_delete.parentId).first()
        children = parent.children.split(";")
        children.pop(children.index(to_delete.id))
        parent.children = ";".join(children)
        session.commit()
        recursion_update(parent)
    for statistic_id in to_delete.history_id.split(";"):
        statistic_to_delete = session.query(HistoryUnit).filter(HistoryUnit.id == statistic_id).first()
        session.delete(statistic_to_delete)
    session.delete(to_delete)
    session.commit()
    session.close()
    return "ok", 200


def main():
    # app.run(port=int(os.environ.get("PORT")), host='0.0.0.0')
    app.run(port=8000, host="0.0.0.0")
    # app.run()


if __name__ == '__main__':
    # task = threading.Thread(target=main)
    # task.start()
    main()
