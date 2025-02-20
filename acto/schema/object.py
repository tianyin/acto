from typing import List, Tuple

from acto.schema.schema import extract_schema
from acto.utils.thread_logger import get_thread_logger

from .base import BaseSchema, TreeNode
from .opaque import OpaqueSchema


class ObjectSchema(BaseSchema):
    '''Representation of an object node
    
    It handles
        - properties
        - additionalProperties
        - required
        - minProperties
        - maxProperties
    TODO:
        - dependencies
        - patternProperties
        - regexp
    '''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.properties = {}
        self.additional_properties = None
        self.required = []
        logger = get_thread_logger(with_prefix=True)
        if 'properties' not in schema and 'additionalProperties' not in schema:
            logger.warning('Object schema %s does not have properties nor additionalProperties' %
                           self.path)
        if 'properties' in schema:
            for property_key, property_schema in schema['properties'].items():
                self.properties[property_key] = extract_schema(self.path + [property_key],
                                                               property_schema)
        if 'additionalProperties' in schema:
            self.additional_properties = extract_schema(self.path + ['additional_properties'],
                                                        schema['additionalProperties'])
        if 'required' in schema:
            self.required = schema['required']
        if 'minProperties' in schema:
            self.min_properties = schema['minProperties']
        if 'maxProperties' in schema:
            self.max_properties = schema['maxProperties']

    def get_all_schemas(self) -> Tuple[list, list, list]:
        '''Return all the subschemas as a list'''
        if self.problematic:
            return [], [], []

        normal_schemas: List[BaseSchema] = []
        pruned_by_overspecified: List[BaseSchema] = []
        pruned_by_copiedover: List[BaseSchema] = []
        if self.properties != None:
            for value in self.properties.values():
                child_schema_tuple = value.get_all_schemas()
                normal_schemas.extend(child_schema_tuple[0])
                pruned_by_overspecified.extend(child_schema_tuple[1])
                pruned_by_copiedover.extend(child_schema_tuple[2])
        if self.additional_properties != None:
            normal_schemas.append(self.additional_properties)

        if self.copied_over:
            if len(self.used_fields) == 0:
                keep = [normal_schemas.pop()]
            else:
                keep = []
            for schema in normal_schemas:
                if schema.path in self.used_fields:
                    keep.append(schema)
                else:
                    pruned_by_copiedover.append(schema)
            normal_schemas = keep
        elif self.over_specified:
            if len(self.used_fields) == 0:
                keep = []
            else:
                keep = []
            for schema in normal_schemas:
                if schema.path in self.used_fields:
                    keep.append(schema)
                else:
                    pruned_by_overspecified.append(schema)
            normal_schemas = keep

        if self not in normal_schemas:
            normal_schemas.append(self)

        return normal_schemas, pruned_by_overspecified, pruned_by_copiedover

    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        if self.problematic:
            return [], []

        normal_schemas: List[BaseSchema] = [self]
        semantic_schemas: List[BaseSchema] = []

        if self.properties != None:
            for value in self.properties.values():
                child_schema_tuple = value.get_normal_semantic_schemas()
                normal_schemas.extend(child_schema_tuple[0])
                semantic_schemas.extend(child_schema_tuple[1])

        if self.additional_properties != None:
            normal_schemas.append(self.additional_properties)

        return normal_schemas, semantic_schemas

    def to_tree(self) -> TreeNode:
        node = TreeNode(self.path)
        if self.properties != None:
            for key, value in self.properties.items():
                node.add_child(key, value.to_tree())

        if self.additional_properties != None:
            node.add_child('additional_properties', self.additional_properties.to_tree())

        return node

    def load_examples(self, example: dict):
        self.examples.append(example)
        for key, value in example.items():
            if key in self.properties:
                self.properties[key].load_examples(value)

    def set_default(self, instance):
        self.default = instance

    def empty_value(self):
        return {}

    def get_property_schema(self, key):
        logger = get_thread_logger(with_prefix=True)
        if key in self.properties:
            return self.properties[key]
        elif self.additional_properties != None:
            return self.additional_properties
        else:
            logger.warning('Field [%s] does not have a schema, using opaque schema', key)
            return OpaqueSchema(self.path + [key], {})

    def get_properties(self) -> dict:
        return self.properties

    def get_additional_properties(self):
        return self.additional_properties

    def __str__(self) -> str:
        ret = '{'
        for k, v in self.properties.items():
            ret += str(k)
            ret += ': '
            ret += str(v)
            ret += ', '
        ret += '}'
        return ret

    def __getitem__(self, key):
        if self.additional_properties != None and key not in self.properties:
            # if the object schema has additionalProperties, and the key is not in the properties,
            # return the additionalProperties schema
            return self.additional_properties
        return self.properties[key]

    def __setitem__(self, key, value):
        self.properties[key] = value
