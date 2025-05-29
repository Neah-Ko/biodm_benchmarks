# Functions to create the schemas


def get_obj_schema(
    props, field_enums=None, required=[], additional_props=False
):

    schema = {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": additional_props,
    }

    # below does not seemed to be used anylonger
    # if field_enums:
    #     for k, v in field_enums.items():
    #         schema["properties"][k]["enum"] = v

    return schema


def get_obj_schema2(
    fields, field_enums=None, required=[], additional_props=False
):

    props = {}
    for field in fields:
        val = {"type": "string"}
        if field["mandatory"]:
            val["minLength"] = 1

        if "allowedValues" in field:
            val = {"type": "boolean"}

        props[field["id"]] = val

    schema = {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": additional_props,
    }

    if field_enums:
        for k, v in field_enums.items():
            schema["properties"][k]["enum"] = v

    return schema


def get_arr_schema(
    array_of="objects",
    props=None,
    additional_props=False,
    field_enums=None,
    required=[],
    min_items=1,
    unique_items=True,
):
    """
    get schema for array of objects (or integers)
    """

    items = {"type": "integer"}
    if array_of == "objects":
        items = get_obj_schema(props, field_enums, required, additional_props)

    schema = {
        "type": "array",
        "minItems": min_items,
        "uniqueItems": unique_items,
        "items": items,
    }

    if array_of == "integers":
        schema["items"] = {"type": "integer"}

    return schema


def modify_schema(schema, prop, fields_to_types):

    props = {k: {"type": v} for k, v in fields_to_types.items()}
    schema["properties"][prop] = {
        "anyOf": [
            get_arr_schema(
                array_of="objects",
                props=props,
                required=list(fields_to_types.keys()),
            ),
            {"type": "null"},
        ]
    }
    schema["required"].append(prop)
