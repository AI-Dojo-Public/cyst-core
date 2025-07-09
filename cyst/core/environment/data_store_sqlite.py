from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, MappedAsDataclass, Session, relationship
from typing import Dict, List

from cyst.api.environment.data_model import ActionModel
from cyst.api.environment.stores import DataStore, DataStoreDescription
from cyst.api.environment.message import Status, Message, Request, Response


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


# We are not keeping a full relationship between actions and messages to make it more easily digestible for user
# analyses. So the action parameters are not really present as they are mapping by message id to one specific action
# and can be extracted if needed.
#
# The SQL query to retrieve the messages together with their parameters (for CYST simulation platform) is:
#
# select message.*,
#        max(case when platform_specific.name == 'current_hop_ip' then platform_specific.value END) as current_hop_ip,
#        max(case when platform_specific.name == 'current_hop_id' then platform_specific.value END) as current_hop_id,
#        max(case when platform_specific.name == 'next_hop_ip' then platform_specific.value END) as next_hop_ip,
#        max(case when platform_specific.name == 'next_hop_id' then platform_specific.value END) as next_hop_id
# from message
# left join platform_specific on message.id = platform_specific.message_id
# group by message.id;
class DBMessage(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column()
    type: Mapped[str] = mapped_column()
    run_id: Mapped[str] = mapped_column()
    action_id: Mapped[str] = mapped_column()
    caller_id: Mapped[str] = mapped_column()
    src_ip: Mapped[str] = mapped_column()
    dst_ip: Mapped[str] = mapped_column()
    dst_service: Mapped[str] = mapped_column()
    ttl: Mapped[int] = mapped_column()
    status_origin: Mapped[str] = mapped_column()
    status_value: Mapped[str] = mapped_column()
    status_detail: Mapped[str] = mapped_column()
    session: Mapped[str] = mapped_column()
    auth: Mapped[str] = mapped_column()
    response: Mapped[str] = mapped_column()

    platform_specific: Mapped[List['DBMessagePlatformSpecific']] = relationship("DBMessagePlatformSpecific",
                                                                                back_populates="message",
                                                                                cascade="all, delete")

class DBMessagePlatformSpecific(Base):
    __tablename__ = "platform_specific"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()

    message_id: Mapped[int] = mapped_column(ForeignKey("message.id"))
    message: Mapped[DBMessage] = relationship(back_populates="platform_specific")


class DataStoreSQLite(DataStore):
    def __init__(self, run_id: str, params: Dict[str, str]):
        self._run_id = run_id
        self._db_path = "cyst.db"
        if "path" in params:
            self._db_path = params["path"]

        self._db = create_engine(f"sqlite+pysqlite:///{self._db_path}")
        Base.metadata.create_all(self._db)

    def add_action(self, action: ActionModel) -> None:
        with Session(self._db) as session:
            db_action = DBAction(
                message_id=action.message_id,
                run_id=self._run_id,
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

    def add_message(self, message: Message) -> None:
        if isinstance(message, Request):
            action_id = message.action.id
            status_origin = ""
            status_value = ""
            status_detail = ""
            response = ""
        elif isinstance(message, Response):
            action_id = message.action.id
            status_origin = str(message.status.origin)
            status_value = str(message.status.value)
            status_detail = str(message.status.detail)
            response = str(message.content)
        else:
            action_id = ""
            status_origin = ""
            status_value = ""
            status_detail = ""
            response = ""

        with Session(self._db) as session:
            db_message = DBMessage(
                message_id=message.id,
                type=str(message.type),
                run_id=self._run_id,
                action_id=action_id,
                caller_id=message.platform_specific["caller_id"],
                src_ip=str(message.src_ip),
                dst_ip=str(message.dst_ip),
                dst_service=message.dst_service,
                ttl=message.ttl,
                status_origin=status_origin,
                status_value=status_value,
                status_detail=status_detail,
                session=str(message.session.id) if message.session else "",
                auth="",
                response=response
            )
            session.add(db_message)
            session.flush()

            for k, v in message.platform_specific.items():
                if k == "caller_id":
                    continue

                session.add(DBMessagePlatformSpecific(
                    name=k,
                    value=str(v),
                    message_id=db_message.id
                ))

            session.commit()


def create_data_store_sqlite(run_id: str, params: Dict[str, str]) -> DataStore:
    return DataStoreSQLite(run_id, params)


data_store_sqlite_description = DataStoreDescription(
    backend="sqlite",
    description="A SQLite-based data store.",
    creation_fn=create_data_store_sqlite
)
