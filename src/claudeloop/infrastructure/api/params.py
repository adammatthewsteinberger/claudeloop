"""Classify SDK method parameters for Typer / Click binding."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Union, get_args, get_origin

from anthropic import NotGiven, Omit

SKIP_PARAMETERS = frozenset(
    {
        "self",
        "extra_headers",
        "extra_query",
        "extra_body",
    }
)


@dataclass(frozen=True, slots=True)
class ScalarParam:
    name: str
    cli_name: str
    annotation: Any
    required: bool
    default: Any


def _is_omit_default(default: Any) -> bool:
    return isinstance(default, (Omit, NotGiven))


def _unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def is_scalar_annotation(annotation: Any) -> bool:
    if annotation is inspect.Parameter.empty:
        return False
    ann = _unwrap_optional(annotation)
    if ann is bool:
        return True
    if ann in (int, float, str):
        return True
    origin = get_origin(ann)
    if origin is not None:
        return False
    if isinstance(ann, str):
        # Forward refs to complex TypedDicts — not scalar.
        return ann in {"int", "float", "str", "bool"}
    return False


def scalar_parameters(signature: inspect.Signature) -> tuple[ScalarParam, ...]:
    params: list[ScalarParam] = []
    for name, param in signature.parameters.items():
        if name in SKIP_PARAMETERS:
            continue
        if not is_scalar_annotation(param.annotation):
            continue
        required = param.default is inspect.Parameter.empty
        if not required and _is_omit_default(param.default):
            required = False
        cli_name = name.replace("_", "-")
        params.append(
            ScalarParam(
                name=name,
                cli_name=cli_name,
                annotation=param.annotation,
                required=required,
                default=None if required else param.default,
            )
        )
    return tuple(params)


def build_call_kwargs(
    signature: inspect.Signature,
    *,
    json_payload: dict[str, Any],
    scalar_values: dict[str, Any],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = dict(json_payload)
    for name, value in scalar_values.items():
        if value is None:
            continue
        kwargs[name] = value
    for name, param in signature.parameters.items():
        if name in SKIP_PARAMETERS or name == "self":
            continue
        if name in kwargs:
            continue
        if param.default is not inspect.Parameter.empty and not _is_omit_default(param.default):
            kwargs[name] = param.default
    return kwargs
