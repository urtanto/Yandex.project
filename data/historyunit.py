import sqlalchemy
from flask_login import UserMixin
from .db_session import SqlAlchemyBase


class HistoryUnit(SqlAlchemyBase, UserMixin):
    __tablename__ = 'historyunit'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    date = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    parentId = sqlalchemy.Column(sqlalchemy.String, nullable=True, default=None)
    price = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=None)
