from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EmbedRequest(_message.Message):
    __slots__ = ("request_id", "texts")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TEXTS_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    texts: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, request_id: _Optional[str] = ..., texts: _Optional[_Iterable[str]] = ...) -> None: ...

class Vector(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, values: _Optional[_Iterable[float]] = ...) -> None: ...

class EmbedResponse(_message.Message):
    __slots__ = ("request_id", "vectors", "model_name", "dimension")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    DIMENSION_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    vectors: _containers.RepeatedCompositeFieldContainer[Vector]
    model_name: str
    dimension: int
    def __init__(self, request_id: _Optional[str] = ..., vectors: _Optional[_Iterable[_Union[Vector, _Mapping]]] = ..., model_name: _Optional[str] = ..., dimension: _Optional[int] = ...) -> None: ...

class GetModelInfoRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetModelInfoResponse(_message.Message):
    __slots__ = ("model_name", "dimension", "max_batch_size", "max_token_length")
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    DIMENSION_FIELD_NUMBER: _ClassVar[int]
    MAX_BATCH_SIZE_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKEN_LENGTH_FIELD_NUMBER: _ClassVar[int]
    model_name: str
    dimension: int
    max_batch_size: int
    max_token_length: int
    def __init__(self, model_name: _Optional[str] = ..., dimension: _Optional[int] = ..., max_batch_size: _Optional[int] = ..., max_token_length: _Optional[int] = ...) -> None: ...
