from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

# Таблица для связи многие-ко-многим между пользователями и группами, 1 пользлователь может быть в нескольких группах
user_group_association = Table(
    'user_group_association',                                                               # Имя таблицы в БД
    Base.metadata,                                                                                # Метаданные SQLAlchemy
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

class Group(Base):

    """Создаем модель Group,таблица позволяющая объединить
     пользователей в группы например для учёта семейных транзакций,
      идентификатор группы, название группы, ссылка на пользователя.
      id - идентификатор
      name - название группы
      description  - описание группы (опциональное поле)
      owner id - создатель группы"""

    __tablename__ = "groups"

    id = Column(Integer,primary_key=True,index= True)
    name = Column(String(100),nullable=False,index = True)
    description = Column(String,nullable=True)
    owner_id = Column(Integer,ForeignKey('user.id'),nullable = False)


    # Связь с пользователями (многие-ко-многим)
    members = relationship(
        "User",
        secondary=user_group_association,
        back_populates="groups",
        lazy="selectin"
    )

    # для  связи с транзакциями, нужно предварительно сопоставить
    transactions = relationship(
        "Transaction",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Связь с создателем
    # Зачем нужна отдельная связь owner?
    # Разные роли: Создатель ≠ обычный участник
    # Права доступа: Создатель может иметь особые права(удаление, редактирование)
    # Аудиторство: Знать, кто создал группу
    # Бизнес - логика: Только создатель может приглашать / исключать

    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_groups")

    #отладка
    def __repr__(self):
        return f"<Group(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"


