from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)

metadata = MetaData()

# Clé primaire auto-incrémentée sur BIGINT côté PostgreSQL, mais INTEGER côté
# SQLite (indispensable pour que SQLite auto-incrémente via le rowid).
BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")

competition = Table(
    "competition",
    metadata,
    Column("id_cpt", BigInteger, primary_key=True, autoincrement=False),  # idcpt FFN
    Column("name", Text),
    Column("city", Text),
    Column("country", Text),
    Column("date_start", Date),
    Column("date_end", Date),
    Column("pool_size", SmallInteger),  # 25 / 50
    Column("level", Text),  # International / National...
    Column("type", Text),  # libellé FFN
    Column("type_code", Integer),
    Column("category", Text),  # Juniors / Seniors... (NULL = open)
    Column("season", Text),
    Column("scraped_at", DateTime(timezone=True)),
)

club = Table(
    "club",
    metadata,
    Column("id_club", BigInteger, primary_key=True, autoincrement=False),  # idban FFN
    Column("name", Text),
)

swimmer = Table(
    "swimmer",
    metadata,
    Column("iuf", BigInteger, primary_key=True, autoincrement=False),  # id national FFN
    Column("last_name", Text),
    Column("first_name", Text),
    Column("full_name", Text),
    Column("birth_year", SmallInteger),
    Column("nationality", Text),
    Column("gender", String(1)),
)

event = Table(
    "event",
    metadata,
    Column("id_event", Integer, primary_key=True),  # auto-incrément
    Column("distance", Integer, nullable=False),
    Column("stroke", Text, nullable=False),  # NL / DOS / BRA / PAP / 4N
    Column("is_relay", Boolean, nullable=False, default=False),
    Column("label", Text, nullable=False),
    UniqueConstraint("distance", "stroke", "is_relay", name="uq_event"),
)

result = Table(
    "result",
    metadata,
    Column("id_result", BIGINT_PK, primary_key=True),  # clé technique
    Column(
        "id_cpt",
        BigInteger,
        ForeignKey("competition.id_cpt", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("id_event", Integer, ForeignKey("event.id_event"), nullable=False),
    Column("iuf", BigInteger, ForeignKey("swimmer.iuf")),  # NULL pour un relais
    Column("id_club", BigInteger, ForeignKey("club.id_club")),
    Column("id_res", BigInteger),  # idres ExtraNat
    Column("rank", Integer),
    Column("time_cs", Integer),  # centièmes de seconde
    Column("reaction", Numeric(5, 2)),  # temps de réaction (s)
    Column("points", Integer),
    Column("phase", Text),  # series / semi / final_a...
    Column("gender", String(1)),
    Column("race_date", Date),
    Column("is_relay", Boolean, default=False),
    Index("idx_result_cpt", "id_cpt"),
    Index("idx_result_event", "id_event"),
    Index("idx_result_swimmer", "iuf"),
    # idres est unique côté FFN : garde-fou contre les doublons (index partiel).
    Index(
        "uq_result_idres",
        "id_res",
        unique=True,
        postgresql_where=text("id_res IS NOT NULL"),
        sqlite_where=text("id_res IS NOT NULL"),
    ),
)
