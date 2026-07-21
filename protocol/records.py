"""Frozen dataclasses to plain data and back, keyed by type name.

Both the events a game publishes and the messages that carry them travel as the
same shape - what kind it is, and its fields - so the mechanism lives here once
and each module supplies only its own list of what may travel.

Encoding is driven by the record's own fields, so a record that gains a field
carries it without this module changing.
"""
from __future__ import annotations

from dataclasses import fields

from protocol.errors import ProtocolError


def by_name(record_types):
    """The lookup a module hands back in: {type name: type}."""
    return {record_type.__name__: record_type for record_type in record_types}


def encode_record(record, allowed):
    """A record as plain data, labelled with the name of its type."""
    name = type(record).__name__
    if name not in allowed:
        raise ProtocolError(name)
    return {
        "name": name,
        "fields": {
            field.name: _to_wire(getattr(record, field.name))
            for field in fields(record)
        },
    }


def decode_record(data, allowed):
    """Plain data back into the record it names."""
    name = data.get("name")
    record_type = allowed.get(name)
    if record_type is None:
        raise ProtocolError(name)
    values = {
        field: _from_wire(value)
        for field, value in data.get("fields", {}).items()
    }
    try:
        return record_type(**values)
    except TypeError as error:
        raise ProtocolError(name) from error


def _to_wire(value):
    # Cells and target lists are the only tuples a record carries, and JSON has
    # no tuples. Anything nested inside a dict is already in wire form.
    return list(value) if isinstance(value, tuple) else value


def _from_wire(value):
    return tuple(value) if isinstance(value, list) else value
