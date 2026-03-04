"""Database models for processual unified tables (TPU) from CNJ."""

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

class TpuClasse(Base, TimestampMixin):
    """
    Tabela Processual Unificada (TPU) - Classes.
    Armazena a classe processual de acordo com a tabela do CNJ (`cod_item`).
    """
    
    __tablename__ = "tpu_classes"
    
    codigo: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        comment="Código da classe no CNJ",
    )
    
    nome: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
        comment="Nome ou descrição da classe",
    )
    
    sigla: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    cod_item_pai: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("tpu_classes.codigo"),
        nullable=True,
        index=True,
    )
    
    glossario: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Adicionais uteis que vem na API do CNJ
    natureza: Mapped[str | None] = mapped_column(Text, nullable=True)
    polo_ativo: Mapped[str | None] = mapped_column(Text, nullable=True)
    polo_passivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<TpuClasse(codigo={self.codigo}, nome={self.nome})>"
        

class TpuAssunto(Base, TimestampMixin):
    """
    Tabela Processual Unificada (TPU) - Assuntos.
    Armazena o assunto processual (matéria) de acordo com a tabela do CNJ (`cod_item`).
    """
    
    __tablename__ = "tpu_assuntos"
    
    codigo: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        comment="Código do assunto no CNJ (cod_item)",
    )
    
    nome: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
        comment="Nome ou descrição do assunto",
    )
    
    cod_item_pai: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("tpu_assuntos.codigo"),
        nullable=True,
        index=True,
    )
    
    glossario: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    artigo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    def __repr__(self) -> str:
        return f"<TpuAssunto(codigo={self.codigo}, nome={self.nome})>"


class TpuDocumento(Base, TimestampMixin):
    """
    Tabela Processual Unificada (TPU) - Documentos Processuais.
    Armazena os tipos de documento conforme tabela oficial do CNJ.
    """

    __tablename__ = "tpu_documentos"

    codigo: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        comment="Código do tipo de documento no CNJ (cod_item)",
    )

    nome: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
        comment="Nome do tipo de documento",
    )

    cod_item_pai: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Código do item pai (categoria)",
    )

    glossario: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição/glossário do tipo de documento",
    )

    def __repr__(self) -> str:
        return f"<TpuDocumento(codigo={self.codigo}, nome={self.nome})>"
