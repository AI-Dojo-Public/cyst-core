from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, MappedAsDataclass, Session, relationship
from typing import Dict, List

from cyst.api.environment.data_model import ActionModel
from cyst.api.environment.stores import DataStore, DataStoreDescription
from cyst.api.environment.message import Status


class Base(DeclarativeBase):
    pass


class DBAction(Base):
    __tablename__ = "action"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column()
    run_id: Mapped[str] = mapped_column()
    action_id: Mapped[str] = mapped_column()
    caller_id: Mapped[str] = mapped_column()
    src_ip: Mapped[str] = mapped_column()
    dst_ip: Mapped[str] = mapped_column()
    dst_service: Mapped[str] = mapped_column()
    parameters: Mapped[List['DBActionParameter']] = relationship("DBActionParameter",
                                                                 back_populates="action",
                                                                 cascade="all, delete")
    status_origin: Mapped[str] = mapped_column()
    status_value: Mapped[str] = mapped_column()
    status_detail: Mapped[str] = mapped_column()
    response: Mapped[str] = mapped_column()
    session_in: Mapped[str] = mapped_column()
    session_out: Mapped[str] = mapped_column()
    auth_in: Mapped[str] = mapped_column()
    auth_out: Mapped[str] = mapped_column()


class DBActionParameter(Base):
    __tablename__ = "action_parameter"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()

    action_id: Mapped[int] = mapped_column(ForeignKey("action.id"))
    action: Mapped['DBAction'] = relationship(back_populates="parameters")

class DataStoreSQLite(DataStore):
    def __init__(self, params: Dict[str, str]):
        self._db_path = "cyst.db"
        if "path" in params:
            self._db_path = params["path"]

        self._db = create_engine(f"sqlite+pysqlite:///{self._db_path}")
        Base.metadata.create_all(self._db)

    def add_action(self, action: ActionModel) -> None:
        with Session(self._db) as session:
            db_action = DBAction(
                message_id=action.message_id,
                run_id=action.run_id,
                action_id=action.action_id,
                caller_id=action.caller_id,
                src_ip=action.src_ip,
                dst_ip=action.dst_ip,
                dst_service=action.dst_service,
                status_origin=action.status_origin,
                status_value=action.status_value,
                status_detail=action.status_detail,
                response=action.response,
                session_in=action.session_in,
                session_out=action.session_out,
                auth_in=action.auth_in,
                auth_out=action.auth_out
            )
            session.add(db_action)
            session.flush()

            for param in action.parameters:
                p = DBActionParameter(
                    name=param.name,
                    value=param.value,
                    action_id=db_action.id
                )
                session.add(p)

            session.commit()


def create_data_store_sqlite(params: Dict[str, str]) -> DataStore:
    return DataStoreSQLite(params)


data_store_sqlite_description = DataStoreDescription(
    backend="sqlite",
    description="A SQLite-based data store.",
    creation_fn=create_data_store_sqlite
)
