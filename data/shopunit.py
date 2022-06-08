import sqlalchemy
from flask_login import UserMixin
from .db_session import SqlAlchemyBase


class ShopUnit(SqlAlchemyBase, UserMixin):
    __tablename__ = 'shopunit'
    number = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    id = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    date = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    parentId = sqlalchemy.Column(sqlalchemy.String, nullable=True, default=None)
    type = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    price = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=None)
    full_cost = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)
    count = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)
    children = sqlalchemy.Column(sqlalchemy.String, nullable=True, default=None)
    history_id = sqlalchemy.Column(sqlalchemy.String, nullable=False)
