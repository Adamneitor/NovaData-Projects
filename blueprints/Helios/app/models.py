from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ---------------------------------------------------------------------------
# Seguridad: perfiles, usuarios y grupos
# ---------------------------------------------------------------------------


class PerfilUsuario(Base):
    __tablename__ = "Perfiles_Usuarios"

    id: Mapped[int] = mapped_column("id_perfil", SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255))

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="perfil")


class Usuario(Base):
    __tablename__ = "Usuarios"

    id: Mapped[int] = mapped_column("key_usuario", Integer, primary_key=True, autoincrement=True)
    usuario_ad: Mapped[str] = mapped_column("usuarioAd", String(50), unique=True)
    nombre: Mapped[str] = mapped_column("Nombre_Usuario", String(100))
    # APP = autenticacion local con contraseña; AD = autenticacion contra Active Directory
    tipo_autenticacion: Mapped[str] = mapped_column("Tipo_Autenticacion", String(10), default="APP")
    password_hash: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Si True, el usuario de aplicación debe cambiar la contraseña al iniciar sesión
    debe_cambiar_password: Mapped[bool] = mapped_column("Debe_Cambiar_Password", Boolean, default=False)
    # Vigencia opcional en dias (NULL = no expira). Solo aplicable a usuarios APP.
    dias_vigencia_password: Mapped[int | None] = mapped_column("Dias_Vigencia_Password", Integer, nullable=True)
    password_fecha_cambio: Mapped[datetime | None] = mapped_column("Password_Fecha_Cambio", DateTime, nullable=True)
    perfil_id: Mapped[int] = mapped_column("id_perfil", ForeignKey("Perfiles_Usuarios.id_perfil"))
    activo: Mapped[bool] = mapped_column("flag_activo", Boolean, default=True)
    fecha_inactivacion: Mapped[datetime | None] = mapped_column(DateTime)

    perfil: Mapped[PerfilUsuario] = relationship(back_populates="usuarios")
    grupos: Mapped[list["GrupoUsuario"]] = relationship(
        secondary="Grupos_X_Usuario", back_populates="usuarios"
    )


class PoliticaPassword(Base):
    """Configuracion global de politicas de contraseña (una fila activa)."""

    __tablename__ = "Politicas_Password"

    id: Mapped[int] = mapped_column("IdPolitica", Integer, primary_key=True, autoincrement=True)
    longitud_minima: Mapped[int] = mapped_column(Integer, default=8)
    # ninguna | inicio | final | cualquiera
    mayusculas: Mapped[str] = mapped_column(String(15), default="cualquiera")
    requiere_numero: Mapped[bool] = mapped_column(Boolean, default=True)
    requiere_especial: Mapped[bool] = mapped_column(Boolean, default=True)
    max_repetidos_consecutivos: Mapped[int] = mapped_column(Integer, default=3)
    permite_espacios: Mapped[bool] = mapped_column(Boolean, default=False)
    historial_no_reutilizar: Mapped[int] = mapped_column(Integer, default=5)  # ultimas N
    vigencia_default_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_modificacion: Mapped[datetime | None] = mapped_column(DateTime)
    modificado_por_id: Mapped[int | None] = mapped_column(
        "key_usuario_modificacion", ForeignKey("Usuarios.key_usuario")
    )


class UsuarioPasswordHistorial(Base):
    __tablename__ = "Usuarios_Password_Historial"

    id: Mapped[int] = mapped_column("IdHistorial", BigInteger, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column("key_usuario", ForeignKey("Usuarios.key_usuario"))
    password_hash: Mapped[str] = mapped_column(String(300))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped[Usuario] = relationship()


class AuditoriaPassword(Base):
    __tablename__ = "Auditoria_Password"

    id: Mapped[int] = mapped_column("IdAuditoria", BigInteger, primary_key=True, autoincrement=True)
    usuario_afectado_id: Mapped[int] = mapped_column("key_usuario_afectado", ForeignKey("Usuarios.key_usuario"))
    actor_id: Mapped[int | None] = mapped_column("key_usuario_actor", ForeignKey("Usuarios.key_usuario"))
    # CAMBIO | RESET_ADMIN | EXPIRACION | POLITICA | LOGIN_FALLIDO
    evento: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[str | None] = mapped_column(String(500))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ip: Mapped[str | None] = mapped_column(String(50))


class GrupoUsuario(Base):
    __tablename__ = "Grupos_Usuarios"

    id: Mapped[int] = mapped_column("key_grupo", Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column("Grupo", String(100), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255))

    usuarios: Mapped[list[Usuario]] = relationship(
        secondary="Grupos_X_Usuario", back_populates="grupos"
    )


class GrupoXUsuario(Base):
    __tablename__ = "Grupos_X_Usuario"

    grupo_id: Mapped[int] = mapped_column(
        "key_grupo", ForeignKey("Grupos_Usuarios.key_grupo"), primary_key=True
    )
    usuario_id: Mapped[int] = mapped_column(
        "key_usuario", ForeignKey("Usuarios.key_usuario"), primary_key=True
    )


# ---------------------------------------------------------------------------
# Catalogos BPM
# ---------------------------------------------------------------------------


class TipoFlujo(Base):
    __tablename__ = "Tipos_Flujos"

    id: Mapped[int] = mapped_column("cod_tipo_flujo", Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column("Tipo_Flujo", String(100), unique=True)


class Documento(Base):
    __tablename__ = "Documentos"

    id: Mapped[int] = mapped_column("IdDocumento", Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column("Nombre", String(150), unique=True)
    descripcion: Mapped[str | None] = mapped_column("Descripcion", String(300))
    activo: Mapped[bool] = mapped_column("Activo", Boolean, default=True)


class TipoDato(Base):
    __tablename__ = "Tipos_Datos_Complementarios"

    id: Mapped[int] = mapped_column("key_tipo_dato", SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column("Tipo_Dato", String(40), unique=True)
    input_html: Mapped[str] = mapped_column(String(20), default="text")
    # Código estable: texto, numero, numero_decimal, telefono, moneda, moneda_decimal, ...
    codigo: Mapped[str | None] = mapped_column("Codigo", String(30))


class DatoComplementario(Base):
    __tablename__ = "Datos_Complementarios"

    id: Mapped[int] = mapped_column("key_dato", Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column("Dato", String(100), unique=True)
    descripcion: Mapped[str | None] = mapped_column("Descripcion", String(255))
    tipo_dato_id: Mapped[int] = mapped_column(
        "key_tipo_dato", ForeignKey("Tipos_Datos_Complementarios.key_tipo_dato")
    )
    # Para tipo "Lista": opciones separadas por ";"
    opciones: Mapped[str | None] = mapped_column("Opciones", String(1000))
    # Formato de visualización independiente del almacenamiento raw
    formato_visualizacion: Mapped[str | None] = mapped_column("Formato_Visualizacion", String(30))
    # Precisión decimal (2 por defecto en tipos decimales)
    decimales: Mapped[int | None] = mapped_column("Decimales", Integer)
    activo: Mapped[bool] = mapped_column("Activo", Boolean, default=True)

    tipo_dato: Mapped[TipoDato] = relationship()


# ---------------------------------------------------------------------------
# Configuracion de APIs externas
# ---------------------------------------------------------------------------


class ApiCall(Base):
    __tablename__ = "Api_Calls"

    id: Mapped[int] = mapped_column("IdApi", Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column("Nombre", String(150), unique=True)
    descripcion: Mapped[str | None] = mapped_column("Descripcion", String(500))
    metodo: Mapped[str] = mapped_column("Metodo", String(10), default="POST")  # GET/POST/PUT/PATCH
    url: Mapped[str] = mapped_column("Url", String(500))
    headers_json: Mapped[str | None] = mapped_column("Headers", Text)  # JSON de headers fijos
    timeout_seg: Mapped[int] = mapped_column("TimeoutSeg", Integer, default=30)
    activo: Mapped[bool] = mapped_column("Activo", Boolean, default=True)

    parametros: Mapped[list["ApiParametro"]] = relationship(
        back_populates="api", cascade="all, delete-orphan"
    )
    outputs: Mapped[list["ApiOutput"]] = relationship(
        back_populates="api", cascade="all, delete-orphan"
    )


class ApiParametro(Base):
    """Parametro de entrada de un API. El valor puede ser fijo, un dato
    complementario del caso o un campo intrinseco del caso (id, cliente, etapa...)."""

    __tablename__ = "Api_Parametros"

    id: Mapped[int] = mapped_column("IdParametro", Integer, primary_key=True, autoincrement=True)
    api_id: Mapped[int] = mapped_column("IdApi", ForeignKey("Api_Calls.IdApi"))
    nombre: Mapped[str] = mapped_column("Nombre", String(100))
    ubicacion: Mapped[str] = mapped_column("Ubicacion", String(10), default="body")  # query/body/header/path
    origen: Mapped[str] = mapped_column("Origen", String(15), default="fijo")  # fijo/dato/caso
    valor_fijo: Mapped[str | None] = mapped_column("ValorFijo", String(500))
    dato_id: Mapped[int | None] = mapped_column(
        "key_dato", ForeignKey("Datos_Complementarios.key_dato")
    )
    campo_caso: Mapped[str | None] = mapped_column("CampoCaso", String(50))  # id_caso/cliente_id/...

    api: Mapped[ApiCall] = relationship(back_populates="parametros")
    dato: Mapped[DatoComplementario | None] = relationship()


class ApiOutput(Base):
    """Salida esperada del API, extraida de la respuesta JSON via ruta de punto
    (ej. 'resultado.score')."""

    __tablename__ = "Api_Outputs"

    id: Mapped[int] = mapped_column("IdOutput", Integer, primary_key=True, autoincrement=True)
    api_id: Mapped[int] = mapped_column("IdApi", ForeignKey("Api_Calls.IdApi"))
    nombre: Mapped[str] = mapped_column("Nombre", String(100))
    json_path: Mapped[str] = mapped_column("JsonPath", String(300))
    formato: Mapped[str] = mapped_column("Formato", String(15), default="texto")  # texto/numero/booleano

    api: Mapped[ApiCall] = relationship(back_populates="outputs")


# ---------------------------------------------------------------------------
# Definicion de flujos
# ---------------------------------------------------------------------------


class Flujo(Base):
    __tablename__ = "Flujos"

    id: Mapped[int] = mapped_column("IdFlujo", Integer, primary_key=True, autoincrement=True)
    tipo_flujo_id: Mapped[int] = mapped_column(
        "cod_tipo_flujo", ForeignKey("Tipos_Flujos.cod_tipo_flujo")
    )
    nombre: Mapped[str] = mapped_column("Nombre", String(150))
    descripcion: Mapped[str | None] = mapped_column("Descripcion", String(500))
    activo: Mapped[bool] = mapped_column("Activo", Boolean, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # API que se invoca al concluir (cerrar) el flujo, para integraciones
    api_conclusion_id: Mapped[int | None] = mapped_column(
        "IdApiConclusion", ForeignKey("Api_Calls.IdApi")
    )

    tipo_flujo: Mapped[TipoFlujo] = relationship()
    api_conclusion: Mapped[ApiCall | None] = relationship()
    etapas: Mapped[list["Etapa"]] = relationship(
        back_populates="flujo", order_by="Etapa.orden", cascade="all, delete-orphan"
    )


class Etapa(Base):
    __tablename__ = "Etapas"

    id: Mapped[int] = mapped_column("IdEtapa", Integer, primary_key=True, autoincrement=True)
    flujo_id: Mapped[int] = mapped_column("IdFlujo", ForeignKey("Flujos.IdFlujo"))
    nombre: Mapped[str] = mapped_column("Nombre_Etapa", String(150))
    descripcion: Mapped[str | None] = mapped_column("Descripcion", String(500))
    orden: Mapped[int] = mapped_column("Orden", Integer)
    permite_retroceso: Mapped[bool] = mapped_column("PermiteRetroceso", Boolean, default=False)
    es_final: Mapped[bool] = mapped_column("EsFinal", Boolean, default=False)
    # Si en esta etapa se solicita documentacion al solicitante
    solicita_documentacion: Mapped[bool] = mapped_column(
        "SolicitaDocumentacion", Boolean, default=False
    )

    flujo: Mapped[Flujo] = relationship(back_populates="etapas")
    estados: Mapped[list["Estado"]] = relationship(
        back_populates="etapa", cascade="all, delete-orphan"
    )
    documentos: Mapped[list["EtapaDocumento"]] = relationship(
        back_populates="etapa", cascade="all, delete-orphan"
    )
    datos: Mapped[list["EtapaDato"]] = relationship(
        back_populates="etapa", cascade="all, delete-orphan"
    )
    grupos: Mapped[list[GrupoUsuario]] = relationship(secondary="Etapas_X_Grupo")


class Estado(Base):
    __tablename__ = "Estados"

    id: Mapped[int] = mapped_column("IdEstado", Integer, primary_key=True, autoincrement=True)
    etapa_id: Mapped[int] = mapped_column("IdEtapa", ForeignKey("Etapas.IdEtapa"))
    nombre: Mapped[str] = mapped_column("Nombre", String(100))
    # Indica si al llegar a este estado se cierra (concluye) la etapa
    cierra_etapa: Mapped[bool] = mapped_column("CierraEtapa", Boolean, default=False)
    es_inicial: Mapped[bool] = mapped_column("EsInicial", Boolean, default=False)
    # API asociado: al entrar al estado se ejecuta y sus reglas direccionan el caso
    api_call_id: Mapped[int | None] = mapped_column("IdApi", ForeignKey("Api_Calls.IdApi"))

    etapa: Mapped[Etapa] = relationship(back_populates="estados")
    api_call: Mapped[ApiCall | None] = relationship()
    transiciones: Mapped[list["Transicion"]] = relationship(
        back_populates="estado_origen",
        foreign_keys="Transicion.estado_origen_id",
        cascade="all, delete-orphan",
    )
    reglas_api: Mapped[list["ApiRegla"]] = relationship(
        back_populates="estado",
        foreign_keys="ApiRegla.estado_id",
        cascade="all, delete-orphan",
    )
    reglas_datos: Mapped[list["DatoRegla"]] = relationship(
        back_populates="estado",
        foreign_keys="DatoRegla.estado_id",
        cascade="all, delete-orphan",
        order_by="DatoRegla.prioridad",
    )
    mapeos_input: Mapped[list["EstadoApiInput"]] = relationship(
        back_populates="estado",
        cascade="all, delete-orphan",
    )
    mapeos_output: Mapped[list["EstadoApiOutput"]] = relationship(
        back_populates="estado",
        cascade="all, delete-orphan",
    )


class EstadoApiInput(Base):
    """Override de origen de un parámetro de API para un estado concreto.

    Si no hay fila, se usa la configuración del ApiParametro del catálogo.
    origen: fijo | dato | caso (incluye campos de cliente).
    """

    __tablename__ = "Estado_Api_Inputs"
    __table_args__ = (UniqueConstraint("IdEstado", "IdParametro"),)

    id: Mapped[int] = mapped_column("IdEstadoApiInput", Integer, primary_key=True, autoincrement=True)
    estado_id: Mapped[int] = mapped_column("IdEstado", ForeignKey("Estados.IdEstado"))
    parametro_id: Mapped[int] = mapped_column("IdParametro", ForeignKey("Api_Parametros.IdParametro"))
    origen: Mapped[str] = mapped_column("Origen", String(15), default="fijo")
    valor_fijo: Mapped[str | None] = mapped_column("ValorFijo", String(500))
    dato_id: Mapped[int | None] = mapped_column(
        "key_dato", ForeignKey("Datos_Complementarios.key_dato")
    )
    campo_caso: Mapped[str | None] = mapped_column("CampoCaso", String(50))

    estado: Mapped[Estado] = relationship(back_populates="mapeos_input")
    parametro: Mapped[ApiParametro] = relationship()
    dato: Mapped[DatoComplementario | None] = relationship()


class EstadoApiOutput(Base):
    """Mapeo de un output de API hacia un dato adicional del caso (por estado).

    El dato destino queda protegido contra edición manual en formularios.
    """

    __tablename__ = "Estado_Api_Outputs"
    __table_args__ = (UniqueConstraint("IdEstado", "IdOutput"),)

    id: Mapped[int] = mapped_column("IdEstadoApiOutput", Integer, primary_key=True, autoincrement=True)
    estado_id: Mapped[int] = mapped_column("IdEstado", ForeignKey("Estados.IdEstado"))
    output_id: Mapped[int] = mapped_column("IdOutput", ForeignKey("Api_Outputs.IdOutput"))
    dato_id: Mapped[int] = mapped_column("key_dato", ForeignKey("Datos_Complementarios.key_dato"))

    estado: Mapped[Estado] = relationship(back_populates="mapeos_output")
    output: Mapped[ApiOutput] = relationship()
    dato: Mapped[DatoComplementario] = relationship()


class Transicion(Base):
    """Transicion manual: desde un estado origen hacia una etapa/estado destino."""

    __tablename__ = "Transiciones"
    __table_args__ = (UniqueConstraint("IdEstadoOrigen", "IdEstadoDestino"),)

    id: Mapped[int] = mapped_column("IdTransicion", Integer, primary_key=True, autoincrement=True)
    estado_origen_id: Mapped[int] = mapped_column("IdEstadoOrigen", ForeignKey("Estados.IdEstado"))
    etapa_destino_id: Mapped[int] = mapped_column("IdEtapaDestino", ForeignKey("Etapas.IdEtapa"))
    estado_destino_id: Mapped[int] = mapped_column("IdEstadoDestino", ForeignKey("Estados.IdEstado"))

    estado_origen: Mapped[Estado] = relationship(
        back_populates="transiciones", foreign_keys=[estado_origen_id]
    )
    etapa_destino: Mapped[Etapa] = relationship(foreign_keys=[etapa_destino_id])
    estado_destino: Mapped[Estado] = relationship(foreign_keys=[estado_destino_id])


class ApiRegla(Base):
    """Regla de direccionamiento segun outputs del API asociado a un estado.

    Condiciones combinables con AND/OR. modo_ejecucion:
    - AUTO: transiciona sin click si no hay pendientes obligatorios
    - MANUAL: el usuario debe confirmar la transición sugerida
    """

    __tablename__ = "Api_Reglas"

    id: Mapped[int] = mapped_column("IdRegla", Integer, primary_key=True, autoincrement=True)
    estado_id: Mapped[int] = mapped_column("IdEstado", ForeignKey("Estados.IdEstado"))
    # Legado: una sola condición; preferir `condiciones` cuando existan
    output_id: Mapped[int | None] = mapped_column("IdOutput", ForeignKey("Api_Outputs.IdOutput"), nullable=True)
    operador: Mapped[str | None] = mapped_column("Operador", String(15), nullable=True)
    valor: Mapped[str | None] = mapped_column("Valor", String(200), nullable=True)
    etapa_destino_id: Mapped[int] = mapped_column("IdEtapaDestino", ForeignKey("Etapas.IdEtapa"))
    estado_destino_id: Mapped[int] = mapped_column("IdEstadoDestino", ForeignKey("Estados.IdEstado"))
    prioridad: Mapped[int] = mapped_column("Prioridad", Integer, default=1)
    logica: Mapped[str] = mapped_column("Logica", String(10), default="AND")  # AND | OR
    modo_ejecucion: Mapped[str] = mapped_column("ModoEjecucion", String(10), default="AUTO")  # AUTO | MANUAL
    nombre: Mapped[str | None] = mapped_column("Nombre", String(120), nullable=True)

    estado: Mapped[Estado] = relationship(back_populates="reglas_api", foreign_keys=[estado_id])
    output: Mapped[ApiOutput | None] = relationship()
    etapa_destino: Mapped[Etapa] = relationship(foreign_keys=[etapa_destino_id])
    estado_destino: Mapped[Estado] = relationship(foreign_keys=[estado_destino_id])
    condiciones: Mapped[list["ApiReglaCondicion"]] = relationship(
        back_populates="regla",
        cascade="all, delete-orphan",
        order_by="ApiReglaCondicion.id",
    )


class ApiReglaCondicion(Base):
    """Condición individual de una ApiRegla (output + operador + valor)."""

    __tablename__ = "Api_Regla_Condiciones"

    id: Mapped[int] = mapped_column("IdCondicion", Integer, primary_key=True, autoincrement=True)
    regla_id: Mapped[int] = mapped_column("IdRegla", ForeignKey("Api_Reglas.IdRegla"))
    output_id: Mapped[int] = mapped_column("IdOutput", ForeignKey("Api_Outputs.IdOutput"))
    operador: Mapped[str] = mapped_column("Operador", String(15))
    valor: Mapped[str] = mapped_column("Valor", String(200), default="")

    regla: Mapped[ApiRegla] = relationship(back_populates="condiciones")
    output: Mapped[ApiOutput] = relationship()


class DatoRegla(Base):
    """Regla de direccionamiento segun datos adicionales del caso.

    Se evalúan por prioridad (ascendente). La primera no-default que cumple
    define el destino; si ninguna cumple, se usa la regla marcada como default.
    """

    __tablename__ = "Dato_Reglas"

    id: Mapped[int] = mapped_column("IdDatoRegla", Integer, primary_key=True, autoincrement=True)
    estado_id: Mapped[int] = mapped_column("IdEstado", ForeignKey("Estados.IdEstado"))
    nombre: Mapped[str | None] = mapped_column("Nombre", String(120), nullable=True)
    logica: Mapped[str] = mapped_column("Logica", String(10), default="AND")  # AND | OR
    prioridad: Mapped[int] = mapped_column("Prioridad", Integer, default=1)
    es_default: Mapped[bool] = mapped_column("EsDefault", Boolean, default=False)
    etapa_destino_id: Mapped[int] = mapped_column("IdEtapaDestino", ForeignKey("Etapas.IdEtapa"))
    estado_destino_id: Mapped[int] = mapped_column("IdEstadoDestino", ForeignKey("Estados.IdEstado"))

    estado: Mapped[Estado] = relationship(back_populates="reglas_datos", foreign_keys=[estado_id])
    etapa_destino: Mapped[Etapa] = relationship(foreign_keys=[etapa_destino_id])
    estado_destino: Mapped[Estado] = relationship(foreign_keys=[estado_destino_id])
    condiciones: Mapped[list["DatoReglaCondicion"]] = relationship(
        back_populates="regla",
        cascade="all, delete-orphan",
        order_by="DatoReglaCondicion.id",
    )


class DatoReglaCondicion(Base):
    """Condición individual dentro de una DatoRegla (campo + operador + valor)."""

    __tablename__ = "Dato_Regla_Condiciones"

    id: Mapped[int] = mapped_column("IdCondicion", Integer, primary_key=True, autoincrement=True)
    regla_id: Mapped[int] = mapped_column("IdDatoRegla", ForeignKey("Dato_Reglas.IdDatoRegla"))
    dato_id: Mapped[int] = mapped_column("key_dato", ForeignKey("Datos_Complementarios.key_dato"))
    operador: Mapped[str] = mapped_column("Operador", String(20))
    valor: Mapped[str] = mapped_column("Valor", String(300), default="")
    # Segundo valor para operador between
    valor_hasta: Mapped[str | None] = mapped_column("ValorHasta", String(300), nullable=True)

    regla: Mapped[DatoRegla] = relationship(back_populates="condiciones")
    dato: Mapped[DatoComplementario] = relationship()


class EtapaDocumento(Base):
    __tablename__ = "Etapas_X_Documento"

    etapa_id: Mapped[int] = mapped_column("IdEtapa", ForeignKey("Etapas.IdEtapa"), primary_key=True)
    documento_id: Mapped[int] = mapped_column(
        "IdDocumento", ForeignKey("Documentos.IdDocumento"), primary_key=True
    )
    obligatorio: Mapped[bool] = mapped_column("Obligatorio", Boolean, default=False)

    etapa: Mapped[Etapa] = relationship(back_populates="documentos")
    documento: Mapped[Documento] = relationship()


class EtapaDato(Base):
    __tablename__ = "Etapas_X_Dato"

    etapa_id: Mapped[int] = mapped_column("IdEtapa", ForeignKey("Etapas.IdEtapa"), primary_key=True)
    dato_id: Mapped[int] = mapped_column(
        "key_dato", ForeignKey("Datos_Complementarios.key_dato"), primary_key=True
    )
    obligatorio: Mapped[bool] = mapped_column("Obligatorio", Boolean, default=False)
    # None = sin índice (solo se asigna cuando el usuario lo define)
    orden: Mapped[int | None] = mapped_column("Orden", Integer, nullable=True, default=None)
    # Reglas condicionales (opcional): depende de otro dato booleano de la misma etapa
    depende_de_dato_id: Mapped[int | None] = mapped_column(
        "Depende_De_Dato",
        Integer,
        ForeignKey("Datos_Complementarios.key_dato"),
        nullable=True,
    )
    # Valor esperado del controlador para "cumplir" la condición (true/Si)
    condicion_valor: Mapped[str | None] = mapped_column("Condicion_Valor", String(20), nullable=True)
    # Si True: el campo es obligatorio cuando la condición se cumple
    requerido_si_cumple: Mapped[bool] = mapped_column("Requerido_Si_Cumple", Boolean, default=False)
    # Si True: el campo se deshabilita cuando la condición NO se cumple
    deshabilitar_si_no_cumple: Mapped[bool] = mapped_column(
        "Deshabilitar_Si_No_Cumple", Boolean, default=False
    )

    etapa: Mapped[Etapa] = relationship(back_populates="datos")
    dato: Mapped[DatoComplementario] = relationship(
        foreign_keys=[dato_id],
    )
    depende_de: Mapped[DatoComplementario | None] = relationship(
        foreign_keys=[depende_de_dato_id],
    )


class EtapaGrupo(Base):
    __tablename__ = "Etapas_X_Grupo"

    etapa_id: Mapped[int] = mapped_column("IdEtapa", ForeignKey("Etapas.IdEtapa"), primary_key=True)
    grupo_id: Mapped[int] = mapped_column(
        "key_grupo", ForeignKey("Grupos_Usuarios.key_grupo"), primary_key=True
    )


# ---------------------------------------------------------------------------
# Clientes (solicitantes)
# ---------------------------------------------------------------------------


class Cliente(Base):
    __tablename__ = "Clientes"

    id: Mapped[int] = mapped_column("Cod_CL", Integer, primary_key=True, autoincrement=True)
    nombre_completo: Mapped[str] = mapped_column("Nombre_Completo", String(200))
    tipo_identificacion: Mapped[str] = mapped_column("Tipo_Id", String(30), default="Cedula")
    identificacion: Mapped[str] = mapped_column("Identificacion", String(30), unique=True)
    telefono: Mapped[str | None] = mapped_column("Telefono", String(20))
    correo: Mapped[str | None] = mapped_column("Correo", String(100))


# ---------------------------------------------------------------------------
# Casos (instancias de flujo en ejecucion)
# ---------------------------------------------------------------------------


class Caso(Base):
    __tablename__ = "Casos"

    id: Mapped[int] = mapped_column("IdCaso", BigInteger, primary_key=True, autoincrement=True)
    flujo_id: Mapped[int] = mapped_column("IdFlujo", ForeignKey("Flujos.IdFlujo"))
    cliente_id: Mapped[int | None] = mapped_column("Cod_CL", ForeignKey("Clientes.Cod_CL"))
    etapa_actual_id: Mapped[int] = mapped_column("IdEtapaActual", ForeignKey("Etapas.IdEtapa"))
    estado_actual_id: Mapped[int] = mapped_column("IdEstadoActual", ForeignKey("Estados.IdEstado"))
    estado_general: Mapped[str] = mapped_column(
        "EstadoGeneral", String(20), default="ACTIVO"
    )  # ACTIVO / CERRADO / CANCELADO
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime)
    creado_por_id: Mapped[int] = mapped_column("key_usuario_creador", ForeignKey("Usuarios.key_usuario"))

    flujo: Mapped[Flujo] = relationship()
    cliente: Mapped[Cliente | None] = relationship()
    etapa_actual: Mapped[Etapa] = relationship(foreign_keys=[etapa_actual_id])
    estado_actual: Mapped[Estado] = relationship(foreign_keys=[estado_actual_id])
    creado_por: Mapped[Usuario] = relationship()
    historial: Mapped[list["CasoHistorial"]] = relationship(
        back_populates="caso", order_by="CasoHistorial.fecha", cascade="all, delete-orphan"
    )
    documentos: Mapped[list["CasoDocumento"]] = relationship(
        back_populates="caso", cascade="all, delete-orphan"
    )
    datos: Mapped[list["CasoDato"]] = relationship(
        back_populates="caso", cascade="all, delete-orphan"
    )


class CasoHistorial(Base):
    __tablename__ = "Casos_Historial"

    id: Mapped[int] = mapped_column("IdHistorial", BigInteger, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column("IdCaso", ForeignKey("Casos.IdCaso"))
    etapa_id: Mapped[int] = mapped_column("IdEtapa", ForeignKey("Etapas.IdEtapa"))
    estado_id: Mapped[int] = mapped_column("IdEstado", ForeignKey("Estados.IdEstado"))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    usuario_id: Mapped[int | None] = mapped_column("key_usuario", ForeignKey("Usuarios.key_usuario"))
    comentario: Mapped[str | None] = mapped_column("Comentario", String(500))
    origen: Mapped[str] = mapped_column("Origen", String(10), default="MANUAL")  # MANUAL / API / SISTEMA

    caso: Mapped[Caso] = relationship(back_populates="historial")
    etapa: Mapped[Etapa] = relationship()
    estado: Mapped[Estado] = relationship()
    usuario: Mapped[Usuario | None] = relationship()


class CasoDocumento(Base):
    __tablename__ = "Casos_Documentos"

    id: Mapped[int] = mapped_column("IdCasoDocumento", BigInteger, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column("IdCaso", ForeignKey("Casos.IdCaso"))
    documento_id: Mapped[int] = mapped_column("IdDocumento", ForeignKey("Documentos.IdDocumento"))
    etapa_id: Mapped[int] = mapped_column("IdEtapa", ForeignKey("Etapas.IdEtapa"))
    ruta_archivo: Mapped[str] = mapped_column("RutaArchivo", String(500))
    nombre_original: Mapped[str] = mapped_column("NombreOriginal", String(300))
    fecha_carga: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    usuario_id: Mapped[int] = mapped_column("key_usuario_carga", ForeignKey("Usuarios.key_usuario"))

    caso: Mapped[Caso] = relationship(back_populates="documentos")
    documento: Mapped[Documento] = relationship()
    usuario: Mapped[Usuario] = relationship()


class CasoDato(Base):
    __tablename__ = "Casos_Datos_Complementarios"
    __table_args__ = (UniqueConstraint("IdCaso", "key_dato"),)

    id: Mapped[int] = mapped_column("IdCasoDato", BigInteger, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column("IdCaso", ForeignKey("Casos.IdCaso"))
    dato_id: Mapped[int] = mapped_column("key_dato", ForeignKey("Datos_Complementarios.key_dato"))
    etapa_id: Mapped[int | None] = mapped_column("IdEtapa", ForeignKey("Etapas.IdEtapa"))
    valor: Mapped[str] = mapped_column("Valor", Text)
    fecha_adicion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_modificacion: Mapped[datetime | None] = mapped_column(DateTime)
    usuario_adicion_id: Mapped[int] = mapped_column(
        "key_usuario_adicion", ForeignKey("Usuarios.key_usuario")
    )
    usuario_modificacion_id: Mapped[int | None] = mapped_column(
        "key_usuario_modificacion", ForeignKey("Usuarios.key_usuario")
    )

    caso: Mapped[Caso] = relationship(back_populates="datos")
    dato: Mapped[DatoComplementario] = relationship()
    etapa: Mapped[Etapa | None] = relationship()
    usuario_adicion: Mapped[Usuario] = relationship(foreign_keys=[usuario_adicion_id])
    usuario_modificacion: Mapped[Usuario | None] = relationship(foreign_keys=[usuario_modificacion_id])


class CasoApiLog(Base):
    """Bitacora de ejecuciones de API por caso."""

    __tablename__ = "Casos_Api_Log"

    id: Mapped[int] = mapped_column("IdLog", BigInteger, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column("IdCaso", ForeignKey("Casos.IdCaso"))
    api_id: Mapped[int] = mapped_column("IdApi", ForeignKey("Api_Calls.IdApi"))
    estado_id: Mapped[int | None] = mapped_column("IdEstado", ForeignKey("Estados.IdEstado"))
    request_json: Mapped[str | None] = mapped_column(Text)
    response_json: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    exito: Mapped[bool] = mapped_column("Exito", Boolean, default=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    api: Mapped[ApiCall] = relationship()
